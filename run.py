"""
run.py
------
Entry point for the autonomous wagon.
Run from the project root:

    python run.py

On Raspberry Pi we can also make it a systemd service pointing here.
"""

import logging
from app.web.app import create_app
from app.config.settings import FLASK_HOST, FLASK_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

if __name__ == "__main__":
    app = create_app()
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)