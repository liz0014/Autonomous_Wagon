import RPi.GPIO as GPIO
import time

# GPIO pin configuration for left wheel
# PIN_LEFT_FWD: Forward direction control for left motor
# PIN_LEFT_REV: Reverse direction control for left motor
# PIN_LEFT_PWM: PWM pin to control left motor speed
PIN_LEFT_FWD = 17
PIN_LEFT_REV = 27
PIN_LEFT_PWM = 12

# GPIO pin configuration for right wheel
# PIN_RIGHT_FWD: Forward direction control for right motor
# PIN_RIGHT_REV: Reverse direction control for right motor
# PIN_RIGHT_PWM: PWM pin to control right motor speed
PIN_RIGHT_FWD = 22
PIN_RIGHT_REV = 23
PIN_RIGHT_PWM = 13

# PWM frequency in Hz (1 kHz frequency for motor control)
FREQ = 1000         # 1 kHz PWM
# Maximum voltage output from Raspberry Pi (3.3V logic level)
V_MAX = 3.3         # Pi max voltage

# Initialize GPIO using Broadcom (BCM) numbering scheme
GPIO.setmode(GPIO.BCM)
# Suppress GPIO warnings for cleaner output
GPIO.setwarnings(False)

# Configure direction control pins (FWD/REV) as digital outputs
for pin in (PIN_LEFT_FWD, PIN_LEFT_REV, PIN_RIGHT_FWD, PIN_RIGHT_REV):
    GPIO.setup(pin, GPIO.OUT)

# Configure PWM speed control pins as outputs
GPIO.setup(PIN_LEFT_PWM, GPIO.OUT)
GPIO.setup(PIN_RIGHT_PWM, GPIO.OUT)

# Initialize PWM objects for both wheel motors
# Start with 0% duty cycle (motors initially stopped)
pwm_left = GPIO.PWM(PIN_LEFT_PWM, FREQ)   # Left wheel PWM controller
pwm_left.start(0)                          # Start with 0% duty cycle

pwm_right = GPIO.PWM(PIN_RIGHT_PWM, FREQ)  # Right wheel PWM controller
pwm_right.start(0)                         # Start with 0% duty cycle

def set_voltage(v):
    """
    Convert voltage (0-3.3V) to PWM duty cycle and apply to both wheels.
    This controls the speed of both motors simultaneously.
    """
    # Calculate duty cycle percentage from voltage
    duty = (v / V_MAX) * 100
    # Clamp duty cycle between 0-100%
    duty = max(0, min(100, duty))
    # Apply the same speed to both wheels
    pwm_left.ChangeDutyCycle(duty)
    pwm_right.ChangeDutyCycle(duty)

def move_forward():
    """
    Set both wheels to move forward direction.
    Activates forward control pin and deactivates reverse for both motors.
    """
    # Set left wheel to forward direction
    GPIO.output(PIN_LEFT_FWD, GPIO.HIGH)
    GPIO.output(PIN_LEFT_REV, GPIO.LOW)
    # Set right wheel to forward direction
    GPIO.output(PIN_RIGHT_FWD, GPIO.HIGH)
    GPIO.output(PIN_RIGHT_REV, GPIO.LOW)

try:
    # Set both wheels to forward direction at startup
    move_forward()
    
    while True:
        # Test sequence: Hold max speed, then ramp down
        
        # Optional: Ramp UP acceleration (currently disabled)
        # steps = 60
        # for i in range(steps + 1):
        #     v = V_MAX * (i / steps)
        #     set_voltage(v)
        #     time.sleep(3 / steps)
        
        # Set both wheels to maximum voltage (full speed)
        set_voltage(V_MAX)
        print("Holding HIGH")
        time.sleep(5)  # Hold at full speed for 5 seconds

        # Ramp DOWN deceleration from max voltage to 0 over 3 seconds
        steps = 60  # 60 steps = smooth deceleration
        for i in range(steps + 1):
            # Calculate voltage linearly decreasing from V_MAX to 0
            v = V_MAX * (1 - i / steps)
            set_voltage(v)  # Apply voltage to both wheels
            time.sleep(3 / steps)  # Sleep between steps for smooth ramp

        # Stop both wheels (0 voltage)
        print("Holding LOW")
        time.sleep(5)  # Hold at zero speed for 5 seconds before repeating

# Graceful shutdown on Ctrl+C
except KeyboardInterrupt:
    print("\nStopping motors...")
    pass

# Motor cleanup: stop PWM signals
pwm_left.stop()
pwm_right.stop()
# Release all GPIO pins
GPIO.cleanup()