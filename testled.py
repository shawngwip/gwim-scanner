import RPi.GPIO as GPIO
import time

LED_PINS = [5, 6, 13]
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in LED_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

print("Flashing LEDs...")
for i in range(3):
    for pin in LED_PINS:
        GPIO.output(pin, GPIO.LOW)  # Turn on
        time.sleep(0.3)
        GPIO.output(pin, GPIO.HIGH)  # Turn off

GPIO.cleanup()
