from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'regular'

matrix = RGBMatrix(options=options)

while True:
    matrix.Fill(255, 0, 0)  # 全红
    time.sleep(1)
    matrix.Clear()
    matrix.Fill(0, 255, 0)  # 全绿
    time.sleep(1)
    matrix.Clear()
    matrix.Fill(0, 0, 255)  # 全蓝
    time.sleep(1)
