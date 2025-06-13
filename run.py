from src import create_app
from src.cli import init_db, reset_db
from flask_socketio import SocketIO
from src.routes.stream_controller import register_video_events
from src.detect_utils import detection_worker, task_queue, results, events
import threading

app = create_app()
app.cli.add_command(init_db)
app.cli.add_command(reset_db)

# 启动检测线程
threading.Thread(target=detection_worker, args=(app,), daemon=True).start()

socketio = SocketIO(app, cors_allowed_origins="*")
register_video_events(socketio)

if __name__ == "__main__":
    import eventlet
    import eventlet.wsgi

    socketio.run(app, debug=True, port=5001)
