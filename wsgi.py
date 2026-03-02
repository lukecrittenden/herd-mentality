# For Production ONLY

from flask_app import Server
from db import DatabaseManager

database_manager = DatabaseManager()
server = Server(__name__, database_manager)

# Expose app and socketio for Gunicorn
app = server.app
socketio = server.socketio