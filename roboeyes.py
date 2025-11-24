"""
RoboEyes library for Python/Raspberry Pi

Ported from MicroPython RoboEyes by mchobby
Original: https://github.com/mchobby/micropython-roboeyes
Arduino origin: https://github.com/FluxGarage/RoboEyes

Copyright (C) 2024 Dennis Hoelscher - www.fluxgarage.com (Arduino Version)
Copyright (C) 2025 Meurisse Dominique - shop.mchobby.be (MicroPython Version)
Copyright (C) 2025 Python/PIL Port for Raspberry Pi

GNU General Public License <https://www.gnu.org/licenses/>.
"""

import time
import random
from PIL import Image, ImageDraw

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


class FBUtil:
    """Helper class for additional drawing methods"""
    def __init__(self, draw):
        self.draw = draw
    
    def fill_triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Draw a filled triangle"""
        self.draw.polygon([(x0, y0), (x1, y1), (x2, y2)], fill=color)
    
    def fill_rrect(self, x, y, w, h, r, color):
        """Draw a filled rounded rectangle"""
        self.draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=color)


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


class RoboEyes:
    """Main RoboEyes animation class for PIL/Pillow displays on Raspberry Pi"""
    
    def __init__(self, display, width=240, height=320, frame_rate=60, bgcolor=(0,0,0), fgcolor=(173, 216, 230)):
        """
        Initialize RoboEyes
        
        Args:
            display: Display object with .image() method (e.g., Adafruit ST7789)
            width: Screen width in pixels
            height: Screen height in pixels
            frame_rate: Target frame rate (FPS)
            bgcolor: Background color (R,G,B)
            fgcolor: Eye color (R,G,B)
        """
        self.display = display
        self.screen_width = width
        self.screen_height = height
        self.bgcolor = bgcolor
        self.fgcolor = fgcolor
        
        # Create frame buffer that can be accessed externally
        # IMPORTANT: Reuse same image buffer instead of creating new one each frame
        self.frame_buffer = Image.new("RGB", (width, height), bgcolor)
        self._draw = ImageDraw.Draw(self.frame_buffer)
        self._gfx = FBUtil(self._draw)
        
        # Frame timing
        self.fps_timer = 0
        self.set_framerate(frame_rate)
        
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
        
        # Target geometry (for smooth transitions)
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
        
        # Initialize display
        self.clear_display()
        self.draw_eyes()
    
    # -------------------------
    # Public Methods
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
    
    def clear_display(self):
        """Clear the display buffer"""
        # This will be done in draw_eyes()
        pass
    
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
    # Drawing
    # -------------------------
    
    def draw_eyes(self):
        """Main drawing method"""
        # Reuse existing image buffer instead of creating new one
        # Clear background by drawing rectangle
        self._draw.rectangle([0, 0, self.screen_width, self.screen_height], fill=self.bgcolor)
        
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
        
        # Draw eyes using reused draw context
        self._gfx.fill_rrect(self.eye_l_x, self.eye_l_y, self.eye_l_width_current, 
                       self.eye_l_height_current, self.eye_l_border_radius_current, self.fgcolor)
        
        if not self._cyclops:
            self._gfx.fill_rrect(self.eye_r_x, self.eye_r_y, self.eye_r_width_current, 
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
            self._gfx.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x, self.eye_l_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
            self._gfx.fill_triangle(self.eye_r_x, self.eye_r_y - 1,
                            self.eye_r_x + self.eye_r_width_current, self.eye_r_y - 1,
                            self.eye_r_x + self.eye_r_width_current, self.eye_r_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
        else:
            self._gfx.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x, self.eye_l_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
            self._gfx.fill_triangle(self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y + self.eyelids_tired_height - 1,
                            self.bgcolor)
        
        # Draw angry eyelids
        self.eyelids_angry_height = (self.eyelids_angry_height + self.eyelids_angry_height_next) // 2
        if not self._cyclops:
            self._gfx.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
            self._gfx.fill_triangle(self.eye_r_x, self.eye_r_y - 1,
                            self.eye_r_x + self.eye_r_width_current, self.eye_r_y - 1,
                            self.eye_r_x, self.eye_r_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
        else:
            self._gfx.fill_triangle(self.eye_l_x, self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
            self._gfx.fill_triangle(self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y - 1,
                            self.eye_l_x + self.eye_l_width_current, self.eye_l_y - 1,
                            self.eye_l_x + (self.eye_l_width_current // 2), self.eye_l_y + self.eyelids_angry_height - 1,
                            self.bgcolor)
        
        # Draw happy bottom eyelids
        self.eyelids_happy_bottom_offset = (self.eyelids_happy_bottom_offset + self.eyelids_happy_bottom_offset_next) // 2
        self._gfx.fill_rrect(self.eye_l_x - 1,
                      (self.eye_l_y + self.eye_l_height_current) - self.eyelids_happy_bottom_offset + 1,
                      self.eye_l_width_current + 2,
                      self.eye_l_height_default,
                      self.eye_l_border_radius_current,
                      self.bgcolor)
        
        if not self._cyclops:
            self._gfx.fill_rrect(self.eye_r_x - 1,
                          (self.eye_r_y + self.eye_r_height_current) - self.eyelids_happy_bottom_offset + 1,
                          self.eye_r_width_current + 2,
                          self.eye_r_height_default,
                          self.eye_r_border_radius_current,
                          self.bgcolor)
        
        # Display the frame (only if display is available)
        if self.display:
            self.display.image(self.frame_buffer)


# Export all constants and class
__all__ = ['RoboEyes', 'DEFAULT', 'TIRED', 'ANGRY', 'HAPPY', 'FROZEN', 'SCARY', 'CURIOUS', 'SAD',
           'ON', 'OFF', 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
