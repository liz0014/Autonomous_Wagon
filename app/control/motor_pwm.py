import time

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except ImportError:
    ON_PI = False

class MotorPWM:
    def __init__(self, pwm_pin=18, freq_hz=50, duty_stop=7.5, duty_forward=8.2):
        self.pwm_pin = pwm_pin
        self.freq_hz = freq_hz
        self.duty_stop = duty_stop
        self.duty_forward = duty_forward
        self._pwm = None
        self._last = None

    def start(self):
        if not ON_PI:
            print("[MOTOR] RPi.GPIO not found -> SIM mode")
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pwm_pin, GPIO.OUT)
        self._pwm = GPIO.PWM(self.pwm_pin, self.freq_hz)
        self._pwm.start(self.duty_stop)
        self._last = self.duty_stop

    def _set(self, duty):
        if not ON_PI:
            print(f"[MOTOR][SIM] duty={duty}")
            return
        if self._last is None or abs(duty - self._last) > 0.01:
            self._pwm.ChangeDutyCycle(duty)
            self._last = duty

    def stop(self):
        self._set(self.duty_stop)

    def forward(self):
        self._set(self.duty_forward)

    def cleanup(self):
        if not ON_PI:
            return
        try:
            self.stop()
            time.sleep(0.1)
            self._pwm.stop()
        except Exception:
            pass
        GPIO.cleanup()