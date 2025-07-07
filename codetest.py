from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.gpio_slowdown = 4
options.hardware_mapping = 'regular'
options.disable_hardware_pulsing = True

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

font = graphics.Font()
try:
    font.LoadFont("/home/pi/gwim-scanner/fonts/helvB12-vp.bdf")
    print("✅ Font loaded successfully!")
except Exception as e:
    print(f"❌ Font Load Error: {e}")
    exit(1)

color = graphics.Color(255, 255, 0)
graphics.DrawText(canvas, font, 10, 20, color, "Hello!")
