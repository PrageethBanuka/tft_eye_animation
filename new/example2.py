"""
Complete RoboEyes Fast Demo - All Features
Demonstrates all animations, moods, positions, and effects
"""

import time
import threading
from PIL import Image
import digitalio
import board
import busio
import adafruit_rgb_display.ili9341 as ili9341
from roboeyes_fast import (FastRoboEyes, DEFAULT, TIRED, ANGRY, HAPPY, CURIOUS, 
                           ON, OFF, N, NE, E, SE, S, SW, W, NW)

print("Initializing Complete RoboEyes Demo...")

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

display = ili9341.ILI9341(
    spi, cs=cs, dc=dc, rst=rst,
    width=320, height=240,
    rotation=0,  # Landscape mode
    baudrate=64000000
)

WIDTH, HEIGHT = display.width, display.height
print(f"Display: {WIDTH}x{HEIGHT}")

display.fill(0x0000)
time.sleep(0.1)
led.value = True

# -------------------------
# Initialize RoboEyes
# -------------------------
eyes = FastRoboEyes(
    display=None,
    width=WIDTH,
    height=HEIGHT,
    frame_rate=60,
    bgcolor=(0, 0, 0),
    fgcolor=(173, 216, 230)
)

# Set larger eye size
eyes.eyes_width(80, 80)
eyes.eyes_height(80, 80)
eyes.eyes_spacing(40)
eyes.eyes_radius(15, 15)

eyes.set_auto_blinker(True, interval=3, variation=2)
eyes.open()

print("\n=== Complete RoboEyes Demo ===")
print("All features with smooth NumPy rendering!")
print("="*60)

# -------------------------
# Demo sequence
# -------------------------
def setup_default():
    eyes.mood = DEFAULT
    eyes.set_curious(False)
    eyes.set_cyclops(False)
    eyes.set_idle_mode(False)

def setup_tired():
    eyes.mood = TIRED

def setup_angry():
    eyes.mood = ANGRY

def setup_happy():
    eyes.mood = HAPPY

def setup_curious():
    eyes.set_curious(True)
    eyes.position = E

def setup_cyclops():
    eyes.set_curious(False)
    eyes.set_cyclops(True)

def setup_look_around():
    eyes.set_cyclops(False)
    eyes.mood = DEFAULT

def animate_look_around(frame):
    eyes.position = [N, NE, E, SE, S, SW, W, NW][(frame // 30) % 8]

def animate_confuse(frame):
    if frame % 120 == 0:
        eyes.confuse()

def animate_laugh(frame):
    if frame % 120 == 0:
        eyes.laugh()

def setup_idle():
    eyes.set_idle_mode(True, interval=1, variation=2)

def setup_wink_left():
    eyes.set_idle_mode(False)
    eyes.set_auto_blinker(False)

def animate_wink_left(frame):
    if frame % 90 == 0:
        eyes.wink(left=ON)

def animate_wink_right(frame):
    if frame % 90 == 0:
        eyes.wink(right=ON)

def setup_custom_size():
    eyes.set_auto_blinker(True)
    eyes.eyes_width(50, 50)
    eyes.eyes_height(50, 50)
    eyes.eyes_spacing(20)

def setup_reset():
    eyes.eyes_width(80, 80)
    eyes.eyes_height(80, 80)
    eyes.eyes_spacing(40)
    eyes.mood = DEFAULT
    eyes.eyes_radius(15, 15)

demos = [
    {
        'name': 'Default - Auto-blink',
        'duration': 8,
        'setup': setup_default
    },
    {
        'name': 'Tired Mood',
        'duration': 5,
        'setup': setup_tired
    },
    {
        'name': 'Angry Mood',
        'duration': 5,
        'setup': setup_angry
    },
    {
        'name': 'Happy Mood',
        'duration': 5,
        'setup': setup_happy
    },
    {
        'name': 'Curious Mode (Look Right)',
        'duration': 5,
        'setup': setup_curious
    },
    {
        'name': 'Cyclops Mode',
        'duration': 5,
        'setup': setup_cyclops
    },
    {
        'name': 'Look Around (8 Directions)',
        'duration': 16,
        'setup': setup_look_around,
        'animation': animate_look_around
    },
    {
        'name': 'Confuse Animation',
        'duration': 8,
        'setup': None,
        'animation': animate_confuse
    },
    {
        'name': 'Laugh Animation',
        'duration': 8,
        'setup': None,
        'animation': animate_laugh
    },
    {
        'name': 'Idle Mode (Random Movement)',
        'duration': 10,
        'setup': setup_idle
    },
    {
        'name': 'Wink Left',
        'duration': 6,
        'setup': setup_wink_left,
        'animation': animate_wink_left
    },
    {
        'name': 'Wink Right',
        'duration': 6,
        'setup': None,
        'animation': animate_wink_right
    },
    {
        'name': 'Custom Eye Size',
        'duration': 5,
        'setup': setup_custom_size
    },
    {
        'name': 'Reset to Default',
        'duration': 5,
        'setup': setup_reset
    }
]

# -------------------------
# Main loop
# -------------------------
current_demo = 0
demo_start_time = time.time()
frame_count = 0
fps_start = time.time()
display_frame_count = 0
last_display_update = time.time()
display_interval = 1.0 / 20.0  # 20 FPS display updates

running = True

def input_thread():
    global running
    print("\nPress Enter to skip to next demo, 'q' to quit")
    while running:
        try:
            cmd = input().strip().lower()
            if cmd == 'q':
                running = False
        except:
            break

threading.Thread(target=input_thread, daemon=True).start()

try:
    # Start first demo
    print(f"\n▶ {demos[current_demo]['name']}")
    if 'setup' in demos[current_demo] and demos[current_demo]['setup']:
        demos[current_demo]['setup']()
    demo_start_time = time.time()
    
    while running:
        now = time.time()
        
        # Check if current demo is complete
        if now - demo_start_time >= demos[current_demo]['duration']:
            # Move to next demo
            current_demo = (current_demo + 1) % len(demos)
            print(f"\n▶ {demos[current_demo]['name']}")
            
            if 'setup' in demos[current_demo] and demos[current_demo]['setup']:
                demos[current_demo]['setup']()
            
            demo_start_time = now
            frame_count = 0
        
        # Run frame animation if defined
        if 'animation' in demos[current_demo] and demos[current_demo]['animation']:
            demos[current_demo]['animation'](frame_count)
        
        # Update eyes animation
        eyes.update()
        frame_count += 1
        
        # Throttle display updates
        if now - last_display_update >= display_interval:
            display.image(eyes.get_image())
            last_display_update = now
            display_frame_count += 1
        
        # Show FPS every 2 seconds
        if frame_count % 120 == 0:
            elapsed = now - fps_start
            if elapsed > 0:
                anim_fps = 120 / elapsed
                disp_fps = display_frame_count / elapsed
                print(f"  [Animation: {anim_fps:.1f} FPS | Display: {disp_fps:.1f} FPS]")
            fps_start = now
            display_frame_count = 0
        
        time.sleep(0.001)

except KeyboardInterrupt:
    print("\n\nStopped by user")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

finally:
    running = False
    print("\nCleaning up...")
    display.image(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))
    led.value = False
    print("Done!")
