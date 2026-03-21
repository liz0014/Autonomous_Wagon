import RPi.GPIO as GPIO
import time

PWM_PIN = 13        # hardware PWM pin for wheel 1
PWM_PIN_TWO = 12    # hardware PWM pin for wheel 2
FREQ = 100         # 1 kHz PWM
V_MAX = 1.65      # Pi max voltage

GPIO.setmode(GPIO.BCM)
GPIO.setup(PWM_PIN, GPIO.OUT)
GPIO.setup(PWM_PIN_TWO, GPIO.OUT)

pwm = GPIO.PWM(PWM_PIN, FREQ)
pwm.start(1)

pwm_two = GPIO.PWM(PWM_PIN_TWO, FREQ)
pwm_two.start(1)

def set_voltage(v):
    """Convert voltage to duty cycle"""
    duty = (v / V_MAX) * 100
    duty = max(0, min(100, duty))
    pwm.ChangeDutyCycle(duty)
    pwm_two.ChangeDutyCycle(duty)

try:
    while True:

        # Ramp UP (0 → 3.3V in 3 sec)
        steps = 60
       # for i in range(steps + 1):
       #     v = V_MAX * (i / steps)
        #    set_voltage(v)
        #    time.sleep(3 / steps)
        
        set_voltage(V_MAX)
        print("Holding HIGH")
        time.sleep(1)

        # Ramp DOWN (3.3 → 0 in 3 sec)
        for i in range(steps + 1):
            v = V_MAX * (1 - i / steps)
            set_voltage(v)
            time.sleep(1 / steps)

        print("Holding LOW")
        time.sleep(1)

except KeyboardInterrupt:
    pass

pwm.stop()
pwm_two.stop()
GPIO.cleanup()