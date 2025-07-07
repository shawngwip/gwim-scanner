from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time

# 设置面板参数（你4片横拼，32行 × 64列 × 4 = 256x32）
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 4
options.parallel = 1
options.hardware_mapping = 'regular'

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# 用内建字体，不加载 .bdf
font = graphics.Font()
font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/6x13.bdf")
color = graphics.Color(255, 255, 0)

pos = 10

while True:
    canvas.Clear()
    graphics.DrawText(canvas, font, pos, 20, color, "GWIM READY")
    pos -= 1
    if pos < -100:
        pos = 64
    time.sleep(0.05)
    canvas = matrix.SwapOnVSync(canvas)
