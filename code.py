# 保存为 /home/pi/gwim-scanner/code.py
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time
import requests

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'regular'

matrix = RGBMatrix(options=options)
font = graphics.Font()
font.LoadFont("/home/pi/gwim-scanner/fonts/helvB12-vp.bdf")

def display_data(data):
    canvas = matrix.CreateFrameCanvas()
    muf = str(data.get("muf_no", "-"))[-6:]
    total = str(data.get("total_carton_needed", "-"))
    target = str(data.get("target_hour", "-"))
    avg = str(data.get("avg_hourly_output", "-"))
    bal_ctn = str(data.get("balance_carton", "-"))
    bal_hr = str(data.get("balance_hours", "-"))

    color = graphics.Color(0, 255, 0) if avg.isdigit() and target.isdigit() and int(avg) >= int(target) else graphics.Color(255, 0, 0)
    graphics.DrawText(canvas, font, 0, 10, graphics.Color(0, 255, 255), f"MUF:{muf}")
    graphics.DrawText(canvas, font, 0, 20, graphics.Color(255, 255, 255), f"TOT:{total}")
    graphics.DrawText(canvas, font, 0, 30, graphics.Color(255, 255, 0), f"TGT:{target}")
    graphics.DrawText(canvas, font, 0, 40, color, f"AVG:{avg}")
    graphics.DrawText(canvas, font, 0, 50, graphics.Color(255, 255, 0), f"BAL:{bal_ctn}")
    graphics.DrawText(canvas, font, 0, 60, graphics.Color(0, 0, 255), f"HRS:{bal_hr}")

    matrix.SwapOnVSync(canvas)

while True:
    try:
        resp = requests.get("http://localhost/summary", timeout=4)
        data = resp.json()
        display_data(data)
    except Exception as e:
        print("❌ Error:", e)
    time.sleep(3)
