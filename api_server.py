from PIL import Image, ImageDraw, ImageFont
from flask import Flask, jsonify
import mysql.connector
from datetime import date, datetime as dt, timedelta

app = Flask(__name__)

# === Configuration ===
LINE_NAME = 'HF1'

def connect_production_db():
    return mysql.connector.connect(
        host="149.28.152.191",
        user="root",
        password="fb267146d223afbd24e88d5ea8090b0b8cdc4254146fa62d",
        database="production",
        charset='utf8mb4'
    )

def query_database():
    conn = None
    cursor = None
    try:
        conn = connect_production_db()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT muf_no FROM output_test
        WHERE muf_no IS NOT NULL AND muf_no != '' AND line = %s
        ORDER BY id DESC
        LIMIT 1
        """
        cursor.execute(query, (LINE_NAME,))
        result = cursor.fetchone()

        return result if result else {"message": "No recent muf_no found"}

    except mysql.connector.Error as err:
        return {"error": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_total_carton_needed(muf_no):
    conn = connect_production_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT qty_done FROM main WHERE muf_no = %s LIMIT 1", (muf_no,))
        result = cursor.fetchone()
        return float(result[0]) if result and result[0] is not None else 0
    finally:
        cursor.close()
        conn.close()

def get_target_hour(muf_no):
    conn = connect_production_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT pack_per_ctn, pack_per_hr FROM output_test
            WHERE muf_no = %s LIMIT 1
        """, (muf_no,))
        result = cursor.fetchone()
        if result and result['pack_per_ctn'] and result['pack_per_hr']:
            return int(round(result['pack_per_hr'] / result['pack_per_ctn'], 0))
        return 0
    finally:
        cursor.close()
        conn.close()

def get_average_hourly_output(muf_no, line):
    conn = connect_production_db()
    cursor = conn.cursor()
    try:
        now = dt.now()
        hour_start = now.replace(minute=1, second=0, microsecond=0)
        hour_end = hour_start + timedelta(minutes=59)
        query = """
            SELECT SUM(ctn_count) FROM output_test
            WHERE muf_no = %s AND line = %s AND scanned_at BETWEEN %s AND %s
        """
        cursor.execute(query, (muf_no, line, hour_start, hour_end))
        result = cursor.fetchone()
        return int(result[0]) if result and result[0] else 0
    finally:
        cursor.close()
        conn.close()

def get_balance_carton(muf_no):
    conn = connect_production_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT qty_done FROM main WHERE muf_no = %s LIMIT 1", (muf_no,))
        qty_done_result = cursor.fetchone()
        qty_done = int(qty_done_result[0]) if qty_done_result and qty_done_result[0] is not None else 0

        cursor.execute("SELECT SUM(ctn_count) FROM output_test WHERE muf_no = %s", (muf_no,))
        ctn_sum_result = cursor.fetchone()
        ctn_done = int(ctn_sum_result[0]) if ctn_sum_result and ctn_sum_result[0] else 0

        return qty_done - ctn_done
    finally:
        cursor.close()
        conn.close()

def get_balance_hours(muf_no):
    conn = connect_production_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT pack_per_ctn, pack_per_hr FROM output_test WHERE muf_no = %s LIMIT 1", (muf_no,))
        output_info = cursor.fetchone()
        if not output_info:
            return 0.0

        pack_per_ctn = float(output_info['pack_per_ctn'])
        pack_per_hr = float(output_info['pack_per_hr'])

        balance_cartons = get_balance_carton(muf_no)
        if pack_per_hr == 0:
            return 0.0
        return round((balance_cartons * pack_per_ctn) / pack_per_hr, 1)
    finally:
        cursor.close()
        conn.close()

@app.route('/query', methods=['GET'])
def get_query():
    data = query_database()
    if isinstance(data, dict) and "muf_no" in data:
        return data["muf_no"]
    else:
        return "No WIP found"

@app.route('/summary', methods=['GET'])
def get_summary():
    data = query_database()
    if not isinstance(data, dict) or "muf_no" not in data:
        return jsonify({"error": "No WIP muf_no found"}), 404

    muf_no = data["muf_no"]
    line = LINE_NAME
    summary = {
        "muf_no": muf_no,
        "total_carton_needed": get_total_carton_needed(muf_no),
        "target_hour": get_target_hour(muf_no),
        "avg_hourly_output": get_average_hourly_output(muf_no, line),
        "balance_carton": get_balance_carton(muf_no),
        "balance_hours": get_balance_hours(muf_no)
    }
    return jsonify(summary)

def create_custom_bitmap(text, width=160, height=32):
    img = Image.new('1', (width, height), color=0)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()

    w, h = font.getmask(text).size
    x = (width - w) // 2
    y = (height - h) // 2
    draw.text((x, y), text, fill=1, font=font)
    return img

def image_to_hex(img):
    width, height = img.size
    pixels = img.load()
    bits = []
    for y in range(height):
        for x in range(width):
            bits.append('1' if pixels[x, y] else '0')

    hex_str = ''
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        byte_str = ''.join(byte_bits)
        byte_val = int(byte_str, 2)
        hex_str += f'{byte_val:02x}'
    return hex_str

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
