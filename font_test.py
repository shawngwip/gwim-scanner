from rgbmatrix import graphics

try:
    font = graphics.Font()
    font.LoadFont("/home/pi/gwim-scanner/fonts/helvB12-vp.bdf")
    print("✅ Font loaded successfully")
except Exception as e:
    print(f"❌ Font Load Error: {e}")
