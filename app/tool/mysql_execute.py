import multiprocessing
import sys
from io import StringIO
from typing import Dict

from app.tool.base import BaseTool
import pymysql

class MySqlExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "mysql_execute"
    description: str = "Executes sql str . Note: Only print outputs are visible, function return values are not captured. Use print statements to see results."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "sql to execute.",
            },
        },
        "required": ["code"],
    }

    def _run_code(self, code: str, result_dict: dict, safe_globals: dict) -> None:
        original_stdout = sys.stdout
        try:
            output_buffer = StringIO()
            sys.stdout = output_buffer
            exec(code, safe_globals, safe_globals)
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["success"] = True
        except Exception as e:
            result_dict["observation"] = str(e)
            result_dict["success"] = False
        finally:
            sys.stdout = original_stdout

    async def execute(
        self,
        code: str,
        timeout: int = 30,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout.

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds.

        Returns:
            Dict: Contains 'output' with execution output or error message and 'success' status.
        """
        result = {"observation": "", "success": False}
        conn = pymysql.connect(host="127.0.0.1", port=3306, user='root', passwd='998877', db='sells', charset='utf8mb4')
        cursor = conn.cursor()
        cursor.execute(code)
        result["observation"] = cursor.fetchall()
        return dict(result)



