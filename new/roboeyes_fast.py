"""
Fast RoboEyes using NumPy for high performance on Raspberry Pi
This version uses NumPy arrays instead of PIL for 10x+ faster rendering

Ported from MicroPython RoboEyes by mchobby
Original: https://github.com/mchobby/micropython-roboeyes
Arduino origin: https://github.com/FluxGarage/RoboEyes

Copyright (C) 2024 Dennis Hoelscher - www.fluxgarage.com (Arduino Version)
Copyright (C) 2025 Meurisse Dominique - shop.mchobby.be (MicroPython Version)
Copyright (C) 2025 Python/NumPy Fast Version for Raspberry Pi

GNU General Public License <https://www.gnu.org/licenses/>.
"""

import time
import random
import numpy as np
from PIL import Image

# Mood constants
DEFAULT = 0
TIRED = 1
ANGRY = 2
HAPPY = 3
FROZEN = 4
SCARY = 5
CURIOUS = 6
SAD = 7

# Direction constants
N, NE, E, SE, S, SW, W, NW = 1, 2, 3, 4, 5, 6, 7, 8

# Boolean constants
ON = True
OFF = False


class StepData:
    """Represents a single sequence step"""
    def __init__(self, owner_seq, ms_timing, callback):
        self.done = False
        self.ms_timing = ms_timing
        self.callback = callback
        self.owner_seq = owner_seq
    
    def update(self, ticks):
        if self.done:
            return
        if ticks - self.owner_seq._start < self.ms_timing:
            return
        self.callback(self.owner_seq.owner)
        self.done = True


class Sequence:
    """A sequence of timed animation steps"""
    def __init__(self, owner, name):
        self.steps = []
        self.owner = owner
        self.name = name
        self._start = None
    
    def step(self, ms_timing, callback):
        """Add a step to the sequence"""
        self.steps.append(StepData(self, ms_timing, callback))
    
    def start(self):
        """Start the sequence"""
        self._start = int(time.time() * 1000)
    
    def reset(self):
        """Reset the sequence"""
        self._start = None
        for s in self.steps:
            s.done = False
    
    @property
    def done(self):
        """Check if all steps are complete"""
        if self._start is None:
            return True
        return all(s.done for s in self.steps)
    
    def update(self, ticks):
        """Update sequence steps"""
        if self._start is None:
            return
        for s in self.steps:
            if not s.done:
                s.update(ticks)


class Sequences:
    """Collection of animation sequences"""
    def __init__(self, owner):
        self.sequences = []
        self.owner = owner
    
    def add(self, name):
        """Add a new sequence"""
        seq = Sequence(self.owner, name)
        self.sequences.append(seq)
        return seq
    
    @property
    def done(self):
        """Check if all sequences are complete"""
        return all(seq.done for seq in self.sequences)
    
    def update(self):
        """Update all sequences"""
        ticks = int(time.time() * 1000)
        for seq in self.sequences:
            seq.update(ticks)


class FastRoboEyes:
    """Optimized RoboEyes using NumPy for fast rendering"""
    
    def __init__(self, display, width=320, height=240, frame_rate=60, bgcolor=(0,0,0), fgcolor=(173, 216, 230)):
        self.display = display
        self.screen_width = width
        self.screen_height = height
        self.bgcolor_tuple = bgcolor
        self.fgcolor_tuple = fgcolor
        self.bgcolor = np.array(bgcolor, dtype=np.uint8)
        self.fgcolor = np.array(fgcolor, dtype=np.uint8)
        
        # Create numpy array buffer
        self.buffer = np.zeros((height, width, 3), dtype=np.uint8)
        self.buffer[:] = self.bgcolor
        
        # Frame timing
        self.fps_timer = 0
        self.frame_interval = 1000 // frame_rate
        
        # Sequences for timed animations
        self.sequences = Sequences(self)
        
        # Position tracking
        self._position = 0
        
        # Mood flags
        self._mood = DEFAULT
        self.tired = False
        self.angry = False
        self.happy = False
        self._curious = False
        self._cyclops = False
        
        # Eye open states
        self.eye_l_open = False
        self.eye_r_open = False
        
        # Default geometry
        self.space_between_default = 10
        self.eye_l_width_default = 36
        self.eye_l_height_default = 36
        self.eye_r_width_default = 36
        self.eye_r_height_default = 36
        self.eye_l_border_radius_default = 8
        self.eye_r_border_radius_default = 8
        
        # Current geometry (start with closed eyes)
        self.eye_l_width_current = self.eye_l_width_default
        self.eye_l_height_current = 1
        self.eye_r_width_current = self.eye_r_width_default
        self.eye_r_height_current = 1
        self.eye_l_border_radius_current = self.eye_l_border_radius_default
        self.eye_r_border_radius_current = self.eye_r_border_radius_default
        self.space_between_current = self.space_between_default
        
        # Target geometry
        self.eye_l_width_next = self.eye_l_width_default
        self.eye_l_height_next = self.eye_l_height_default
        self.eye_r_width_next = self.eye_r_width_default
        self.eye_r_height_next = self.eye_r_height_default
        self.eye_l_border_radius_next = self.eye_l_border_radius_default
        self.eye_r_border_radius_next = self.eye_r_border_radius_default
        self.space_between_next = self.space_between_default
        
        # Height offsets (for curious mode)
        self.eye_l_height_offset = 0
        self.eye_r_height_offset = 0
        
        # Eye positions
        self.eye_l_x_default = int(((self.screen_width) - (self.eye_l_width_default + self.space_between_default + self.eye_r_width_default)) / 2)
        self.eye_l_y_default = int((self.screen_height - self.eye_l_height_default) / 2)
        self.eye_l_x = self.eye_l_x_default
        self.eye_l_y = self.eye_l_y_default
        self.eye_l_x_next = self.eye_l_x
        self.eye_l_y_next = self.eye_l_y
        
        self.eye_r_x_default = self.eye_l_x + self.eye_l_width_current + self.space_between_default
        self.eye_r_y_default = self.eye_l_y
        self.eye_r_x = self.eye_r_x_default
        self.eye_r_y = self.eye_r_y_default
        self.eye_r_x_next = self.eye_r_x
        self.eye_r_y_next = self.eye_r_y
        
        # Eyelids
        self.eyelids_height_max = int(self.eye_l_height_default / 2)
        self.eyelids_tired_height = 0
        self.eyelids_tired_height_next = 0
        self.eyelids_angry_height = 0
        self.eyelids_angry_height_next = 0
        self.eyelids_happy_bottom_offset = 0
        self.eyelids_happy_bottom_offset_next = 0
        
        # Flickering
        self.h_flicker = False
        self.h_flicker_amplitude = 0
        self.h_flicker_alternate = False
        self.v_flicker = False
        self.v_flicker_amplitude = 0
        self.v_flicker_alternate = False
        
        # Auto blinker
        self.autoblinker = False
        self.blink_interval = 3
        self.blink_interval_variation = 2
        self.blink_timer = 0
        
        # Idle mode
        self.idle = False
        self.idle_interval = 1
        self.idle_interval_variation = 3
        self.idle_animation_timer = 0
        
        # Confused animation
        self._confused = False
        self.confused_animation_timer = 0
        self.confused_animation_duration = 500
        self.confused_toggle = True
        
        # Laugh animation
        self._laugh = False
        self.laugh_animation_timer = 0
        self.laugh_animation_duration = 500
        self.laugh_toggle = True
        
        # Frame timing
        self.last_update = time.time()
        
    # -------------------------
    # Public Methods
    # -------------------------
    
    def set_framerate(self, fps):
        """Set the frame rate"""
        self.frame_interval = 1000 // fps
    
    def eyes_width(self, left_eye=None, right_eye=None):
        """Set eye width"""
        if left_eye is not None:
            self.eye_l_width_next = left_eye
            self.eye_l_width_default = left_eye
        if right_eye is not None:
            self.eye_r_width_next = right_eye
            self.eye_r_width_default = right_eye
    
    def eyes_height(self, left_eye=None, right_eye=None):
        """Set eye height"""
        if left_eye is not None:
            self.eye_l_height_next = left_eye
            self.eye_l_height_default = left_eye
        if right_eye is not None:
            self.eye_r_height_next = right_eye
            self.eye_r_height_default = right_eye
    
    def eyes_radius(self, left_eye=None, right_eye=None):
        """Set border radius"""
        if left_eye is not None:
            self.eye_l_border_radius_next = left_eye
            self.eye_l_border_radius_default = left_eye
        if right_eye is not None:
            self.eye_r_border_radius_next = right_eye
            self.eye_r_border_radius_default = right_eye
    
    def eyes_spacing(self, space):
        """Set spacing between eyes"""
        self.space_between_next = space
        self.space_between_default = space
    
    @property
    def mood(self):
        """Get current mood"""
        return self._mood
    
    @mood.setter
    def mood(self, value):
        """Set mood"""
        self._mood = value
        self.tired = (value == TIRED)
        self.angry = (value == ANGRY)
        self.happy = (value == HAPPY)
    
    @property
    def curious(self):
        """Get curious mode"""
        return self._curious
    
    @curious.setter
    def curious(self, enable):
        """Set curious mode"""
        self._curious = enable
    
    def set_curious(self, value):
        """Set curious mode (callable)"""
        self.curious = value
    
    @property
    def cyclops(self):
        """Get cyclops mode"""
        return self._cyclops
    
    @cyclops.setter
    def cyclops(self, enabled):
        """Set cyclops mode"""
        self._cyclops = enabled
    
    def set_cyclops(self, value):
        """Set cyclops mode (callable)"""
        self.cyclops = value
    
    def horiz_flicker(self, enable, amplitude=None):
        """Enable horizontal flickering"""
        self.h_flicker = enable
        if amplitude is not None:
            self.h_flicker_amplitude = amplitude
    
    def vert_flicker(self, enable, amplitude=None):
        """Enable vertical flickering"""
        self.v_flicker = enable
        if amplitude is not None:
            self.v_flicker_amplitude = amplitude
    
    def get_screen_constraint_x(self):
        """Get max X position for left eye"""
        return self.screen_width - self.eye_l_width_current - self.space_between_current - self.eye_r_width_current
    
    def get_screen_constraint_y(self):
        """Get max Y position for eyes"""
        return self.screen_height - self.eye_l_height_default
    
    def set_auto_blinker(self, active, interval=None, variation=None):
        """Set auto blinker mode"""
        self.autoblinker = active
        if interval is not None:
            self.blink_interval = interval
        if variation is not None:
            self.blink_interval_variation = variation
    
    def set_idle_mode(self, active, interval=None, variation=None):
        """Set idle mode"""
        self.idle = active
        if interval is not None:
            self.idle_interval = interval
        if variation is not None:
            self.idle_interval_variation = variation
    
    @property
    def position(self):
        """Get current position"""
        return self._position
    
    @position.setter
    def position(self, direction):
        """Set eye position by direction"""
        max_x = self.get_screen_constraint_x()
        max_y = self.get_screen_constraint_y()
        
        if direction == N:
            self.eye_l_x_next = max_x // 2
            self.eye_l_y_next = 0
        elif direction == NE:
            self.eye_l_x_next = max_x
            self.eye_l_y_next = 0
        elif direction == E:
            self.eye_l_x_next = max_x
            self.eye_l_y_next = max_y // 2
        elif direction == SE:
            self.eye_l_x_next = max_x
            self.eye_l_y_next = max_y
        elif direction == S:
            self.eye_l_x_next = max_x // 2
            self.eye_l_y_next = max_y
        elif direction == SW:
            self.eye_l_x_next = 0
            self.eye_l_y_next = max_y
        elif direction == W:
            self.eye_l_x_next = 0
            self.eye_l_y_next = max_y // 2
        elif direction == NW:
            self.eye_l_x_next = 0
            self.eye_l_y_next = 0
        else:
            self.eye_l_x_next = max_x // 2
            self.eye_l_y_next = max_y // 2
        
        self._position = direction
    
    # -------------------------
    # Animation Methods
    # -------------------------
    
    def close(self, left=None, right=None):
        """Close eyes"""
        if left is None and right is None:
            self.eye_l_height_next = 1
            self.eye_r_height_next = 1
            self.eye_l_open = False
            self.eye_r_open = False
        else:
            if left is not None:
                self.eye_l_height_next = 1
                self.eye_l_open = False
            if right is not None:
                self.eye_r_height_next = 1
                self.eye_r_open = False
    
    def open(self, left=None, right=None):
        """Open eyes"""
        if left is None and right is None:
            self.eye_l_open = True
            self.eye_r_open = True
        else:
            if left is not None:
                self.eye_l_open = True
            if right is not None:
                self.eye_r_open = True
    
    def blink(self, left=None, right=None):
        """Trigger blink animation"""
        if left is None and right is None:
            self.close()
            self.open()
        else:
            self.close(left, right)
            self.open(left, right)
    
    def confuse(self):
        """Play confused animation"""
        self._confused = True
    
    def laugh(self):
        """Play laugh animation"""
        self._laugh = True
    
    def wink(self, left=None, right=None):
        """Wink one eye"""
        if not (left or right):
            raise ValueError("wink requires left or right")
        self.autoblinker = False
        self.idle = False
        self.blink(left=left, right=right)
    
    # -------------------------
    # Drawing Helpers
    # -------------------------
    
    def draw_rounded_rect(self, x, y, w, h, r, color):
        """Draw a filled rounded rectangle using NumPy with proper rounded corners"""
        x, y, w, h, r = int(x), int(y), int(w), int(h), int(r)
        
        # Clamp radius to half of smaller dimension
        r = min(r, w // 2, h // 2)
        
        if r <= 0 or w <= 0 or h <= 0:
            # Fall back to simple rectangle
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(self.screen_width, x + w)
            y2 = min(self.screen_height, y + h)
            if x2 > x1 and y2 > y1:
                self.buffer[y1:y2, x1:x2] = color
            return
        
        # Draw the main rectangular sections
        # Top rectangle
        y1 = max(0, y)
        y2 = min(self.screen_height, y + r)
        x1 = max(0, x + r)
        x2 = min(self.screen_width, x + w - r)
        if x2 > x1 and y2 > y1:
            self.buffer[y1:y2, x1:x2] = color
        
        # Middle rectangle (full width)
        y1 = max(0, y + r)
        y2 = min(self.screen_height, y + h - r)
        x1 = max(0, x)
        x2 = min(self.screen_width, x + w)
        if x2 > x1 and y2 > y1:
            self.buffer[y1:y2, x1:x2] = color
        
        # Bottom rectangle
        y1 = max(0, y + h - r)
        y2 = min(self.screen_height, y + h)
        x1 = max(0, x + r)
        x2 = min(self.screen_width, x + w - r)
        if x2 > x1 and y2 > y1:
            self.buffer[y1:y2, x1:x2] = color
        
        # Draw four rounded corners using circle equation
        self._draw_circle_corner(x + r, y + r, r, color, 'tl')  # Top-left
        self._draw_circle_corner(x + w - r, y + r, r, color, 'tr')  # Top-right
        self._draw_circle_corner(x + r, y + h - r, r, color, 'bl')  # Bottom-left
        self._draw_circle_corner(x + w - r, y + h - r, r, color, 'br')  # Bottom-right
    
    def _draw_circle_corner(self, cx, cy, r, color, corner):
        """Draw a filled quarter circle for rounded corners"""
        cx, cy, r = int(cx), int(cy), int(r)
        
        # Determine which quadrant to fill
        for dy in range(-r, r + 1):
            py = cy + dy
            if py < 0 or py >= self.screen_height:
                continue
            
            # Calculate x extent using circle equation: x^2 + y^2 = r^2
            dx_max = int(np.sqrt(max(0, r * r - dy * dy)))
            
            if corner == 'tl':  # Top-left
                x_start = max(0, cx - dx_max)
                x_end = min(self.screen_width, cx + 1)
            elif corner == 'tr':  # Top-right
                x_start = max(0, cx)
                x_end = min(self.screen_width, cx + dx_max + 1)
            elif corner == 'bl':  # Bottom-left
                x_start = max(0, cx - dx_max)
                x_end = min(self.screen_width, cx + 1)
            else:  # 'br' Bottom-right
                x_start = max(0, cx)
                x_end = min(self.screen_width, cx + dx_max + 1)
            
            if x_end > x_start:
                self.buffer[py, x_start:x_end] = color
    
    def fill_triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Draw filled triangle using NumPy (simplified scanline fill)"""
        x0, y0, x1, y1, x2, y2 = int(x0), int(y0), int(x1), int(y1), int(x2), int(y2)
        
        # Sort vertices by y coordinate
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        if y0 > y2:
            x0, y0, x2, y2 = x2, y2, x0, y0
        if y1 > y2:
            x1, y1, x2, y2 = x2, y2, x1, y1
        
        # Scanline fill
        if y1 == y2:
            # Bottom-flat triangle
            self._fill_bottom_flat_triangle(x0, y0, x1, y1, x2, y2, color)
        elif y0 == y1:
            # Top-flat triangle
            self._fill_top_flat_triangle(x0, y0, x1, y1, x2, y2, color)
        else:
            # General case - split into two triangles
            x3 = int(x0 + ((y1 - y0) / (y2 - y0 + 0.001)) * (x2 - x0))
            y3 = y1
            self._fill_bottom_flat_triangle(x0, y0, x1, y1, x3, y3, color)
            self._fill_top_flat_triangle(x1, y1, x3, y3, x2, y2, color)
    
    def _fill_bottom_flat_triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Helper for triangle fill"""
        if y1 == y0:
            return
        invslope1 = (x1 - x0) / (y1 - y0 + 0.001)
        invslope2 = (x2 - x0) / (y2 - y0 + 0.001)
        
        curx1 = x0
        curx2 = x0
        
        for scanlineY in range(y0, y1 + 1):
            if 0 <= scanlineY < self.screen_height:
                x_start = max(0, min(int(curx1), int(curx2)))
                x_end = min(self.screen_width, max(int(curx1), int(curx2)) + 1)
                if x_start < x_end:
                    self.buffer[scanlineY, x_start:x_end] = color
            curx1 += invslope1
            curx2 += invslope2
    
    def _fill_top_flat_triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Helper for triangle fill"""
        if y2 == y0:
            return
        invslope1 = (x2 - x0) / (y2 - y0 + 0.001)
        invslope2 = (x2 - x1) / (y2 - y1 + 0.001)
        
        curx1 = x2
        curx2 = x2
        
        for scanlineY in range(y2, y0 - 1, -1):
            if 0 <= scanlineY < self.screen_height:
                x_start = max(0, min(int(curx1), int(curx2)))
                x_end = min(self.screen_width, max(int(curx1), int(curx2)) + 1)
                if x_start < x_end:
                    self.buffer[scanlineY, x_start:x_end] = color
            curx1 -= invslope1
            curx2 -= invslope2
    
    # -------------------------
    # Main Update and Rendering
    # -------------------------
    
    def update(self):
        """Main update loop - call this regularly"""
        # Check sequences
        self.sequences.update()
        
        # Frame rate limiting
        now = int(time.time() * 1000)
        if now - self.fps_timer >= self.frame_interval:
            self.draw_eyes()
            self.fps_timer = now
    
    def draw_eyes(self):
        """Main drawing method with all animations"""
        # Clear buffer
        self.buffer[:] = self.bgcolor
        
        now = int(time.time() * 1000)
        
        # Handle curious mode (outer eye gets larger when looking left/right)
        if self._curious:
            if self.eye_l_x_next <= 10:
                self.eye_l_height_offset = 8
            elif (self.eye_l_x_next >= self.get_screen_constraint_x() - 10) and self._cyclops:
                self.eye_l_height_offset = 8
            else:
                self.eye_l_height_offset = 0
            
            if self.eye_r_x_next >= (self.screen_width - self.eye_r_width_current - 10):
                self.eye_r_height_offset = 8
            else:
                self.eye_r_height_offset = 0
        else:
            self.eye_l_height_offset = 0
            self.eye_r_height_offset = 0
        
        # Interpolate geometry (smooth transitions)
        self.eye_l_height_current = (self.eye_l_height_current + self.eye_l_height_next + self.eye_l_height_offset) // 2
        self.eye_l_y += (self.eye_l_height_default - self.eye_l_height_current) // 2
        self.eye_l_y -= self.eye_l_height_offset // 2
        
        self.eye_r_height_current = (self.eye_r_height_current + self.eye_r_height_next + self.eye_r_height_offset) // 2
        self.eye_r_y += (self.eye_r_height_default - self.eye_r_height_current) // 2
        self.eye_r_y -= self.eye_r_height_offset // 2
        
        # Open eyes if needed
        if self.eye_l_open:
            if self.eye_l_height_current <= (1 + self.eye_l_height_offset):
                self.eye_l_height_next = self.eye_l_height_default
        
        if self.eye_r_open:
            if self.eye_r_height_current <= (1 + self.eye_r_height_offset):
                self.eye_r_height_next = self.eye_r_height_default
        
        # Widths
        self.eye_l_width_current = (self.eye_l_width_current + self.eye_l_width_next) // 2
        self.eye_r_width_current = (self.eye_r_width_current + self.eye_r_width_next) // 2
        
        # Spacing
        self.space_between_current = (self.space_between_current + self.space_between_next) // 2
        
        # Positions
        self.eye_l_x = (self.eye_l_x + self.eye_l_x_next) // 2
        self.eye_l_y = (self.eye_l_y + self.eye_l_y_next) // 2
        
        self.eye_r_x_next = self.eye_l_x_next + self.eye_l_width_current + self.space_between_current
        self.eye_r_y_next = self.eye_l_y_next
        self.eye_r_x = (self.eye_r_x + self.eye_r_x_next) // 2
        self.eye_r_y = (self.eye_r_y + self.eye_r_y_next) // 2
        
        # Border radius
        self.eye_l_border_radius_current = (self.eye_l_border_radius_current + self.eye_l_border_radius_next) // 2
        self.eye_r_border_radius_current = (self.eye_r_border_radius_current + self.eye_r_border_radius_next) // 2
        
        # Apply macro animations
        if self.autoblinker:
            if now - self.blink_timer >= 0:
                self.blink()
                self.blink_timer = now + (self.blink_interval * 1000) + (random.randint(0, self.blink_interval_variation) * 1000)
        
        # Laughing
        if self._laugh:
            if self.laugh_toggle:
                self.vert_flicker(True, 5)
                self.laugh_animation_timer = now
                self.laugh_toggle = False
            elif now - self.laugh_animation_timer >= self.laugh_animation_duration:
                self.vert_flicker(False, 0)
                self.laugh_toggle = True
                self._laugh = False
        
        # Confused
        if self._confused:
            if self.confused_toggle:
                self.horiz_flicker(True, 20)
                self.confused_animation_timer = now
                self.confused_toggle = False
            elif now - self.confused_animation_timer >= self.confused_animation_duration:
                self.horiz_flicker(False, 0)
                self.confused_toggle = True
                self._confused = False
        
        # Idle mode
        if self.idle:
            if now - self.idle_animation_timer >= 0:
                self.eye_l_x_next = random.randint(0, self.get_screen_constraint_x())
                self.eye_l_y_next = random.randint(0, self.get_screen_constraint_y())
                self.idle_animation_timer = now + (self.idle_interval * 1000) + (random.randint(0, self.idle_interval_variation) * 1000)
        
        # Horizontal flicker
        if self.h_flicker:
            if self.h_flicker_alternate:
                self.eye_l_x += self.h_flicker_amplitude
                self.eye_r_x += self.h_flicker_amplitude
            else:
                self.eye_l_x -= self.h_flicker_amplitude
                self.eye_r_x -= self.h_flicker_amplitude
            self.h_flicker_alternate = not self.h_flicker_alternate
        
        # Vertical flicker
        if self.v_flicker:
            if self.v_flicker_alternate:
                self.eye_l_y += self.v_flicker_amplitude
                self.eye_r_y += self.v_flicker_amplitude
            else:
                self.eye_l_y -= self.v_flicker_amplitude
                self.eye_r_y -= self.v_flicker_amplitude
            self.v_flicker_alternate = not self.v_flicker_alternate
        
        # Draw eyes
        self.draw_rounded_rect(self.eye_l_x, self.eye_l_y, self.eye_l_width_current, 
                       self.eye_l_height_current, self.eye_l_border_radius_current, self.fgcolor)
        
        if not self._cyclops:
            self.draw_rounded_rect(self.eye_r_x, self.eye_r_y, self.eye_r_width_current, 
                           self.eye_r_height_current, self.eye_r_border_radius_current, self.fgcolor)
        
        # Prepare mood transitions
        if self.tired:
            self.eyelids_tired_height_next = self.eye_l_height_current // 2
            self.eyelids_angry_height_next = 0
        else:
            self.eyelids_tired_height_next = 0
        
        if self.angry:
            self.eyelids_angry_height_next = self.eye_l_height_current // 2
            self.eyelids_tired_height_next = 0
        else:
            self.eyelids_angry_height_next = 0
        
        if self.happy:
            self.eyelids_happy_bottom_offset_next = self.eye_l_height_current // 2
        else:
            self.eyelids_happy_bottom_offset_next = 0
        
        # Draw tired eyelids
        self.eyelids_tired_height = (self.eyelids_tired_height + self.eyelids_tired_height_next) // 2
        if not self._cyclops:
            self.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x, self.eye_l_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
            self.fill_triangle(self.eye_r_x, self.eye_r_y - 1,
                            self.eye_r_x + self.eye_r_width_current, self.eye_r_y - 1,
                            self.eye_r_x + self.eye_r_width_current, self.eye_r_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
        else:
            self.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x, self.eye_l_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
            self.fill_triangle(self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
        
        # Draw angry eyelids
        self.eyelids_angry_height = (self.eyelids_angry_height + self.eyelids_angry_height_next) // 2
        if not self._cyclops:
            self.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
            self.fill_triangle(self.eye_r_x, self.eye_r_y - 1,
                            self.eye_r_x + self.eye_r_width_current, self.eye_r_y - 1,
                            self.eye_r_x, self.eye_r_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
        else:
            self.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
            self.fill_triangle(self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
        
        # Draw happy bottom eyelids
        self.eyelids_happy_bottom_offset = (self.eyelids_happy_bottom_offset + self.eyelids_happy_bottom_offset_next) // 2
        self.draw_rounded_rect(self.eye_l_x - 1,
                      (self.eye_l_y + self.eye_l_height_current) - self.eyelids_happy_bottom_offset + 1,
                      self.eye_l_width_current + 2,
                      self.eye_l_height_default,
                      self.eye_l_border_radius_current,
                      self.bgcolor)
        
        if not self._cyclops:
            self.draw_rounded_rect(self.eye_r_x - 1,
                          (self.eye_r_y + self.eye_r_height_current) - self.eyelids_happy_bottom_offset + 1,
                          self.eye_r_width_current + 2,
                          self.eye_r_height_default,
                          self.eye_r_border_radius_current,
                          self.bgcolor)
        
        # Display the frame
        if self.display:
            self.display.image(self.get_image())
    
    def get_image(self):
        """Convert buffer to PIL Image for display"""
        return Image.fromarray(self.buffer, 'RGB')
    
    def show(self):
        """Display the current frame"""
        if self.display:
            self.display.image(self.get_image())


__all__ = ['FastRoboEyes', 'DEFAULT', 'TIRED', 'ANGRY', 'HAPPY', 'FROZEN', 'SCARY', 'CURIOUS', 'SAD',
           'ON', 'OFF', 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'Sequences']
