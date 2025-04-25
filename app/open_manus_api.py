import asyncio
import configparser
import hashlib
import json
import os
import secrets
from typing import Optional

import mysql.connector
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent.manus import Manus
from app.mcp_client import MCPClient
from app.tool.mcp_tool import MCPTool


class OpenManusAPI:
    def __init__(self):
        self.app = FastAPI()
        self.mcp_client = MCPClient()
        self.serverRunning = False
        self.sessions = {}
        self.agent = Manus()

        self.setup_routes()
        self.init_mcp_tools()

    def get_db_connection(self):
        config = configparser.ConfigParser()
        config.read("config/database.ini")

        return mysql.connector.connect(
            host=config["mysql"]["host"],
            database=config["mysql"]["database"],
            user=config["mysql"]["user"],
            password=config["mysql"]["password"],
            port=int(config["mysql"]["port"]),
        )

    async def execute_sql(self, query: str, params=None, fetch_one=False):
        conn = self.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if query.strip().upper().startswith("SELECT"):
                if fetch_one:
                    return cursor.fetchone()
                else:
                    return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
        finally:
            cursor.close()
            conn.close()

    def get_current_user(self, request: Request):
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in self.sessions:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Basic"},
            )
        return self.sessions[session_id]

    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        return (
            hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 100000
            ).hex()
            + ":"
            + salt
        )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        stored_hash, salt = hashed_password.split(":")
        new_hash = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode(), salt.encode(), 100000
        ).hex()
        return new_hash == stored_hash

    async def load_mcp_tools(self, scene_id: int = 1):
        """Load tools from enabled MCP servers for specified scene"""
        tools = []

        # Get all active MCP servers for this scene
        configs = await self.execute_sql(
            """SELECT server_name FROM mcp_config
               WHERE scene_id = %s AND active = TRUE""",
            (scene_id,),
        )

        for config in configs:
            server_name = config["server_name"]
            if server_name in self.mcp_client.tools:
                for tool in self.mcp_client.tools[server_name]:
                    tools.append(
                        MCPTool(
                            tool.name,
                            server_name,
                            tool.inputSchema,
                            tool.description if tool.description else tool.name,
                            self.mcp_client,
                        )
                    )
        return tools

    def setup_routes(self):
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        self.templates = Jinja2Templates(directory="templates")

        @self.app.get("/login", response_class=HTMLResponse)
        async def login_page(request: Request):
            return self.templates.TemplateResponse("login.html", {"request": request})

        @self.app.post("/login")
        async def login(
            request: Request, username: str = Form(...), password: str = Form(...)
        ):
            # Check user exists and password matches
            user = await self.execute_sql(
                "SELECT * FROM users WHERE username = %s", (username,), fetch_one=True
            )
            if not user or not self.verify_password(password, user["password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )

            # Create session
            session_id = secrets.token_urlsafe(32)
            self.sessions[session_id] = username
            response = RedirectResponse(
                url="/chat", status_code=status.HTTP_303_SEE_OTHER
            )
            response.set_cookie(key="session_id", value=session_id, httponly=True)
            return response

        @self.app.get("/register", response_class=HTMLResponse)
        async def register_page(request: Request):
            return self.templates.TemplateResponse(
                "register.html", {"request": request}
            )

        @self.app.post("/register")
        async def register(
            username: str = Form(...),
            password: str = Form(...),
            phone: str = Form(None),
            name: str = Form(None),
        ):
            # Check if username already exists
            existing_user = await self.execute_sql(
                "SELECT * FROM users WHERE username = %s", (username,), fetch_one=True
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists",
                )

            # Hash password and create user
            hashed_password = self.hash_password(password)
            await self.execute_sql(
                "INSERT INTO users (username, password, phone, name) VALUES (%s, %s, %s, %s)",
                (username, hashed_password, phone, name),
            )

            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

        @self.app.get("/logout")
        async def logout(request: Request):
            session_id = request.cookies.get("session_id")
            if session_id in self.sessions:
                del self.sessions[session_id]
            response = RedirectResponse(
                url="/login", status_code=status.HTTP_303_SEE_OTHER
            )
            response.delete_cookie("session_id")
            return response

        @self.app.get("/", response_class=HTMLResponse)
        async def root(request: Request):
            return self.templates.TemplateResponse("chat.html", {"request": request})

        @self.app.get("/chat", response_class=HTMLResponse)
        async def chat_page(request: Request):
            return self.templates.TemplateResponse("chat.html", {"request": request})

        @self.app.post("/chat")
        async def chat_response(
            user_input: str = Form(...), show_steps: bool = Form(False)
        ):
            response = await self.agent.run(user_input, show_steps=show_steps)
            # Convert newlines to <br> and escape HTML
            html_response = response.replace("\n", "<br>")
            # Return only the assistant's answer
            return html_response

        @self.app.post("/clear-messages")
        async def clear_messages():
            self.agent.memory.messages = []
            self.agent.current_step = 0
            return "Messages cleared"

        @self.app.get("/get-user-scenes")
        async def get_user_scenes():
            # Get all scenes
            scenes = await self.execute_sql(
                """SELECT id, name, is_active
                   FROM user_scenes""",
            )
            return JSONResponse({"scenes": scenes})

        @self.app.get("/get-mcp-config")
        async def get_mcp_config(scene_id: int):
            # Get all MCP configs for this scene from database
            configs = await self.execute_sql(
                """SELECT server_name, cmd, args, env, active
                   FROM mcp_config
                   WHERE scene_id = %s""",
                (scene_id,),
            )

            # Format response to match expected structure
            formatted_configs = []
            for config in configs:
                formatted_configs.append(
                    {
                        "server_name": config["server_name"],
                        "config": {
                            "cmd": config["cmd"],
                            "args": config["args"],
                            "env": config["env"],
                            "disabled": not config["active"],
                        },
                    }
                )

            return JSONResponse({"configs": formatted_configs})

        @self.app.post("/save-mcp-config")
        async def save_mcp_config(request: Request):
            data = await request.json()
            server_name = data.get("server_name")
            config = data.get("config")

            if not all([server_name, config]):
                return JSONResponse(
                    {"error": "Missing required parameters"}, status_code=400
                )

            try:
                # Use default scene ID (1)
                scene_id = 1

                # First check if record exists
                existing = await self.execute_sql(
                    "SELECT 1 FROM mcp_config WHERE scene_id = %s AND server_name = %s",
                    (scene_id, server_name),
                    fetch_one=True,
                )

                if existing:
                    # Update existing record
                    await self.execute_sql(
                        """UPDATE mcp_config
                           SET cmd = %s, args = %s, env = %s, active = %s
                           WHERE scene_id = %s AND server_name = %s""",
                        (
                            config.get("cmd"),
                            config.get("args"),
                            config.get("env"),
                            not config.get("disabled", False),
                            scene_id,
                            server_name,
                        ),
                    )
                else:
                    # Insert new record
                    await self.execute_sql(
                        """INSERT INTO mcp_config
                           (scene_id, server_name, cmd, args, env, active)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            scene_id,
                            server_name,
                            config.get("cmd"),
                            config.get("args"),
                            config.get("env"),
                            not config.get("disabled", False),
                        ),
                    )

                return JSONResponse({"status": "success"})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @self.app.post("/add-scene")
        async def add_scene(name: str = Form(...)):
            # Create new scene directly in user_scenes
            await self.execute_sql(
                """INSERT INTO user_scenes
                   (name, config, is_active)
                   VALUES (%s, %s, TRUE)""",
                (name, json.dumps({"mcpServers": {}})),
            )

            scene_id = await self.execute_sql(
                "SELECT LAST_INSERT_ID() AS id", fetch_one=True
            )

            # Deactivate other scenes
            await self.execute_sql(
                "UPDATE user_scenes SET is_active = FALSE WHERE id != %s",
                (scene_id["id"],),
            )

            return JSONResponse({"status": "success", "scene_id": scene_id["id"]})

        @self.app.post("/set-active-scene")
        async def set_active_scene(scene_id: int):
            # Set this scene as active
            await self.execute_sql(
                "UPDATE user_scenes SET is_active = TRUE WHERE id = %s",
                (scene_id,),
            )

            # Deactivate other scenes
            await self.execute_sql(
                "UPDATE user_scenes SET is_active = FALSE WHERE id != %s",
                (scene_id,),
            )

            return JSONResponse({"status": "success"})

        @self.app.post("/delete-mcp-config")
        async def delete_mcp_config(scene_id: int, server_name: str):
            await self.execute_sql(
                "DELETE FROM mcp_config WHERE scene_id = %s AND server_name = %s",
                (scene_id, server_name),
            )
            return JSONResponse({"status": "success"})

        @self.app.post("/save-mcp-settings")
        async def save_mcp_settings(request: Request):
            # Use default scene ID (1)
            scene_id = 1

            # Update scene config
            data = await request.json()
            await self.execute_sql(
                "UPDATE user_scenes SET config = %s WHERE id = %s",
                (json.dumps(data), scene_id),
            )

            return JSONResponse({"status": "success"})

        @self.app.get("/start-mcp-server")
        async def start_mcp_server(server_name: str):
            # Use default scene ID (1)
            scene_id = 1

            try:
                server_config = await self.execute_sql(
                    """SELECT cmd, args, env FROM mcp_config
                       WHERE scene_id = %s AND server_name = %s""",
                    (scene_id, server_name),
                    fetch_one=True,
                )

                if not server_config:
                    return JSONResponse(
                        {"error": "Server config not found"}, status_code=404
                    )

                # Start server with config
                success = await self.mcp_client.start_server(server_name, server_config)

                if success:
                    # First delete any existing tools from this server
                    tools_to_delete = [
                        tool.name for tool in self.mcp_client.tools.get(server_name, [])
                    ]
                    for tool_name in tools_to_delete:
                        self.agent.available_tools.delete_tool(tool_name)

                    # Then add the new tools
                    tools = await self.load_mcp_tools(scene_id)
                    for tool in tools:
                        self.agent.available_tools.add_tool(tool)
                return JSONResponse({"success": success})

            except Exception as e:
                return JSONResponse(
                    {"error": f"Failed to start server: {str(e)}"}, status_code=500
                )

        @self.app.get("/list-mcp-servers")
        async def list_mcp_servers():
            """List all configured MCP servers"""
            servers = await self.execute_sql(
                "SELECT DISTINCT server_name FROM mcp_config",
            )
            return JSONResponse({"servers": [s["server_name"] for s in servers]})

        @self.app.get("/stop-mcp-server")
        async def stop_mcp_server(server_name: str):
            success = self.mcp_client.stop_server(server_name)
            if success:
                # Remove tools from stopped server
                tools_to_delete = [
                    tool.name for tool in self.mcp_client.tools.get(server_name, [])
                ]
                for tool_name in tools_to_delete:
                    self.agent.available_tools.delete_tool(tool_name)
            return JSONResponse({"success": success})

        @self.app.get("/settings", response_class=HTMLResponse)
        async def settings_page(request: Request):
            return self.templates.TemplateResponse(
                "settings.html", {"request": request}
            )

        @self.app.get("/get-mcp-server-tools")
        async def get_mcp_server_tools(server_name: str):
            status = self.mcp_client.get_server_status(server_name)
            if status and server_name in self.mcp_client.tools:
                return JSONResponse(
                    {
                        "tools": [
                            {"name": tool.name, "description": tool.description}
                            for tool in self.mcp_client.tools[server_name]
                        ]
                    }
                )
            return JSONResponse({"tools": []})

    async def init_mcp_tools(self):
        tools = await self.load_mcp_tools()
        for tool in tools:
            self.agent.available_tools.add_tool(tool)
