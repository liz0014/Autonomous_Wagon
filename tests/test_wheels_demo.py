import RPi.GPIO as GPIO
import time

# GPIO pins from settings.py
PIN_LEFT_FWD = 17
PIN_LEFT_REV = 27
PIN_LEFT_PWM = 12

PIN_RIGHT_FWD = 22
PIN_RIGHT_REV = 23
PIN_RIGHT_PWM = 13

FREQ = 1000         # 1 kHz PWM
DUTY_CYCLE = 75     # 0-100, control speed

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup direction pins
for pin in (PIN_LEFT_FWD, PIN_LEFT_REV, PIN_RIGHT_FWD, PIN_RIGHT_REV):
    GPIO.setup(pin, GPIO.OUT)

# Setup PWM pins
GPIO.setup(PIN_LEFT_PWM, GPIO.OUT)
GPIO.setup(PIN_RIGHT_PWM, GPIO.OUT)

pwm_left = GPIO.PWM(PIN_LEFT_PWM, FREQ)
pwm_left.start(0)

pwm_right = GPIO.PWM(PIN_RIGHT_PWM, FREQ)
pwm_right.start(0)

def move_forward(duty):
    """Move wagon forward at given duty cycle (0-100)"""
    GPIO.output(PIN_LEFT_FWD, GPIO.HIGH)
    GPIO.output(PIN_LEFT_REV, GPIO.LOW)
    GPIO.output(PIN_RIGHT_FWD, GPIO.HIGH)
    GPIO.output(PIN_RIGHT_REV, GPIO.LOW)
    pwm_left.ChangeDutyCycle(duty)
    pwm_right.ChangeDutyCycle(duty)

def move_backward(duty):
    """Move wagon backward at given duty cycle (0-100)"""
    GPIO.output(PIN_LEFT_FWD, GPIO.LOW)
    GPIO.output(PIN_LEFT_REV, GPIO.HIGH)
    GPIO.output(PIN_RIGHT_FWD, GPIO.LOW)
    GPIO.output(PIN_RIGHT_REV, GPIO.HIGH)
    pwm_left.ChangeDutyCycle(duty)
    pwm_right.ChangeDutyCycle(duty)

def stop():
    """Stop both wheels"""
    GPIO.output(PIN_LEFT_FWD, GPIO.LOW)
    GPIO.output(PIN_LEFT_REV, GPIO.LOW)
    GPIO.output(PIN_RIGHT_FWD, GPIO.LOW)
    GPIO.output(PIN_RIGHT_REV, GPIO.LOW)
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)

try:
    while True:
        # Move FORWARD with ramp up
        print("Moving FORWARD - ramping up...")
        steps = 30
        for i in range(steps + 1):
            duty = DUTY_CYCLE * (i / steps)
            move_forward(duty)
            time.sleep(2 / steps)
        
        print("Moving FORWARD at full speed")
        move_forward(DUTY_CYCLE)
        time.sleep(5)

        # Ramp DOWN
        print("Slowing down...")
        for i in range(steps + 1):
            duty = DUTY_CYCLE * (1 - i / steps)
            move_forward(duty)
            time.sleep(2 / steps)

        # Stop
        print("Stopping")
        stop()
        time.sleep(3)

        # Move BACKWARD
        print("Moving BACKWARD...")
        move_backward(DUTY_CYCLE)
        time.sleep(5)

        # Stop
        print("Stopping")
        stop()
        time.sleep(3)

except KeyboardInterrupt:
    print("Stopping...")
    stop()
finally:
    pwm_left.stop()
    pwm_right.stop()
    GPIO.cleanup()


