"""
serial.py
---------
Optional UART bridge — useful if you offload motor control to an Arduino/ESP32.
Sends compact command packets: "CMD,STEER\\n"
Set SERIAL_ENABLED=False in settings.py to disable entirely.
"""

import logging
import serial as pyserial

from app.config.settings import SERIAL_ENABLED, SERIAL_PORT, SERIAL_BAUD

log = logging.getLogger(__name__)
_ser = None


def init():
    global _ser
    if not SERIAL_ENABLED:
        log.info("Serial bridge disabled.")
        return
    try:
        _ser = pyserial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        log.info("Serial open: %s @ %d", SERIAL_PORT, SERIAL_BAUD)
    except Exception as exc:
        log.warning("Serial init failed (%s) — continuing without it.", exc)
        _ser = None


def send(cmd: str, steer: float):
    if _ser is None or not _ser.is_open:
        return
    try:
        packet = f"{cmd},{steer:+.3f}\n".encode()
        _ser.write(packet)
    except Exception as exc:
        log.warning("Serial write error: %s", exc)


def close():
    if _ser and _ser.is_open:
        _ser.close()