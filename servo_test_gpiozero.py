from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

factory = PiGPIOFactory()   # uses pigpiod
servo = Servo(18, pin_factory=factory,
              min_pulse_width=0.5/1000, max_pulse_width=2.4/1000)

servo.mid(); sleep(1)
servo.min(); sleep(1)
servo.max(); sleep(1)
servo.mid(); sleep(1)
