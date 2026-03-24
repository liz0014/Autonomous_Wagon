"""
navigation/brain.py
-------------------
Translates WagonState + steer value into left/right motor speeds.
This is the only file that calls motor_pwm.
No drawing, no detection logic — just drive physics.

Differential drive steering:
  correction  = steer * STEER_GAIN
  left_speed  = speed - correction
  right_speed = speed + correction

Acceleration ramping prevents sudden jerks by limiting the per-frame
speed delta to ACCEL_RAMP_RATE.
"""

from app.navigation.state_machine import WagonState
from app.control import motor_pwm
from app.config.settings import (
    BASE_SPEED, SEARCH_TURN_SPEED, STEER_GAIN, ACCEL_RAMP_RATE,
)

# Persistent state for acceleration ramping
_prev_left = 0.0
_prev_right = 0.0


def _ramp(current, target, rate):
    """Move current toward target by at most ±rate per call."""
    diff = target - current
    if abs(diff) <= rate:
        return target
    return current + rate * (1 if diff > 0 else -1)


def execute(state: WagonState, steer: float, speed_factor: float = 1.0):
    """
    Args:
        state        : WagonState enum value from state_machine
        steer        : float [-1.0, +1.0] from follow_logic
        speed_factor : float [0.0, 1.0] proportional speed from follow_logic
    """
    global _prev_left, _prev_right

    if state == WagonState.STOP:
        target_left = 0.0
        target_right = 0.0

    elif state == WagonState.SEARCH:
        # Spin slowly in place to scan (left reverse + right forward)
        target_left = -SEARCH_TURN_SPEED
        target_right = SEARCH_TURN_SPEED

    elif state == WagonState.FOLLOW:
        speed = BASE_SPEED * speed_factor
        correction = steer * STEER_GAIN
        target_left = speed - correction
        target_right = speed + correction
        # Clamp to [-1, +1]
        target_left = max(-1.0, min(1.0, target_left))
        target_right = max(-1.0, min(1.0, target_right))

    else:
        target_left = 0.0
        target_right = 0.0

    # Smooth acceleration ramp
    _prev_left = _ramp(_prev_left, target_left, ACCEL_RAMP_RATE)
    _prev_right = _ramp(_prev_right, target_right, ACCEL_RAMP_RATE)

    motor_pwm.set_speeds(_prev_left, _prev_right)