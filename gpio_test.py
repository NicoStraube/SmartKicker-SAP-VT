import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
LEFT_RELAY = 16

def initThing():
  GPIO.cleanup()
  GPIO.setup(LEFT_RELAY, GPIO.OUT)
  time.sleep(2)
  test()

def test():
  GPIO.output(LEFT_RELAY, GPIO.LOW)

initThing()
