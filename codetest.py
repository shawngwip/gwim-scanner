from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.hardware_mapping = 'regular'
# options.disable_hardware_pulsing = True  # 不再支持，可忽略

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

font = graphics.Font()
try:
    font.LoadFont("/home/pi/gwim-scanner/fonts/helvB12-vp.bdf")
    print("✅ Font loaded successfully.")
except Exception as e:
    print(f"❌ Font Load Error: {e}")
    exit(1)

textColor = graphics.Color(255, 255, 0)  # 黄色
pos = canvas.width

while True:
    canvas.Clear()
    pos -= 1
    if pos < -100:
        pos = canvas.width
    graphics.DrawText(canvas, font, pos, 20, textColor, "HELLO WORLD")
    time.sleep(0.05)
    canvas = matrix.SwapOnVSync(canvas)
