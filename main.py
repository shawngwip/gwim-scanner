import os
import csv
import time
import pymysql
import threading
from datetime import datetime
from config import MYSQL_CONFIG, DEVICE_LINE, DEVICE_ID
import simpleaudio as sa
import sys
import keyboard

# --- 调试模式开关 ---
DEBUG_MODE = True

def debug(msg):
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

# --- 日志重定向 ---
try:
    log_path = "/home/pi/Desktop/gwim_log.txt"
    sys.stdout = open(log_path, "a", buffering=1)
    sys.stderr = sys.stdout
    debug("🔁 Script started (log ready)")
except Exception as e:
    with open("/home/pi/Desktop/gwim_fallback.txt", "a") as f:
        f.write(f"Logging failed: {e}\n")

# --- 音效播放函数 ---
def play_success():
    try:
        sa.WaveObject.from_wave_file("success.wav").play()
        debug("🔊 success.wav 播放")
    except Exception as e:
        debug(f"⚠️ 播放 success.wav 失败：{e}")

def play_error():
    try:
        sa.WaveObject.from_wave_file("error.wav").play()
        debug("🔊 error.wav 播放")
    except Exception as e:
        debug(f"⚠️ 播放 error.wav 失败：{e}")

# --- 工具函数 ---
def safe_int(value):
    try:
        return int(value)
    except:
        return None

def normalize_barcode(code):
    return (
        code.strip()
            .replace("–", "-")   # en dash
            .replace("−", "-")   # minus
            .replace("—", "-")   # em dash
            .replace("_", "-")   # underscore
            .upper()
    )

# --- 初始化变量 ---
CSV_FOLDER = "/home/pi/Desktop/logs"
os.makedirs(CSV_FOLDER, exist_ok=True)

RESET_CODES = {"RESET", "RESET-001", "RESETGWIM"}
SCAN_INTERVAL = 1.5

current_batch = None
current_muf = None
template_code = None
muf_info = None
last_scan_time = 0
last_barcode = None
barcode_buffer = ""

csv_lock = threading.Lock()

# --- 数据库操作 ---
def fetch_muf_info(cursor, muf_code):
    debug(f"正在查询数据库 main 表，条件：muf_no = '{muf_code}'")
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
        debug(f"📂 已写入 CSV: {filename} (uploaded={uploaded})")

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
        debug("✅ DB 插入成功")
        write_to_csv(data, current_muf, uploaded=1)
        play_success()
    except Exception as e:
        debug(f"⚠️ DB 插入失败，仅写入缓存：{e}")
        write_to_csv(data, current_muf, uploaded=0)
        play_success()

# --- 上传 SD 卡数据 ---
def upload_from_csv():
    debug("⏫ 尝试从 SD 卡上传数据…")
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
            debug(f"⚠️ 上传失败：{e}")

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
                debug(f"✅ 已上传并标记: {path}")

    threading.Timer(300, upload_from_csv).start()

# --- 判断是否为 RESET 条码 ---
def is_reset_code(barcode):
    normalized = normalize_barcode(barcode)
    return normalized in {normalize_barcode(r) for r in RESET_CODES}

# --- 扫码监听 ---
def on_key(event):
    global barcode_buffer, last_barcode, last_scan_time
    global current_batch, current_muf, template_code, muf_info

    if event.name == "enter":
        barcode = barcode_buffer.strip()
        normalized_barcode = normalize_barcode(barcode)
        barcode_buffer = ""

        debug(f"📥 扫描到条码: '{barcode}' → 标准化为: '{normalized_barcode}'")

        now = datetime.now()
        last_barcode = barcode
        last_scan_time = time.time()

        if is_reset_code(barcode):
            current_batch = f"batch_{now.strftime('%Y%m%d_%H%M%S')}"
            current_muf = None
            template_code = None
            muf_info = None
            debug(f"🔄 RESET 扫码，新批次开始: {current_batch}")
        elif not current_batch:
            debug("⚠️ 请先扫描 RESET 开始批次")
        elif current_muf is None:
            try:
                clean_barcode = normalize_barcode(barcode)
                conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
                cursor = conn.cursor()
                muf_info = fetch_muf_info(cursor, clean_barcode)
                conn.close()
                if muf_info:
                    current_muf = clean_barcode
                    debug(f"✅ MUF 识别成功: {current_muf}")
                else:
                    debug(f"❌ MUF 不存在于数据库: {clean_barcode}")
                    play_error()
            except Exception as e:
                debug(f"⚠️ 数据库连接失败: {e}")
                play_error()
        elif template_code is None:
            if barcode == current_muf:
                debug(f"⚠️ 重复扫描到 MUF 条码：{barcode}，忽略此条码作为模板")
                return
            template_code = barcode
            debug(f"🧾 模板条码设定为: {template_code}")
            process_and_store(barcode, muf_info)
        elif barcode != template_code:
            debug(f"❌ 错误条码: {barcode} ≠ {template_code}，不写入数据库")
            play_error()
        else:
            process_and_store(barcode, muf_info)

    elif len(event.name) == 1:
        barcode_buffer += event.name
    elif event.name == "minus":
        barcode_buffer += "-"

# --- 主程序入口 ---
if __name__ == '__main__':
    upload_from_csv()
    debug("🧭 使用 keyboard 模块监听扫码…")
    keyboard.on_press(on_key)
    keyboard.wait()
