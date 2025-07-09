import RPi.GPIO as GPIO
import time

# GPIO 引脚编号
RED_PIN = 5
GREEN_PIN = 6
YELLOW_PIN = 13

# 使用 BCM 模式
GPIO.setmode(GPIO.BCM)

# 初始化为输出
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(YELLOW_PIN, GPIO.OUT)

# 初始化为关闭（HIGH = 灯灭）
GPIO.output(RED_PIN, GPIO.HIGH)
GPIO.output(GREEN_PIN, GPIO.HIGH)
GPIO.output(YELLOW_PIN, GPIO.HIGH)

print("🔴 Red ON")
GPIO.output(RED_PIN, GPIO.LOW)   # 灯亮
time.sleep(2)
GPIO.output(RED_PIN, GPIO.HIGH)  # 灯灭

print("🟢 Green ON")
GPIO.output(GREEN_PIN, GPIO.LOW)
time.sleep(2)
GPIO.output(GREEN_PIN, GPIO.HIGH)

print("🟡 Yellow ON")
GPIO.output(YELLOW_PIN, GPIO.LOW)
time.sleep(2)
GPIO.output(YELLOW_PIN, GPIO.HIGH)

print("✅ 测试完成，清理 GPIO")
GPIO.cleanup()



import RPi.GPIO as GPIO
import time

PIN = 5
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

GPIO.output(PIN, GPIO.HIGH)  # 默认状态：灯灭（NO） / 亮（NC）
time.sleep(999)              # 保持状态让你测试
