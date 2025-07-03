import os
import csv
import time
import pymysql
import threading
from datetime import datetime
from config import MYSQL_CONFIG, DEVICE_LINE, DEVICE_ID
import simpleaudio as sa
import sys

# --- 音效播放函数 ---
def play_success():
    try:
        sa.WaveObject.from_wave_file("success.wav").play()
    except:
        pass

def play_error():
    try:
        sa.WaveObject.from_wave_file("error.wav").play()
    except:
        pass

# --- 工具函数 ---
def safe_int(value):
    try:
        return int(value)
    except:
        return None

# --- 全局变量初始化 ---
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
                    "actual_pack", "ctn_count", "scanned_code", "scanned_count", "scanned_at", "scanned_by", "is_uploaded"
                ])
            writer.writerow(data + (uploaded,))
        print(f"📂 Cached to SD card: {filename} (uploaded={uploaded})")

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
        print("✅ DB insert successful.")
        write_to_csv(data, current_muf, uploaded=1)
        play_success()
    except Exception as e:
        print("⚠️ DB insert failed. Cached only:", e)
        write_to_csv(data, current_muf, uploaded=0)
        play_success()

# --- 定时上传函数 ---
def upload_from_csv():
    print("⏫ Attempting upload from SD card...")
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
            print("⚠️ Upload failed:", e)

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
                print(f"✅ Uploaded & updated: {path}")

    threading.Timer(300, upload_from_csv).start()

# --- 主循环启动 ---
upload_from_csv()
print("📦 System ready. Please scan RESET to begin.")

while True:
    try:
        if sys.stdin.closed or not sys.stdin.isatty():
            time.sleep(1)
            continue

        barcode = input().strip()
        now = datetime.now()

        if not barcode:
            continue

        if barcode == last_barcode and (time.time() - last_scan_time) < SCAN_INTERVAL:
            continue
        last_barcode = barcode
        last_scan_time = time.time()

        if barcode in RESET_CODES:
            current_batch = f"batch_{now.strftime('%Y%m%d_%H%M%S')}"
            current_muf = None
            template_code = None
            muf_info = None
            print(f"🔄 RESET scanned. New batch started: {current_batch}")
            continue

        if not current_batch:
            print("⚠️ Please scan RESET first to begin new batch.")
            continue

        if current_muf is None:
            conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            cursor = conn.cursor()
            muf_info = fetch_muf_info(cursor, barcode)
            conn.close()
            if muf_info:
                current_muf = barcode
                print(f"✅ MUF found: {current_muf}")
            else:
                print(f"❌ MUF not found in database: {barcode}")
                play_error()
            continue

        if template_code is None:
            template_code = barcode
            print(f"🧾 Template set: {template_code}")
            process_and_store(barcode, muf_info)
            continue

        if barcode != template_code:
            print(f"❌ ERROR: {barcode} ≠ {template_code} — skipped DB, only saved to CSV")
            play_error()
            continue

        process_and_store(barcode, muf_info)

    except KeyboardInterrupt:
        print("\n🛑 Program manually stopped.")
        break
