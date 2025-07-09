import RPi.GPIO as GPIO
import time

RED_PIN = 5

GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_PIN, GPIO.OUT)

# 初始化为不亮
GPIO.output(RED_PIN, GPIO.HIGH)
print("灯灭了，5 秒后亮")
time.sleep(5)

# 点亮
GPIO.output(RED_PIN, GPIO.LOW)
print("灯亮起，5 秒后关闭")
time.sleep(5)

# 灭灯
GPIO.output(RED_PIN, GPIO.HIGH)
print("测试完毕")
GPIO.cleanup()


import RPi.GPIO as GPIO
import time

PIN = 5
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

GPIO.output(PIN, GPIO.HIGH)  # 默认状态：灯灭（NO） / 亮（NC）
time.sleep(999)              # 保持状态让你测试
