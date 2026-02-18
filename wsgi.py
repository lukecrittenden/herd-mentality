from flask_app import Server
from db import DatabaseManager

# Initialize database manager
database_manager = DatabaseManager()

# Create server instance
server_instance = Server(__name__, database_manager)

# Expose app and socketio for Gunicorn
app = server_instance.app
socketio = server_instance.socketio