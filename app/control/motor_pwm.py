"""
motor_pwm.py
------------
MCP4725 I2C DAC interface for precision analog motor control.
Replaces PWM with true 0-5V analog output.

Architecture:
  Pi I2C (GPIO 2/3) → MCP4725 chip → analog 0-5V → motor throttle pin

Speeds are normalized floats: -1.0 (full reverse) to +1.0 (full forward).
Direction control via GPIO pins (FWD/REV), voltage control via DAC.

Installation:
  pip install adafruit-circuitpython-mcp4725
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)

# ── Try to import I2C libraries; fall back to stub mode ──────────────────────
try:
    import board
    import busio
    from adafruit_mcp4725 import MCP4725
    _HW_AVAILABLE = True
except (ImportError, NotImplementedError) as e:
    log.warning(f"MCP4725 libraries not found — running in stub mode. ({e})")
    _HW_AVAILABLE = False
    board = None
    busio = None
    MCP4725 = None

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:
    log.warning("RPi.GPIO not found — direction pins will not respond.")
    _GPIO_AVAILABLE = False
    GPIO = None

from app.config.settings import (
    PIN_LEFT_FWD, PIN_LEFT_REV,
    PIN_RIGHT_FWD, PIN_RIGHT_REV,
)

# ── MCP4725 Configuration ─────────────────────────────────────────────────────

MCP4725_I2C_ADDRESS = 0x60  # Default address (configurable via A0 pin)
MCP4725_VREF = 5.0          # Reference voltage (5V)
MCP4725_MAX_12BIT = 4095    # 12-bit DAC max value

# Voltage mapping for normalized speeds
# Speed -1.0 → 0V   (full reverse)
# Speed  0.0 → 2.5V (neutral/stop)
# Speed +1.0 → 5V   (full forward)
NEUTRAL_VOLTAGE = MCP4725_VREF / 2.0  # 2.5V


# ── DAC Instances ─────────────────────────────────────────────────────────────

_dac_left: Optional[MCP4725] = None
_dac_right: Optional[MCP4725] = None
_i2c: Optional[object] = None


def init(dac_left_addr: int = 0x60, dac_right_addr: int = 0x61):
    """
    Initialize I2C and DAC chips.
    
    Args:
        dac_left_addr  : I2C address of left motor DAC (default 0x60)
        dac_right_addr : I2C address of right motor DAC (default 0x61)
    
    Note: If you only have one DAC, set both to the same address
          and it will control both motors simultaneously.
    """
    global _dac_left, _dac_right, _i2c

    if not _HW_AVAILABLE:
        log.info("DAC subsystem in stub mode (no hardware).")
        return

    try:
        # Initialize I2C bus
        _i2c = busio.I2C(board.SCL, board.SDA)
        log.info("I2C bus initialized (GPIO 2/3).")

        # Initialize left motor DAC
        try:
            _dac_left = MCP4725(_i2c, address=dac_left_addr)
            log.info(f"Left motor DAC initialized at 0x{dac_left_addr:02x}.")
        except Exception as e:
            log.warning(f"Left motor DAC (0x{dac_left_addr:02x}) failed: {e}")
            _dac_left = None

        # Initialize right motor DAC
        if dac_right_addr != dac_left_addr:
            try:
                _dac_right = MCP4725(_i2c, address=dac_right_addr)
                log.info(f"Right motor DAC initialized at 0x{dac_right_addr:02x}.")
            except Exception as e:
                log.warning(f"Right motor DAC (0x{dac_right_addr:02x}) failed: {e}")
                _dac_right = None
        else:
            _dac_right = _dac_left  # Use same DAC for both
            log.info("Both motors sharing single DAC (same speed).")

        # Initialize GPIO for direction control
        if _GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in (PIN_LEFT_FWD, PIN_LEFT_REV, PIN_RIGHT_FWD, PIN_RIGHT_REV):
                GPIO.setup(pin, GPIO.OUT)
            log.info("GPIO direction pins initialized.")

    except Exception as e:
        log.error(f"DAC initialization failed: {e}")
        _dac_left = None
        _dac_right = None


def set_speeds(left: float, right: float):
    """
    Drive both motors using DAC voltage + GPIO direction.
    
    Args:
        left  : float [-1.0, +1.0]  (-1=full reverse, 0=stop, +1=full forward)
        right : float [-1.0, +1.0]
    
    The DAC outputs:
      |speed| → volt magnitude
    Direction control:
      speed sign → GPIO FWD/REV pins
    """
    _drive_motor_dac(PIN_LEFT_FWD, PIN_LEFT_REV, _dac_left, left, is_left=True)
    _drive_motor_dac(PIN_RIGHT_FWD, PIN_RIGHT_REV, _dac_right, right, is_left=False)


def stop():
    """Emergency stop — all motors to neutral voltage."""
    set_speeds(0.0, 0.0)


def cleanup():
    """Shutdown: stop motors and release resources."""
    stop()
    if _i2c and _HW_AVAILABLE:
        try:
            _i2c.deinit()
            log.info("I2C bus closed.")
        except Exception as e:
            log.warning(f"I2C close error: {e}")
    if _GPIO_AVAILABLE and GPIO:
        GPIO.cleanup()


# ── Internal ──────────────────────────────────────────────────────────────────

def _speed_to_voltage(speed: float) -> float:
    """
    Convert normalized speed (-1.0 to +1.0) to analog voltage (0 to 5V).
    
    Mapping:
      -1.0 → 0V     (full reverse)
       0.0 → 2.5V   (neutral)
      +1.0 → 5V     (full forward)
    """
    # Clamp speed to valid range
    speed = max(-1.0, min(1.0, speed))
    # Map to voltage: voltage = 2.5 + (speed * 2.5)
    voltage = NEUTRAL_VOLTAGE + (speed * NEUTRAL_VOLTAGE)
    return voltage


def _voltage_to_dac_code(voltage: float) -> int:
    """
    Convert analog voltage (0-5V) to 12-bit DAC code (0-4095).
    
    DAC code = (voltage / VREF) * 4095
    """
    voltage = max(0.0, min(MCP4725_VREF, voltage))
    dac_code = int((voltage / MCP4725_VREF) * MCP4725_MAX_12BIT)
    return dac_code


def _drive_motor_dac(pin_fwd, pin_rev, dac_obj, speed: float, is_left: bool = True):
    """
    Drive a single motor via DAC.
    
    Args:
        pin_fwd  : GPIO pin for forward
        pin_rev  : GPIO pin for reverse
        dac_obj  : MCP4725 instance (or None if stub)
        speed    : normalized speed [-1.0, +1.0]
        is_left  : for logging
    """
    motor_name = "LEFT" if is_left else "RIGHT"

    # Clamp and map
    speed = max(-1.0, min(1.0, speed))
    voltage = _speed_to_voltage(speed)
    dac_code = _voltage_to_dac_code(voltage)

    # Set direction via GPIO
    if _GPIO_AVAILABLE and GPIO:
        if speed >= 0:
            GPIO.output(pin_fwd, GPIO.HIGH)
            GPIO.output(pin_rev, GPIO.LOW)
            direction = "FWD"
        else:
            GPIO.output(pin_fwd, GPIO.LOW)
            GPIO.output(pin_rev, GPIO.HIGH)
            direction = "REV"
    else:
        direction = "FWD" if speed >= 0 else "REV"

    # Set voltage via DAC
    if dac_obj is not None and _HW_AVAILABLE:
        try:
            dac_obj.value = dac_code
            log.debug(
                f"{motor_name:>5} speed={speed:+.2f}  "
                f"volt={voltage:.2f}V  code={dac_code:>4d}  dir={direction}"
            )
        except Exception as e:
            log.warning(f"{motor_name} DAC write failed: {e}")
    else:
        # Stub mode
        log.debug(
            f"{motor_name:>5} STUB  speed={speed:+.2f}  "
            f"volt={voltage:.2f}V  code={dac_code:>4d}  dir={direction}"
        )