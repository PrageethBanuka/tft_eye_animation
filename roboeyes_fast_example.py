"""
Fast RoboEyes Example - Optimized for Raspberry Pi
Uses NumPy for 10x+ faster rendering
"""

import time
import threading
from PIL import Image
import digitalio
import board
import busio
import adafruit_rgb_display.ili9341 as ili9341
from roboeyes_fast import FastRoboEyes, DEFAULT, HAPPY, ANGRY, TIRED, ON

print("Initializing Fast RoboEyes...")

# -------------------------
# Initialize display
# -------------------------
rst = digitalio.DigitalInOut(board.D24)
rst.direction = digitalio.Direction.OUTPUT
rst.value = False
time.sleep(0.1)
rst.value = True
time.sleep(0.1)

spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D25)
led = digitalio.DigitalInOut(board.D18)
led.direction = digitalio.Direction.OUTPUT
led.value = False

# Display settings - rotation=90 for landscape (fixes noise)
display = ili9341.ILI9341(
    spi, cs=cs, dc=dc, rst=rst,
    width=320, height=240,
    rotation=0,
    baudrate=64000000  # Maximum speed
)

WIDTH, HEIGHT = display.width, display.height
print(f"Display: {WIDTH}x{HEIGHT}")

# Clear and enable backlight
display.fill(0x0000)
time.sleep(0.1)
led.value = True

# -------------------------
# Initialize Fast RoboEyes
# -------------------------
eyes = FastRoboEyes(
    display=None,  # We'll manually update
    width=WIDTH,
    height=HEIGHT,
    bgcolor=(0, 0, 0),
    fgcolor=(100, 200, 255)
)

# Enable auto-blink
eyes.set_auto_blinker(ON, interval=4, variation=2)

# Open eyes
eyes.open_eyes()
eyes.update()
display.image(eyes.get_image())

print("Fast RoboEyes ready!")
print("="*60)

# -------------------------
# User input thread
# -------------------------
user_input = None

def input_thread():
    global user_input
    while True:
        print("\nCommands: 0=DEFAULT, 1=HAPPY, 2=ANGRY, 3=TIRED, B=Blink, Q=Quit")
        inp = input("> ").upper().strip()
        user_input = inp
        if inp == "Q":
            break

threading.Thread(target=input_thread, daemon=True).start()

# -------------------------
# Main loop - FAST!
# -------------------------
mood_sequence = [DEFAULT, HAPPY, ANGRY, TIRED]
mood_names = ["DEFAULT", "HAPPY", "ANGRY", "TIRED"]
mood_index = 0
last_mood_change = time.time()
auto_cycle = True

frame_count = 0
fps_start = time.time()
display_frame_count = 0

# Display update throttling
last_display_update = time.time()
DISPLAY_FPS_TARGET = 20  # Update display at 20 FPS max
display_interval = 1.0 / DISPLAY_FPS_TARGET

try:
    print("Starting animation...")
    
    while True:
        # Update animation (fast - pure NumPy)
        eyes.update()
        frame_count += 1
        
        # Only update physical display at limited rate
        now = time.time()
        if now - last_display_update >= display_interval:
            display.image(eyes.get_image())
            last_display_update = now
            display_frame_count += 1
        
        # Show FPS every 100 animation frames
        if frame_count % 100 == 0:
            elapsed = now - fps_start
            if elapsed > 0:
                anim_fps = 100 / elapsed
                disp_fps = display_frame_count / elapsed
                print(f"[Anim: {anim_fps:.1f} FPS | Display: {disp_fps:.1f} FPS]")
            fps_start = now
            display_frame_count = 0
        
        # Handle user input
        if user_input:
            cmd = user_input
            user_input = None
            
            if cmd == "Q":
                break
            elif cmd == "0":
                eyes.mood = DEFAULT
                print("→ DEFAULT")
                auto_cycle = False
            elif cmd == "1":
                eyes.mood = HAPPY
                print("→ HAPPY")
                auto_cycle = False
            elif cmd == "2":
                eyes.mood = ANGRY
                print("→ ANGRY")
                auto_cycle = False
            elif cmd == "3":
                eyes.mood = TIRED
                print("→ TIRED")
                auto_cycle = False
            elif cmd == "B":
                eyes.blink()
                print("→ Blink")
            elif cmd == "A":
                auto_cycle = not auto_cycle
                print(f"→ Auto-cycle: {auto_cycle}")
        
        # Auto mood cycling every 20 seconds
        if auto_cycle and (now - last_mood_change) >= 20:
            mood_index = (mood_index + 1) % len(mood_sequence)
            eyes.mood = mood_sequence[mood_index]
            print(f"\n[AUTO] {mood_names[mood_index]}")
            last_mood_change = now
        
        # Small sleep to prevent 100% CPU usage
        time.sleep(0.001)

except KeyboardInterrupt:
    print("\nStopped")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("Clearing display...")
    display.image(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))
    led.value = False
    print("Done!")
