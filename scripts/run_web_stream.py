"""
run_web_stream.py
-----------------
Start only the Flask MJPEG video stream.
"""

from app.web.app import create_app
from app.config.settings import FLASK_HOST, FLASK_PORT

if __name__ == "__main__":
    app = create_app()
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)