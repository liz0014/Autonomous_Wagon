import RPi.GPIO as GPIO
import time

# GPIO pin number for the first motor's PWM signal (BCM numbering)
PWM_PIN = 13
# GPIO pin number for the second motor's PWM signal (BCM numbering)
PWM_PIN_TWO = 12
# PWM frequency in Hertz (100 Hz in this case)
FREQ = 100
# Maximum voltage for the motors (Pi outputs 3.3V, capped at 0.8V for safety)
V_MAX = 0.8

# Set GPIO to use BCM (Broadcom) pin numbering instead of board numbering
GPIO.setmode(GPIO.BCM)
# Configure first PWM pin as output
GPIO.setup(PWM_PIN, GPIO.OUT)
# Configure second PWM pin as output
GPIO.setup(PWM_PIN_TWO, GPIO.OUT)

# Create PWM object for first motor on pin 13 at 100 Hz frequency
pwm = GPIO.PWM(PWM_PIN, FREQ)
# Start the first PWM with 1% duty cycle
pwm.start(1)

# Create PWM object for second motor on pin 12 at 100 Hz frequency
pwm_two = GPIO.PWM(PWM_PIN_TWO, FREQ)
# Start the second PWM with 1% duty cycle
pwm_two.start(1)

# Define function to set voltage by converting it to PWM duty cycle
def set_voltage(v):
    # Convert voltage to duty cycle percentage
    """Convert voltage to duty cycle"""
    # Calculate duty cycle: (voltage / max_voltage) * 100
    duty = (v / V_MAX) * 100
    # Clamp duty to range 0–100%
    duty = max(0, min(100, duty))
    # Apply duty cycle to first motor
    pwm.ChangeDutyCycle(duty)
    # Apply duty cycle to second motor
# Apply duty cycle to second motor
    pwm_two.ChangeDutyCycle(duty)

# Start infinite loop for continuous motor control
try:
    # Infinite loop - runs until user presses Ctrl+C
    while True:
        # Ramp UP (0 → 3.3V in 3 sec)
        # Number of steps for ramping
        steps = 60
        # Gradually increase voltage from 0 to max
        for i in range(steps + 1):
            # Calculate voltage for this step
            v = V_MAX * (i / steps)
            # Set the motor to this voltage
            set_voltage(v)
            # Wait between steps for smooth ramp
            time.sleep(3 / steps)
        
        # Print status message
        print("Holding HIGH")
        # Hold at max voltage for 1 second
        time.sleep(1)

        # Ramp DOWN (3.3 → 0 in 3 sec)
        # Loop through each ramp step down
        for i in range(steps + 1):
            # Calculate voltage for this step (decreasing from V_MAX to 0)
            v = V_MAX * (1 - i / steps)
            # Set the motor to this voltage
            set_voltage(v)
            # Wait between steps for smooth ramp
            time.sleep(1 / steps)

        # Print status message when ramped down
        print("Holding LOW")
        # Hold at low voltage for 1 second
        time.sleep(1)

# Catch Ctrl+C interrupt from user
except KeyboardInterrupt:
    # Do nothing on interrupt - just exit cleanly
    pass

# Stop first motor PWM
pwm.stop()
# Stop second motor PWM
pwm_two.stop()
# Clean up GPIO pins to release them
GPIO.cleanup()