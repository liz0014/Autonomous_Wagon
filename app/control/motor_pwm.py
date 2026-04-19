"""
motor_pwm.py
------------
Wiring:
  Pi GPIO 13 → left motor controller  → left motor
  Pi GPIO 12 → right motor controller → right motor

Speed is a normalized float 0.0 to 1.0:
  0.0 = stopped
  1.0 = full speed

PWM frequency: 100 Hz
"""
import logging 
import RPi.GPIO as GPIO

log = logging.getLogger(__name__)


PIN_LEFT = 13 #left motor Controller
PIN_RIGHT = 12 #Right motor Controller

PWM_FREQ = 100
MAX_DUTY = 85.0
V_MAX = 1.0

_pwm_left = None
_pwm_right = None

_HW_AVAILABLE = False

def init():
    global _pwm_left
    global _pwm_right
    global _HW_AVAILABLE

    try:
        GPIO.setmode(GPIO.BCM)
        # Suppress warnings if pins were left in a dirty state from a previous run
        GPIO.setwarnings(False)

        # Configure both pins as outputs — they will send signals, not receive them
        GPIO.setup(PIN_LEFT,  GPIO.OUT)
        GPIO.setup(PIN_RIGHT, GPIO.OUT)

        # Create PWM objects — frequency is set here, duty cycle set later
        _pwm_left  = GPIO.PWM(PIN_LEFT,  PWM_FREQ)
        _pwm_right = GPIO.PWM(PIN_RIGHT, PWM_FREQ)

        # Start both motors at 70% duty cycle — fully stopped
        _pwm_left.start(70)
        _pwm_right.start(70)

        _HW_AVAILABLE = True
        log.info("Motor PWM initialized - left=GPIO13, right=GPIO12")

    except Exception as e:
        # If anything fails run the rest of app but without the motors
        log.warning(f"motor PWM init failed - running in stub mode ({e})")
        _HW_AVAILABLE = False

def set_speeds(left: float, right: float):



    if not _HW_AVAILABLE:
        #testing - no hardware
        log.debug (f"STUB motors: left={left:.2f} right={right:.2f}")
        return
    left = max(0.0, min(1.0, left))
    right = max(0.0, min(1.0, right))



    # converting to duty cycle 
    left_duty = min((left * V_MAX) *100, MAX_DUTY)
    right_duty = min((right * V_MAX)*100, MAX_DUTY)
    print(f"DEBUG pwm: left_duty={left_duty:.1f}% right_duty={right_duty:.1f}%") 
    #sending the duty cycle to each motor
    _pwm_left.ChangeDutyCycle(left_duty)
    _pwm_right.ChangeDutyCycle(right_duty)

    log.debug(f"Motors: left={left:.2f} ({left_duty:.1f}%) right={right:.2f} ({right_duty:.1f}%)")

def stop():

    if not _HW_AVAILABLE:
        return
    
    #setting both motors zero duty cycle
    _pwm_left.ChangeDutyCycle(0)
    _pwm_right.ChangeDutyCycle(0)
    log.info("motors stopped")

def  cleanup():
    stop()
    if not _HW_AVAILABLE:
        return
    #Stops pwm signal
    _pwm_left.stop()
    _pwm_right.stop()
    #Release GPIO pins back to the system
    GPIO.cleanup()
    log.info("Motor pwm cleaned up")





