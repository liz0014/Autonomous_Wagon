"""
run.py
------
Entry point for the autonomous wagon with Flask web interface.

USAGE:
    1. Start the script:
       python run.py
    
    2. Open your browser:
       http://localhost:5000
    
    3. Use the web UI:
       - Click LOCK to lock onto a person
       - Wagon will automatically start driving toward them (motors engage)
       - Click UNLOCK to stop motors and reset

The full autonomous pipeline runs in the background:
  camera → detect persons → track (Kalman + scoring) → lock/unlock
  → compute steering & speed → state machine → motors → HUD overlay
  → MJPEG stream to browser

On Raspberry Pi you can make this a systemd service.
"""

import logging
from app.web.app import create_app
from app.config.settings import FLASK_HOST, FLASK_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info(" AUTONOMOUS WAGON STARTING")
    logger.info("=" * 70)
    
    app = create_app()
    
    logger.info("")
    logger.info(" Hardware initialized (motors, serial)")
    logger.info("")
    logger.info(" Flask server starting...")
    logger.info(f"   Open your browser: http://{FLASK_HOST}:{FLASK_PORT}")
    logger.info("")
    logger.info(" CONTROLS (via web UI):")
    logger.info("   • Click LOCK button → wagon locks onto person")
    logger.info("   • Motors engage automatically → autonomous driving starts")
    logger.info("   • Click UNLOCK button → motors stop, wagon freezes")
    logger.info("")
    logger.info("Press Ctrl+C to exit")
    logger.info("=" * 70)
    logger.info("")
    
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)