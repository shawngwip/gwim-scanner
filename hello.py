from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import time

# 设置 LED 屏幕参数（为你量身定制）
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.gpio_mapping = 'regular'
options.scan_mode = 1            # ✅ 你的面板是 1/16S 扫描
options.hardware_pulsing = False

# 初始化 LED 屏幕
matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# 加载字体和颜色
font = graphics.Font()
font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/6x12.bdf")
color = graphics.Color(0, 255, 0)  # 绿色字体

# 清屏并绘制固定文字
canvas.Clear()
graphics.DrawText(canvas, font, 2, 20, color, "HELLO BP-AiS")
matrix.SwapOnVSync(canvas)

# 保持显示
while True:
    time.sleep(1)
