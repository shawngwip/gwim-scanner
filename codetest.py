from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import os
import time

# === Font loading logic ===
font = graphics.Font()
FONT_PATH = "/home/pi/gwim-scanner/fonts/helvB12-vp.bdf"

try:
    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError(f"Font file not found: {FONT_PATH}")
    font.LoadFont(FONT_PATH)
    print(f"✅ Font loaded successfully: {FONT_PATH}")
except Exception as e:
    print(f"❌ Font Load Error: {e}")
    exit(1)

# === LED matrix config ===
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'regular'
options.brightness = 80
options.gpio_slowdown = 2
options.pwm_lsb_nanoseconds = 130
options.disable_hardware_pulsing = True

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()
color = graphics.Color(255, 255, 0)

text = "HELLO"
pos = canvas.width

while True:
    canvas.Clear()
    pos -= 1
    if pos + len(text) * 10 < 0:
        pos = canvas.width
    graphics.DrawText(canvas, font, pos, 20, color, text)
    time.sleep(0.05)
    canvas = matrix.SwapOnVSync(canvas)
