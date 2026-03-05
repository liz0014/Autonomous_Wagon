import RPi.GPIO as GPIO
import time

PWM_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(PWM_PIN, GPIO.OUT)

pwm = GPIO.PWM(PWM_PIN, 50)   # 50Hz like RC servo
pwm.start(7.5)                # neutral

def move_forward():
    pwm.ChangeDutyCycle(8)

def stop():
    pwm.ChangeDutyCycle(7.5)

def reverse():
    pwm.ChangeDutyCycle(6)

while True:
    move_forward()
    time.sleep(3)

    stop()
    time.sleep(3)