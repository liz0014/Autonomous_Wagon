
"""
wheel testing code, without the camera:

"""
import RPi.GPIO as GPIO
import time

PWM_PIN = 18        # hardware PWM pin
FREQ = 1000         # 1 kHz PWM
V_MAX = 3.3         # Pi max voltage

GPIO.setmode(GPIO.BCM)
GPIO.setup(PWM_PIN, GPIO.OUT)

pwm = GPIO.PWM(PWM_PIN, FREQ)
pwm.start(0)

def set_voltage(v):
    """Convert voltage to duty cycle"""
    duty = (v / V_MAX) * 100
    duty = max(0, min(100, duty))
    pwm.ChangeDutyCycle(duty)

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
        time.sleep(5)

        # Ramp DOWN (3.3 → 0 in 3 sec)
        for i in range(steps + 1):
            v = V_MAX * (1 - i / steps)
            set_voltage(v)
            time.sleep(3 / steps)

        print("Holding LOW")
        time.sleep(5)

except KeyboardInterrupt:
    pass

pwm.stop()
GPIO.cleanup()