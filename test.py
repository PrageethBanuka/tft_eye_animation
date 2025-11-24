"""
RoboEyes Example for Raspberry Pi with ILI9341 Display - FIXED FOR RPI

Known issue: ILI9341 displays noise on Raspberry Pi but works fine on ESP32
Solution: Proper SPI configuration + display initialization sequence

Hardware:
- ILI9341 TFT display (240x320)
- Connect to Raspberry Pi SPI pins
"""

import time
import threading
from PIL import Image
import digitalio
import board
import busio
import adafruit_rgb_display.ili9341 as ili9341
from roboeyes import RoboEyes, DEFAULT, HAPPY, ANGRY, TIRED, CURIOUS, SAD, ON, OFF, N, E, S, W

print("Initializing ILI9341 display for Raspberry Pi...")

# -------------------------
# Initialize display - FIXED FOR RASPBERRY PI
# -------------------------

# Hardware reset first
rst = digitalio.DigitalInOut(board.D24)
rst.direction = digitalio.Direction.OUTPUT
rst.value = False
time.sleep(0.1)
rst.value = True
time.sleep(0.1)

# Initialize SPI with specific settings for ILI9341
# Key: polarity=0, phase=0 for ILI9341 compatibility
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Control pins
cs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D25)

# Backlight
led = digitalio.DigitalInOut(board.D18)
led.direction = digitalio.Direction.OUTPUT
led.value = False

# CRITICAL: Use rotation to fix display orientation and noise
# rotation=0  : Portrait (240x320) - may have noise at bottom
# rotation=90 : Landscape (320x240) - RECOMMENDED, often fixes noise
# rotation=180: Portrait inverted
# rotation=270: Landscape inverted

# Try rotation=90 first - this often fixes the noise issue!
display = ili9341.ILI9341(
    spi,
    cs=cs,
    dc=dc,
    rst=rst,
    width=320,
    height=240,
    rotation=0,  # Changed to landscape mode - often fixes noise!
    baudrate=24000000  # Stable speed for RPi
)

# Get actual display dimensions (should match rotation setting)
WIDTH, HEIGHT = display.width, display.height
print(f"Display size: {WIDTH} x {HEIGHT}")

# Clear display to black and enable backlight
print("Clearing display...")
display.fill(0x0000)  # Use fill() instead of image() for initial clear
time.sleep(0.2)
led.value = True
time.sleep(0.2)

# Verify display is working with a test pattern
print("Running display test...")
test_img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
display.image(test_img)
time.sleep(0.5)

# -------------------------
# Initialize RoboEyes
# -------------------------
print("Initializing RoboEyes...")

# Create RoboEyes WITHOUT display (we'll update display manually)
eyes = RoboEyes(
    display=None,  # Don't auto-update display
    width=WIDTH,
    height=HEIGHT,
    frame_rate=30,  # Higher internal frame rate
    bgcolor=(0, 0, 0),  # Pure black to avoid color noise
    fgcolor=(173, 216, 255)  # Light blue eyes
)

# Configure eye size (adjusted for landscape if rotation=90)
if WIDTH > HEIGHT:  # Landscape mode
    eyes.eyes_width(80, 80)
    eyes.eyes_height(80, 80)
    eyes.eyes_radius(15, 15)
    eyes.eyes_spacing(60)
else:  # Portrait mode
    eyes.eyes_width(80, 80)
    eyes.eyes_height(80, 80)
    eyes.eyes_radius(15, 15)
    eyes.eyes_spacing(40)

# -------------------------
# Initialize RoboEyes
# -------------------------
print("Initializing RoboEyes...")

# Create RoboEyes WITHOUT display (we'll update display manually)
eyes = RoboEyes(
    display=None,  # Don't auto-update display
    width=WIDTH,
    height=HEIGHT,
    frame_rate=30,  # Higher internal frame rate
    bgcolor=(0, 0, 0),  # Pure black to avoid color noise
    fgcolor=(173, 216, 255)  # Light blue eyes
)

# Configure eye size (adjusted for landscape if rotation=90)
if WIDTH > HEIGHT:  # Landscape mode
    eyes.eyes_width(80, 80)
    eyes.eyes_height(60, 60)
    eyes.eyes_radius(15, 15)
    eyes.eyes_spacing(40)
else:  # Portrait mode
    eyes.eyes_width(60, 60)
    eyes.eyes_height(60, 60)
    eyes.eyes_radius(12, 12)
    eyes.eyes_spacing(20)

# Enable auto-blink every 4-6 seconds
eyes.set_auto_blinker(ON, interval=4, variation=2)

# Disable idle mode - no random eye movement
eyes.set_idle_mode(OFF)

# Open eyes at startup
eyes.open()

# Force first frame render
eyes.update()
if eyes.frame_buffer:
    display.image(eyes.frame_buffer)
time.sleep(0.5)

print("\n" + "="*60)
print("RoboEyes initialized successfully!")
print(f"Display: {WIDTH}x{HEIGHT} @ rotation={display.rotation}")
print("Optimization: Skip-frame rendering enabled")
print("="*60)
print("\nStarting with DEFAULT mood...")

# -------------------------
# User input thread
# -------------------------
user_input = None


def input_thread():
    global user_input
    while True:
        print("\nAvailable commands:")
        print("  0 or DEFAULT - Default mood")
        print("  1 or HAPPY - Happy mood")
        print("  2 or ANGRY - Angry mood")
        print("  3 or TIRED - Tired mood")
        print("  4 or CURIOUS - Curious mood")
        print("  5 or SAD - Sad mood")
        print("  L - Laugh animation")
        print("  C - Confuse animation")
        print("  B - Blink")
        print("  N/E/S/W - Look North/East/South/West")
        print("  Q - Quit")
        
        inp = input("\nEnter command: ").upper().strip()
        user_input = inp
        if inp == "Q":
            break


threading.Thread(target=input_thread, daemon=True).start()

# -------------------------
# Main animation loop
# -------------------------
mood_sequence = [DEFAULT, HAPPY, ANGRY, TIRED, CURIOUS, SAD]
mood_names = ["DEFAULT", "HAPPY", "ANGRY", "TIRED", "CURIOUS", "SAD"]
mood_index = 0
last_mood_change = time.time()
auto_cycle = True

frame_count = 0
fps_start = time.time()
last_display_update = time.time()
display_update_interval = 0.05  # Update display every 50ms = 20 FPS max
skip_frames = 2  # Only update display every N animation frames
frame_skip_counter = 0

try:
    while True:
        # Update eyes animation state
        eyes.update()
        
        frame_count += 1
        frame_skip_counter += 1
        
        # Only update physical display every N frames to save time
        if frame_skip_counter >= skip_frames:
            if eyes.frame_buffer:
                display.image(eyes.frame_buffer)
            frame_skip_counter = 0
        
        # Show FPS every 100 frames
        if frame_count % 100 == 0:
            elapsed = time.time() - fps_start
            if elapsed > 0:
                actual_fps = 100 / elapsed
                display_fps = actual_fps / skip_frames
                print(f"[Animation FPS: {actual_fps:.1f} | Display FPS: {display_fps:.1f}]")
            fps_start = time.time()

        # Handle user input
        if user_input:
            cmd = user_input
            user_input = None
            
            if cmd == "Q":
                break
            elif cmd in ["0", "DEFAULT"]:
                eyes.mood = DEFAULT
                print("Mood: DEFAULT")
                auto_cycle = False
            elif cmd in ["1", "HAPPY"]:
                eyes.mood = HAPPY
                print("Mood: HAPPY")
                auto_cycle = False
            elif cmd in ["2", "ANGRY"]:
                eyes.mood = ANGRY
                print("Mood: ANGRY")
                auto_cycle = False
            elif cmd in ["3", "TIRED"]:
                eyes.mood = TIRED
                print("Mood: TIRED")
                auto_cycle = False
            elif cmd in ["4", "CURIOUS"]:
                eyes.mood = CURIOUS
                print("Mood: CURIOUS")
                auto_cycle = False
            elif cmd in ["5", "SAD"]:
                eyes.mood = SAD
                print("Mood: SAD")
                auto_cycle = False
            elif cmd == "L":
                eyes.laugh()
                print("Playing laugh animation")
            elif cmd == "C":
                eyes.confuse()
                print("Playing confuse animation")
            elif cmd == "B":
                eyes.blink()
                print("Blinking")
            elif cmd == "N":
                eyes.position = N
                print("Looking North")
            elif cmd == "E":
                eyes.position = E
                print("Looking East")
            elif cmd == "S":
                eyes.position = S
                print("Looking South")
            elif cmd == "W":
                eyes.position = W
                print("Looking West")
            elif cmd == "AUTO":
                auto_cycle = True
                print("Auto-cycling enabled")

        # Automatic mood cycling every 15 seconds (if enabled)
        if auto_cycle:
            elapsed = time.time() - last_mood_change
            if elapsed >= 60:
                mood_index = (mood_index + 1) % len(mood_sequence)
                eyes.mood = mood_sequence[mood_index]
                print(f"\n[AUTO] Mood: {mood_names[mood_index]}")
                last_mood_change = time.time()

        # No sleep - run as fast as possible

except KeyboardInterrupt:
    print("\nInterrupted by user")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

finally:
    # -------------------------
    # Clear display on exit
    # -------------------------
    print("Clearing display...")
    display.image(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))
    led.value = False
    print("Exiting...")
