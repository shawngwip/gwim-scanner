import os
import csv
import time
import pymysql
import threading
from datetime import datetime
from config import MYSQL_CONFIG, DEVICE_LINE, DEVICE_ID
import simpleaudio as sa
import sys
from evdev import InputDevice, list_devices, categorize, ecodes

# --- 日志重定向 ---
try:
    log_path = "/home/pi/Desktop/gwim_log.txt"
    sys.stdout = open(log_path, "a", buffering=1)
    sys.stderr = sys.stdout
    print("🔁 Script started (log ready)")
except Exception as e:
    with open("/home/pi/Desktop/gwim_fallback.txt", "a") as f:
        f.write(f"Logging failed: {e}\n")

# --- 音效播放函数 ---
def play_success():
    try:
        sa.WaveObject.from_wave_file("success.wav").play()
        print("🔊 success.wav 播放")
    except Exception as e:
        print("⚠️ 播放 success.wav 失败：", e)

def play_error():
    try:
        sa.WaveObject.from_wave_file("error.wav").play()
        print("🔊 error.wav 播放")
    except Exception as e:
        print("⚠️ 播放 error.wav 失败：", e)

# --- 工具函数 ---
def safe_int(value):
    try:
        return int(value)
    except:
        return None

# --- 自动识别扫码器设备 ---
def auto_find_device():
    for path in list_devices():
        dev = InputDevice(path)
        if "Barcode" in dev.name or "Scanner" in dev.name or "USB" in dev.name:
            print(f"✅ 自动识别扫码器: {dev.name} @ {path}")
            return path
    print("❌ 没有找到扫码器设备，请检查连接")
    return None

# --- 初始化变量 ---
RESET_CODES = {"RESET", "RESET-001", "RESETGWIM"}
SCAN_INTERVAL = 1.5
CSV_FOLDER = "logs"
os.makedirs(CSV_FOLDER, exist_ok=True)

current_batch = None
current_muf = None
template_code = None
muf_info = None
last_scan_time = 0
last_barcode = None

csv_lock = threading.Lock()

# --- 数据库操作 ---
def fetch_muf_info(cursor, muf_code):
    cursor.execute("SELECT * FROM main WHERE muf_no = %s", (muf_code,))
    return cursor.fetchone()

def write_to_csv(data, muf_no, uploaded=0):
    with csv_lock:
        filename = os.path.join(CSV_FOLDER, f"{muf_no}_{datetime.now().strftime('%Y%m%d')}.csv")
        is_new = not os.path.exists(filename)
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow([
                    "muf_no", "line", "fg_no", "pack_per_ctn", "pack_per_hr",
                    "actual_pack", "ctn_count", "scanned_code", "scanned_count",
                    "scanned_at", "scanned_by", "is_uploaded"
                ])
            writer.writerow(data + (uploaded,))
        print(f"📂 已写入 SD 卡缓存: {filename} (uploaded={uploaded})")

def process_and_store(barcode, muf_info):
    pack_per_ctn = safe_int(muf_info["pack_per_ctn"])
    ctn_count = 1
    actual_pack = pack_per_ctn * ctn_count if pack_per_ctn is not None else None

    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    data = (
        current_muf,
        DEVICE_LINE,
        muf_info["fg_no"],
        pack_per_ctn,
        safe_int(muf_info["pack_per_hr"]),
        actual_pack,
        ctn_count,
        barcode,
        1,
        timestamp,
        DEVICE_ID
    )

    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        sql = (
            "INSERT INTO output_test ("
            "muf_no, line, fg_no, pack_per_ctn, pack_per_hr, actual_pack, "
            "ctn_count, scanned_code, scanned_count, scanned_at, scanned_by"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        cursor.execute(sql, data)
        conn.commit()
        conn.close()
        print("✅ DB 插入成功")
        write_to_csv(data, current_muf, uploaded=1)
        play_success()
    except Exception as e:
        print("⚠️ DB 插入失败，仅写入缓存：", e)
        write_to_csv(data, current_muf, uploaded=0)
        play_success()

# --- 上传 SD 卡数据 ---
def upload_from_csv():
    print("⏫ 尝试从 SD 卡上传数据…")
    for file in os.listdir(CSV_FOLDER):
        if not file.endswith(".csv"):
            continue
        path = os.path.join(CSV_FOLDER, file)
        rows = []
        updated = False

        with csv_lock:
            with open(path, 'r', newline='') as f:
                reader = list(csv.reader(f))
                headers = reader[0]
                for row in reader[1:]:
                    if len(row) < 12 or row[-1] == "1":
                        continue
                    rows.append(row)

        if not rows:
            continue

        try:
            conn = pymysql.connect(**MYSQL_CONFIG)
            cursor = conn.cursor()
            for row in rows:
                sql = (
                    "INSERT INTO output_test ("
                    "muf_no, line, fg_no, pack_per_ctn, pack_per_hr, actual_pack, "
                    "ctn_count, scanned_code, scanned_count, scanned_at, scanned_by"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                cursor.execute(sql, row[:11])
            conn.commit()
            conn.close()
            updated = True
        except Exception as e:
            print("⚠️ 上传失败：", e)

        if updated:
            with csv_lock:
                with open(path, 'r', newline='') as f:
                    reader = list(csv.reader(f))
                    headers = reader[0]
                    for i in range(1, len(reader)):
                        if len(reader[i]) >= 12 and reader[i][-1] == "0":
                            reader[i][-1] = "1"
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(reader)
                print(f"✅ 已上传并标记: {path}")

    threading.Timer(300, upload_from_csv).start()

# --- 扫码监听 ---
def listen_to_barcode(device_path):
    global current_batch, current_muf, template_code, muf_info, last_barcode, last_scan_time

    print(f"🧭 正在监听扫码器输入: {device_path}")
    dev = InputDevice(device_path)
    barcode = ""

    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate != 1:
                continue
            key = key_event.keycode

            if key == 'KEY_ENTER':
                print(f"📥 扫描到条码: {barcode}")
                now = datetime.now()
                if barcode == last_barcode and (time.time() - last_scan_time) < SCAN_INTERVAL:
                    barcode = ""
                    continue
                last_barcode = barcode
                last_scan_time = time.time()

                if barcode in RESET_CODES:
                    current_batch = f"batch_{now.strftime('%Y%m%d_%H%M%S')}"
                    current_muf = None
                    template_code = None
                    muf_info = None
                    print(f"🔄 RESET 扫码，新批次开始: {current_batch}")
                elif not current_batch:
                    print("⚠️ 请先扫描 RESET 开始批次")
                elif current_muf is None:
                    conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
                    cursor = conn.cursor()
                    muf_info = fetch_muf_info(cursor, barcode)
                    conn.close()
                    if muf_info:
                        current_muf = barcode
                        print(f"✅ MUF 识别成功: {current_muf}")
                    else:
                        print(f"❌ MUF 不存在于数据库: {barcode}")
                        play_error()
                elif template_code is None:
                    template_code = barcode
                    print(f"🧾 模板条码设定为: {template_code}")
                    process_and_store(barcode, muf_info)
                elif barcode != template_code:
                    print(f"❌ 错误条码: {barcode} ≠ {template_code}，不写入数据库")
                    play_error()
                else:
                    process_and_store(barcode, muf_info)

                barcode = ""

            elif key.startswith('KEY_') and len(key) == 5:
                barcode += key[-1]
            elif key.startswith('KEY_KP'):
                barcode += key[-1]
            elif key == 'KEY_MINUS':
                barcode += '-'

# --- 主程序 ---
if __name__ == '__main__':
    upload_from_csv()
    device_path = auto_find_device()
    if device_path:
        listen_to_barcode(device_path)
    else:
        print("❌ 未检测到扫码器，程序终止")
