import os
import csv
import time
import pymysql
import threading
from datetime import datetime
from config import MYSQL_CONFIG, DEVICE_LINE, DEVICE_ID
import sys
import keyboard
import RPi.GPIO as GPIO

# --- Debug mode switch ---
DEBUG_MODE = True

def debug(msg):
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")

# --- GPIO Setup ---

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# === Tower Light & Buzzer GPIO Setup ===
RED_PIN = 5       # Red tower light
GREEN_PIN = 6     # Green tower light
YELLOW_PIN = 13   # Yellow (Internet)
BUZZER_PIN = 19   # Buzzer for alerts

GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(YELLOW_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# 初始化所有灯和 buzzer 为 OFF（HIGH 表示 OFF）
GPIO.output(RED_PIN, GPIO.HIGH)
GPIO.output(GREEN_PIN, GPIO.HIGH)
GPIO.output(YELLOW_PIN, GPIO.HIGH)
GPIO.output(BUZZER_PIN, GPIO.HIGH)

# === State Control ===
def set_light(pin, state):
    GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

def blink_light(pin, duration=0.2, times=3):
    for _ in range(times):
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(duration)

def buzz(times=1, duration=0.2):
    for _ in range(times):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(duration)

# === Network Checker ===
def check_internet():
    response = os.system("ping -c 1 -W 1 8.8.8.8 > /dev/null 2>&1")
    return response == 0

def update_yellow_light():
    if check_internet():
        set_light(YELLOW_PIN, True)
    else:
        blink_light(YELLOW_PIN, duration=0.5, times=1)
    threading.Timer(30, update_yellow_light).start()

update_yellow_light()  # Start yellow light check thread



# --- Redirect stdout/stderr to log file ---
try:
    log_path = "/home/pi/gwim-scanner/gwim_log.txt"
    sys.stdout = open(log_path, "a", buffering=1)
    sys.stderr = sys.stdout
    debug("🔁 Script started (log ready)")
except Exception as e:
    with open("/home/pi/gwim-scanner/gwim_fallback.txt", "a") as f:
        f.write(f"Logging failed: {e}\n")

# --- Helper functions ---
def safe_int(value):
    try:
        return int(value)
    except:
        return None

def normalize_barcode(code):
    return (
        code.strip()
            .replace("–", "-")
            .replace("−", "-")
            .replace("—", "-")
            .replace("_", "-")
            .upper()
    )

# --- Global variables ---
CSV_FOLDER = "/home/pi/gwim-scanner/logs"
os.makedirs(CSV_FOLDER, exist_ok=True)

RESET_CODES = {"123456789"}
SCAN_INTERVAL = 2.0  # <- changed to 2.0 seconds

current_batch = None
current_muf = None
template_code = None
muf_info = None
last_scan_time = 0
last_barcode = None
barcode_buffer = ""

csv_lock = threading.Lock()

# --- Database operations ---
def fetch_muf_info(cursor, muf_code):
    debug(f"Querying table 'main' for muf_no = '{muf_code}'")
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
        debug(f"📂 Written to CSV: {filename} (uploaded={uploaded})")

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
        debug("✅ DB insert successful")
        write_to_csv(data, current_muf, uploaded=1)
        
    except Exception as e:
        debug(f"⚠️ DB insert failed. Cached locally: {e}")
        write_to_csv(data, current_muf, uploaded=0)
        

# --- Upload pending CSV data every 5 minutes ---
def upload_from_csv():
    debug("⏫ Attempting to upload cached CSV data...")
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
            debug(f"⚠️ Upload failed: {e}")

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
                debug(f"✅ Upload complete and marked: {path}")

    threading.Timer(300, upload_from_csv).start()

# --- Check if barcode is a RESET code ---
def is_reset_code(barcode):
    normalized = normalize_barcode(barcode)
    return normalized in {normalize_barcode(r) for r in RESET_CODES}

# --- Barcode scan listener ---
# --- Enhanced Logic with Tower Light ---
def on_key(event):
    global barcode_buffer, last_barcode, last_scan_time
    global current_batch, current_muf, template_code, muf_info

    if event.name == "enter":
        barcode = barcode_buffer.strip()
        normalized_barcode = normalize_barcode(barcode)
        barcode_buffer = ""

        now = datetime.now()
        now_ts = time.time()

        # --- Prevent duplicate within 2 seconds ---
        if barcode == last_barcode and now_ts - last_scan_time < SCAN_INTERVAL:
            debug(f"⏱️ Duplicate scan ignored: {barcode}")
            return

        last_barcode = barcode
        last_scan_time = now_ts

        debug(f"📥 Scanned barcode: '{barcode}' → normalized: '{normalized_barcode}'")

        if is_reset_code(barcode):
            # Green: slow blink after RESET
            threading.Thread(target=lambda: blink_light(GREEN_PIN, 0.5, 3)).start()
            current_batch = f"batch_{now.strftime('%Y%m%d_%H%M%S')}"
            current_muf = None
            template_code = None
            muf_info = None
            debug(f"🔄 RESET scanned. New batch: {current_batch}")
        elif not current_batch:
            debug("⚠️ Please scan RESET first.")
            blink_light(RED_PIN, 0.3, 3)
            buzz(1)
        elif current_muf is None:
            try:
                clean_barcode = normalize_barcode(barcode)
                conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
                cursor = conn.cursor()
                muf_info = fetch_muf_info(cursor, clean_barcode)
                conn.close()
                if muf_info:
                    current_muf = clean_barcode
                    debug(f"✅ MUF found: {current_muf}")
                    set_light(GREEN_PIN, True)
                else:
                    debug(f"❌ MUF not found: {clean_barcode}")
                    blink_light(RED_PIN, 0.3, 3)
                    buzz(1)
            except Exception as e:
                debug(f"⚠️ DB connection error: {e}")
                blink_light(RED_PIN, 0.3, 3)
                buzz(1)
        elif template_code is None:
            if barcode == current_muf:
                debug(f"⚠️ Duplicate MUF barcode: {barcode}, ignoring as template")
                return
            template_code = barcode
            debug(f"🧾 Template barcode set: {template_code}")
            process_and_store(barcode, muf_info)
        elif barcode != template_code:
            debug(f"❌ Barcode mismatch: {barcode} ≠ {template_code}, skipped DB")
            blink_light(RED_PIN, 0.3, 3)
            buzz(1)
        else:
            process_and_store(barcode, muf_info)

    elif len(event.name) == 1:
        barcode_buffer += event.name
    elif event.name == "minus":
        barcode_buffer += "-"

# --- Main entry ---
if __name__ == '__main__':
    upload_from_csv()
    debug("🧭 Listening for barcode scan via keyboard...")
    keyboard.on_press(on_key)
    keyboard.wait()
