import subprocess
import sys
import os
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw

# Global process handle
server_proc = None
logfile_path = os.path.join(os.getcwd(), "server.log")

def start_server(icon=None, item=None):
    global server_proc
    if server_proc is None or server_proc.poll() is not None:
        # Clear log file before starting
        with open(logfile_path, "w") as f:
            f.write("")  # truncate file

        logfile = open(logfile_path, "a")
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=logfile,
            stderr=logfile,
            creationflags=subprocess.CREATE_NO_WINDOW  # hide console window
        )
        print("Server started")

def stop_server(icon=None, item=None):
    global server_proc
    if server_proc and server_proc.poll() is None:
        server_proc.terminate()
        server_proc = None
        print("Server stopped")

def restart_server(icon=None, item=None):
    stop_server()
    start_server()

def view_logs(icon=None, item=None):
    if os.path.exists(logfile_path):
        os.startfile(logfile_path)
    else:
        print("No logs found yet.")

def quit_app(icon, item):
    stop_server()
    icon.stop()

def create_image(color="blue"):
    # Simple tray icon (circle)
    image = Image.new("RGB", (64, 64), "white")
    dc = ImageDraw.Draw(image)
    dc.ellipse((8, 8, 56, 56), fill=color)
    return image

menu = Menu(
    MenuItem("Start Server", start_server),
    MenuItem("Stop Server", stop_server),
    MenuItem("Restart Server", restart_server),
    MenuItem("View Logs", view_logs),
    MenuItem("Quit", quit_app)
)

icon = Icon("UvicornServer", create_image(), menu=menu)

# Start server immediately on launch
start_server()

# Run tray icon loop
icon.run()