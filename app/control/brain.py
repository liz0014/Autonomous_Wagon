"""
navigation/brain.py
-------------------
Translates WagonState + steer value into left/right motor speeds.
This is the only file that calls motor_pwm.
No drawing, no detection logic — just drive physics.

Differential drive steering:
  correction  = steer * STEER_GAIN
  left_speed  = BASE_SPEED - correction
  right_speed = BASE_SPEED + correction

Example — target is to the right, steer = +0.5:
  correction  = +0.5 * 0.40 = +0.20
  left_speed  = 0.55 - 0.20 = 0.35  (slows down)
  right_speed = 0.55 + 0.20 = 0.75  (speeds up)
  → right wheel faster = wagon curves right = target re-centres ✓
"""

from app.navigation.state_machine import WagonState
from app.control import motor_pwm
from app.config.settings import BASE_SPEED, SEARCH_TURN_SPEED, STEER_GAIN


def execute(state: WagonState, steer: float):
    """
    Args:
        state : WagonState enum value from state_machine
        steer : float [-1.0, +1.0] from follow_logic
    """
    if state == WagonState.STOP:
        # Person too close — cut both motors
        motor_pwm.set_speeds(0, 0)

    elif state == WagonState.SEARCH:
        # No person visible — spin slowly in place to scan
        # Left reverse + right forward = counter-clockwise rotation
        # Flip signs if your wagon spins the wrong way
        motor_pwm.set_speeds(-SEARCH_TURN_SPEED, SEARCH_TURN_SPEED)

    elif state == WagonState.FOLLOW:
        correction = steer * STEER_GAIN
        left  = BASE_SPEED - correction
        right = BASE_SPEED + correction
        # Clamp to [-1, +1] to never send out-of-range values to PWM
        motor_pwm.set_speeds(
            max(-1.0, min(1.0, left)),
            max(-1.0, min(1.0, right)),
        )