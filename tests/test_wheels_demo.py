# Import required libraries for GPIO control and timing
import RPi.GPIO as GPIO
import time

# GPIO pins for left wheel control
# PIN_LEFT_FWD: Forward direction control for left wheel
# PIN_LEFT_REV: Reverse direction control for left wheel
# PIN_LEFT_PWM: PWM pin to control left wheel speed
PIN_LEFT_FWD = 17 # Pin leftFwd 
PIN_LEFT_REV = 27 # pin leftRev
PIN_LEFT_PWM = 12 # pin leftPwm

# GPIO pins for right wheel control
# PIN_RIGHT_FWD: Forward direction control for right wheel
# PIN_RIGHT_REV: Reverse direction control for right wheel
# PIN_RIGHT_PWM: PWM pin to control right wheel speed
PIN_RIGHT_FWD = 22 # pin rightFwd
PIN_RIGHT_REV = 23 # pin rightRev
PIN_RIGHT_PWM = 13 # pin rightPwm

# PWM Configuration
FREQ = 1000         # PWM frequency in Hz (1 kHz)
DUTY_CYCLE = 75     # Default speed: 0-100 (percentage)

# Initialize GPIO using Broadcom (BCM) numbering scheme
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Suppress GPIO warnings

# Configure all direction control pins as outputs
for pin in (PIN_LEFT_FWD, PIN_LEFT_REV, PIN_RIGHT_FWD, PIN_RIGHT_REV):
    GPIO.setup(pin, GPIO.OUT)

# Configure PWM speed control pins as outputs
GPIO.setup(PIN_LEFT_PWM, GPIO.OUT)
GPIO.setup(PIN_RIGHT_PWM, GPIO.OUT)

# Initialize PWM objects for both wheels
# Start with 0% duty cycle (motors off)
pwm_left = GPIO.PWM(PIN_LEFT_PWM, FREQ)   # Left wheel PWM
pwm_left.start(0)                          # Initially stopped

pwm_right = GPIO.PWM(PIN_RIGHT_PWM, FREQ)  # Right wheel PWM
pwm_right.start(0)                         # Initially stopped

# ============================================================================
# Motor Control Functions
# ============================================================================

def move_forward(duty):
    """Move wagon forward at given duty cycle (0-100)"""
    # Set forward direction for both wheels
    GPIO.output(PIN_LEFT_FWD, GPIO.HIGH)
    GPIO.output(PIN_LEFT_REV, GPIO.LOW)
    GPIO.output(PIN_RIGHT_FWD, GPIO.HIGH)
    GPIO.output(PIN_RIGHT_REV, GPIO.LOW)
    # Apply speed control via PWM
    pwm_left.ChangeDutyCycle(duty)
    pwm_right.ChangeDutyCycle(duty)

def move_backward(duty):
    """Move wagon backward at given duty cycle (0-100)"""
    # Set reverse direction for both wheels
    GPIO.output(PIN_LEFT_FWD, GPIO.LOW)
    GPIO.output(PIN_LEFT_REV, GPIO.HIGH)
    GPIO.output(PIN_RIGHT_FWD, GPIO.LOW)
    GPIO.output(PIN_RIGHT_REV, GPIO.HIGH)
    # Apply speed control via PWM
    pwm_left.ChangeDutyCycle(duty)
    pwm_right.ChangeDutyCycle(duty)

def stop():
    """Stop both wheels by disabling direction controls and PWM"""
    # Disable all direction signals
    GPIO.output(PIN_LEFT_FWD, GPIO.LOW)
    GPIO.output(PIN_LEFT_REV, GPIO.LOW)
    GPIO.output(PIN_RIGHT_FWD, GPIO.LOW)
    GPIO.output(PIN_RIGHT_REV, GPIO.LOW)
    # Set PWM duty cycle to 0 (stop motors)
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)

# ============================================================================
# Main Demo Loop - Test both wheels in forward and backward motion
# ============================================================================

try:
    while True:
        # Move FORWARD with ramp up (smooth acceleration)
        print("Moving FORWARD - ramping up...")
        steps = 30  # Number of steps for acceleration
        for i in range(steps + 1):
            # Gradually increase speed from 0 to DUTY_CYCLE
            duty = DUTY_CYCLE * (i / steps)
            move_forward(duty)
            time.sleep(2 / steps)
        
        # Run at full speed
        print("Moving FORWARD at full speed")
        move_forward(DUTY_CYCLE)
        time.sleep(5)

        # Smooth deceleration (ramp down to stop)
        print("Slowing down...")
        for i in range(steps + 1):
            # Gradually decrease speed from DUTY_CYCLE to 0
            duty = DUTY_CYCLE * (1 - i / steps)
            move_forward(duty)
            time.sleep(2 / steps)

        # Complete stop and wait
        print("Stopping")
        stop()
        time.sleep(3)

        # Test backward motion
        print("Moving BACKWARD...")
        move_backward(DUTY_CYCLE)
        time.sleep(5)

        # Stop and repeat
        print("Stopping")
        stop()
        time.sleep(3)

# Graceful shutdown on Ctrl+C
except KeyboardInterrupt:
    print("Stopping...")
    stop()
finally:
    # Cleanup: stop PWM and release GPIO pins
    pwm_left.stop()
    pwm_right.stop()
    GPIO.cleanup()


