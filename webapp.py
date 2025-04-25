import os

import uvicorn

from app.open_manus_api import OpenManusAPI


def main():
    api = OpenManusAPI()
    print("uvicorn ready to start...")
    print(os.getpid())
    if not api.serverRunning:
        api.serverRunning = True
        try:
            uvicorn.run(api.app, host="0.0.0.0", port=8000)
        except Exception as e:
            api.serverRunning = False
            print(f"Failed to start server: {e}")


print("process name=" + __name__)
if __name__ == "__main__":
    main()
