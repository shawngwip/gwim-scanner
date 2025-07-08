from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time

# === 配置 LED 屏幕参数（专为你面板设定）===
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.scan_mode = 1  # 你的是 P5 1/16 扫描
options.hardware_mapping = 'regular'
options.gpio_slowdown = 3
options.disable_hardware_pulsing = True

matrix = RGBMatrix(options=options)

# === 创建红色背景图像 ===
image = Image.new("RGB", (64, 32), (255, 0, 0))  # 红色背景
draw = ImageDraw.Draw(image)

# === 加载系统 TTF 字体（字体路径稳定）===
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)

# === 在图像中写字（白色） ===
draw.text((5, 8), "HELLO", font=font, fill=(255, 255, 255))

# === 显示在 LED 屏幕上 ===
matrix.SetImage(image)

# === 保持 15 秒不动（你会看到 HELLO）===
time.sleep(15)
