"""
motor_pwm.py
------------
Low-level PWM interface for two DC motors via RPi GPIO (or pigpio).
Speeds are normalised floats: -1.0 (full reverse) to +1.0 (full forward).

Pin assignments → app/config/settings.py
"""

import logging

log = logging.getLogger(__name__)

# ── Try to import RPi.GPIO; fall back to a stub so the code runs on non-Pi ──
try:
    import RPi.GPIO as GPIO
    _HW_AVAILABLE = True
except ImportError:
    log.warning("RPi.GPIO not found — running in stub mode (no physical output).")
    _HW_AVAILABLE = False

from app.config.settings import (
    PIN_LEFT_FWD, PIN_LEFT_REV, PIN_LEFT_PWM,
    PIN_RIGHT_FWD, PIN_RIGHT_REV, PIN_RIGHT_PWM,
    PWM_FREQ_HZ,
)

_pwm_left  = None
_pwm_right = None


def init():
    """Call once at startup to configure GPIO pins and PWM channels."""
    global _pwm_left, _pwm_right

    if not _HW_AVAILABLE:
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for pin in (PIN_LEFT_FWD, PIN_LEFT_REV, PIN_LEFT_PWM,
                PIN_RIGHT_FWD, PIN_RIGHT_REV, PIN_RIGHT_PWM):
        GPIO.setup(pin, GPIO.OUT)

    _pwm_left  = GPIO.PWM(PIN_LEFT_PWM,  PWM_FREQ_HZ)
    _pwm_right = GPIO.PWM(PIN_RIGHT_PWM, PWM_FREQ_HZ)
    _pwm_left.start(0)
    _pwm_right.start(0)
    log.info("Motor PWM initialised.")


def set_speeds(left: float, right: float):
    """
    Drive both motors.
    left / right: floats in [-1.0, +1.0]
    """
    _drive_motor(PIN_LEFT_FWD,  PIN_LEFT_REV,  _pwm_left,  left)
    _drive_motor(PIN_RIGHT_FWD, PIN_RIGHT_REV, _pwm_right, right)


def stop():
    set_speeds(0, 0)


def cleanup():
    stop()
    if _HW_AVAILABLE:
        GPIO.cleanup()


# ── Internal ──────────────────────────────────────────────────────────────────

def _drive_motor(pin_fwd, pin_rev, pwm_ch, speed):
    duty = int(abs(speed) * 100)
    if _HW_AVAILABLE:
        if speed >= 0:
            GPIO.output(pin_fwd, GPIO.HIGH)
            GPIO.output(pin_rev, GPIO.LOW)
        else:
            GPIO.output(pin_fwd, GPIO.LOW)
            GPIO.output(pin_rev, GPIO.HIGH)
        if pwm_ch:
            pwm_ch.ChangeDutyCycle(duty)
    else:
        direction = "FWD" if speed >= 0 else "REV"
        log.debug("MOTOR STUB  pin_fwd=%s  %s  duty=%d%%", pin_fwd, direction, duty)