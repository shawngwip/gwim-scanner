from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time

# 配置选项
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2  # 2块拼接（64*2 = 128宽）
options.parallel = 1
options.hardware_mapping = 'regular'  # 如果你是HUB75就用'regular'

matrix = RGBMatrix(options=options)

# 加载字体
font = graphics.Font()
font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/7x13.bdf")  # 用的是系统字体
color = graphics.Color(255, 0, 0)

# 显示文字
while True:
    matrix.Clear()
    graphics.DrawText(matrix, font, 10, 20, color, "HELLO GWIM")
    time.sleep(1)
