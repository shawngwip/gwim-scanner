
import RPi.GPIO as GPIO
import time
import threading
import requests
from threading import Timer

# -------------------- GPIO 设置 --------------------
RED_PIN = 5       # 红灯：错误
GREEN_PIN = 6     # 绿灯：系统状态
YELLOW_PIN = 13   # 黄灯：网络状态
BUZZER_PIN = 19   # 蜂鸣器

GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(YELLOW_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# -------------------- 灯控制函数 --------------------
def set_light(pin, state):
    GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

def blink_light(pin, duration=0.3, times=3):
    for _ in range(times):
        set_light(pin, False)
        time.sleep(duration)
        set_light(pin, True)
        time.sleep(duration)

# -------------------- 蜂鸣器 --------------------
def buzz(times=1, duration=0.15):
    for _ in range(times):
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.1)

# -------------------- 系统启动灯闪 --------------------
def startup_blink_green():
    for _ in range(5):
        set_light(GREEN_PIN, False)
        time.sleep(0.2)
        set_light(GREEN_PIN, True)
        time.sleep(0.1)

# -------------------- 网络状态更新 --------------------
def update_yellow_light():
    try:
        r = requests.get("http://www.google.com", timeout=3)
        # 网络 OK：黄灯常亮
        set_light(YELLOW_PIN, False)
    except:
        # 网络断线：慢闪黄灯
        blink_light(YELLOW_PIN, duration=0.5, times=1)
    finally:
        Timer(10.0, update_yellow_light).start()  # 每 10 秒检查一次

# -------------------- 模拟主流程 --------------------
def main():
    print("🔋 系统上电，启动中...")
    set_light(RED_PIN, True)
    set_light(GREEN_PIN, True)
    set_light(YELLOW_PIN, True)
    set_light(BUZZER_PIN, True)

    startup_blink_green()

    print("🌐 启动网络状态检测线程")
    update_yellow_light()

    print("🟢 模拟扫码 RESET：慢闪")
    blink_light(GREEN_PIN, duration=0.5, times=3)

    print("✅ 模拟 MUF 正确：绿灯常亮")
    set_light(GREEN_PIN, False)

    time.sleep(5)

    print("🚨 模拟错误 carton：红灯闪 + buzzer")
    blink_light(RED_PIN)
    buzz(2)

    time.sleep(5)
    print("🧹 清理 GPIO，程序结束")
    GPIO.cleanup()

if __name__ == '__main__':
    main()
