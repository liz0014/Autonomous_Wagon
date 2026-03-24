"""
navigation/tracking.py
-----------------------
Single-person lock-on tracker.

Built on three ideas we worked out together:

  1. SCORING    — every detection gets scored against our saved person
                  using position, color, and size. Highest score wins.

  2. KALMAN     — when detection misses a frame, we predict where the
                  person should be using their last known velocity
                  (momentum — they keep moving in the same direction).

  3. HSV COLOR  — we compare clothing color in HSV space so lighting
                  changes don't confuse the tracker. We only compare
                  Hue and Saturation, ignoring Value (brightness).

Scoring weights (based on reliability for a follow-from-behind wagon):
  position : 0.60  — most reliable, momentum is predictable
  color    : 0.30  — reliable, clothing doesn't change
  size     : 0.10  — least reliable, changes as person moves closer/further
"""

import math
import cv2
import numpy as np



# Maximum pixel distance between predicted and detected position
# that we'll still consider a match. Based on our math:
#   person walks ~9px per frame at normal speed
#   50px gives comfortable buffer for fast movement or dropped frames
MAX_POSITION_DISTANCE = 50

# Minimum combined score to accept a detection as our person.
# 0.0 = accept anything, 1.0 = perfect match only.
# 0.4 means at least a reasonable match across all three clues.
MIN_SCORE_THRESHOLD = 0.4

# How many consecutive missed frames before we declare LOST.
# At 30fps, 10 frames = 0.33 seconds of patience before freezing.
LOST_PATIENCE = 10


class PersonTracker:
    """
    Tracks a single locked person across frames.

    State machine:
      IDLE   → no lock yet, wagon sits still
      LOCKED → actively tracking, wagon follows
      LOST   → person disappeared, wagon freezes and waits
    """

    def __init__(self):
        # ── Lock state ────────────────────────────────────────────────────
        # Whether the user has pressed LOCK yet
        self.locked = False

        # ── Position — where they are ─────────────────────────────────────
        # Centre of their bounding box in pixels
        self.center_x = None
        self.center_y = None

        # ── Velocity — how fast they're moving ───────────────────────────
        # Pixels per frame in x and y directions.
        # Starts at zero because person is standing still at lock moment.
        # Updated every frame so we always know their current momentum.
        self.velocity_x = 0
        self.velocity_y = 0

        # ── Predicted position — where we EXPECT them next frame ──────────
        # Calculated as: current_position + velocity
        # Used when detection misses a frame (Kalman step)
        self.predicted_x = None
        self.predicted_y = None

        # ── Color — what their clothing looks like ────────────────────────
        # Stored as HSV array [hue, saturation, value]
        # We compare only H and S, ignore V (brightness)
        self.color_hsv = None

        # ── Size — their box proportions ──────────────────────────────────
        self.box_w = None
        self.box_h = None

        # ── Tracking health ───────────────────────────────────────────────
        # How many consecutive frames we've failed to find them
        self.missed_frames = 0
        self.is_lost = False


    def lock(self, box, frame):
        """
        Called when user presses LOCK.
        Saves everything we know about the chosen person.

        Args:
            box   : (x1, y1, x2, y2, conf) — the chosen detection tuple
            frame : numpy BGR image — needed to sample clothing color
        """
        x1, y1, x2, y2, conf = box

        # ── Save position ─────────────────────────────────────────────────
        # Calculate the centre point of their bounding box.
        # This is our anchor — all future tracking compares against this.
        self.center_x = (x1 + x2) // 2
        self.center_y = (y1 + y2) // 2

        # ── Save size ─────────────────────────────────────────────────────
        self.box_w = x2 - x1
        self.box_h = y2 - y1

        # ── Sample clothing color ─────────────────────────────────────────
        # Crop the bounding box region out of the frame.
        # frame[y1:y2, x1:x2] gives us just the pixels inside the box.
        # We clamp to frame boundaries in case the box is at an edge.
        h, w = frame.shape[:2]
        crop = frame[
            max(0, y1) : min(h, y2),
            max(0, x1) : min(w, x2)
        ]

        # Average all pixels in the crop into one BGR color value.
        # mean(axis=(0,1)) averages across rows and columns,
        # leaving us with [avg_B, avg_G, avg_R].
        avg_bgr = crop.mean(axis=(0, 1))

        # Convert that single averaged color to HSV.
        # We reshape to (1,1,3) because cvtColor expects an image, not a single pixel.
        pixel = np.uint8([[avg_bgr]])
        self.color_hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]

        # ── Set velocity to zero ──────────────────────────────────────────
        # Person is standing still at lock moment — no momentum yet.
        self.velocity_x = 0
        self.velocity_y = 0

        # Predicted position starts as current position
        self.predicted_x = self.center_x
        self.predicted_y = self.center_y

        # ── Activate tracker ──────────────────────────────────────────────
        self.locked       = True
        self.is_lost      = False
        self.missed_frames = 0


    def unlock(self):
        """Called when user presses UNLOCK. Resets everything."""
        self.locked        = False
        self.is_lost       = False
        self.missed_frames = 0
        self.center_x      = None
        self.center_y      = None
        self.predicted_x   = None
        self.predicted_y   = None
        self.color_hsv     = None
        self.velocity_x    = 0
        self.velocity_y    = 0


    def update(self, persons, frame):
        """
        Called every frame. Finds our locked person among all detections.

        Flow:
          1. Not locked yet?        → return None
          2. No detections?         → predict position, increment miss counter
          3. Detections available?  → score each one, pick best match
             Good match found?      → update position + velocity, return box
             No good match?         → predict position, increment miss counter
          4. Too many missed frames? → declare LOST, freeze wagon

        Args:
            persons : list of (x1, y1, x2, y2, conf) tuples from YOLO
            frame   : numpy BGR image — needed for color comparison

        Returns:
            best matching box tuple, or None if lost/not locked
        """

        # ── Step 1: Not locked yet ────────────────────────────────────────
        if not self.locked:
            return None

        # ── Step 2: No detections this frame ─────────────────────────────
        if not persons:
            self._predict_and_miss()
            return None

        # ── Step 3: Score every detection ─────────────────────────────────
        best_box   = None
        best_score = 0.0

        for person in persons:
            score = self._score(person, frame)

            if score > best_score:
                best_score = score
                best_box   = person

        # ── Step 4: Did we find a good enough match? ──────────────────────
        if best_score >= MIN_SCORE_THRESHOLD:
            # Good match — update our saved state with the new position
            self._update_state(best_box)
            return best_box
        else:
            # No detection was close enough — treat as a miss
            self._predict_and_miss()
            return None


    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score(self, person, frame):
        """
        Score a single detection against our saved person.
        Returns a float 0.0–1.0. Higher = more likely to be our person.

        Combined score = (position × 0.60) + (color × 0.30) + (size × 0.10)
        """
        x1, y1, x2, y2, conf = person

        det_cx = (x1 + x2) // 2
        det_cy = (y1 + y2) // 2

        position_score = self._score_position(det_cx, det_cy)
        color_score    = self._score_color(person, frame)
        size_score     = self._score_size(x2 - x1, y2 - y1)

        return (position_score * 0.60 +
                color_score    * 0.30 +
                size_score     * 0.10)


    def _score_position(self, det_cx, det_cy):
        """
        How close is this detection to where we predicted the person would be?

        Uses the distance formula (Pythagorean theorem):
          distance = sqrt((det_cx - predicted_x)² + (det_cy - predicted_y)²)

        Converts to 0–1 score:
          distance = 0px  → score = 1.0  (perfect)
          distance = 50px → score = 0.0  (too far)
        """
        dx = det_cx - self.predicted_x
        dy = det_cy - self.predicted_y
        distance = math.sqrt(dx * dx + dy * dy)

        # max(0.0, ...) clamps so we never return a negative score
        return max(0.0, 1.0 - (distance / MAX_POSITION_DISTANCE))


    def _score_color(self, person, frame):
        """
        How similar is this detection's clothing color to our saved color?

        Samples HSV color from inside the detection box.
        Compares only Hue and Saturation — ignores Value (brightness)
        so lighting changes don't confuse us.

        Uses distance formula in HSV color space:
          color_distance = sqrt(hue_diff² + sat_diff²)
        """
        x1, y1, x2, y2, conf = person

        if self.color_hsv is None:
            return 0.5   # no color saved yet, neutral score

        # Sample the color from this detection's box region
        h, w = frame.shape[:2]
        crop = frame[
            max(0, y1) : min(h, y2),
            max(0, x1) : min(w, x2)
        ]

        if crop.size == 0:
            return 0.5   # empty crop (box at edge), neutral score

        avg_bgr = crop.mean(axis=(0, 1))
        pixel   = np.uint8([[avg_bgr]])
        hsv     = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]

        # Compare only H and S, ignore V
        # Hue range is 0-179 in OpenCV, Saturation is 0-255
        hue_diff = abs(int(self.color_hsv[0]) - int(hsv[0]))
        sat_diff = abs(int(self.color_hsv[1]) - int(hsv[1]))

        # Hue wraps around (179→0 is the same as 0→179)
        # so we take the shorter path around the circle
        hue_diff = min(hue_diff, 180 - hue_diff)

        # Max possible distance in this reduced HSV space
        # sqrt(90² + 255²) ≈ 270
        max_color_distance = 270.0
        color_distance = math.sqrt(hue_diff ** 2 + sat_diff ** 2)

        return max(0.0, 1.0 - (color_distance / max_color_distance))


    def _score_size(self, det_w, det_h):
        """
        How similar is this detection's size to our saved box?

        We compare the WIDTH/HEIGHT RATIO instead of raw pixels
        because the ratio stays stable even as the person moves
        closer or further away.

        A tall narrow person stays tall and narrow regardless of distance.
        """
        if self.box_w is None or self.box_h is None or self.box_w == 0:
            return 0.5   # no size saved yet, neutral score

        saved_ratio   = self.box_h / self.box_w
        current_ratio = det_h / det_w if det_w > 0 else 1.0

        ratio_diff = abs(saved_ratio - current_ratio)

        # A ratio difference of 1.0 or more = very different body shape
        return max(0.0, 1.0 - ratio_diff)


    # ── Kalman prediction ─────────────────────────────────────────────────────

    def _predict_and_miss(self):
        """
        Called when we couldn't find our person this frame.

        Uses velocity (momentum) to predict where they probably are.
        This keeps the wagon steering in the right direction even during
        brief detection gaps.

        predicted_position = last_known_position + last_known_velocity
        """
        if self.predicted_x is not None:
            self.predicted_x += self.velocity_x
            self.predicted_y += self.velocity_y

        self.missed_frames += 1

        if self.missed_frames >= LOST_PATIENCE:
            self.is_lost = True


    def _update_state(self, box):
        """
        Called when we successfully matched a detection to our person.
        Updates position, recalculates velocity, resets miss counter.
        """
        x1, y1, x2, y2, conf = box

        new_cx = (x1 + x2) // 2
        new_cy = (y1 + y2) // 2

        # Velocity = how far they moved since last frame
        # This is what gives us momentum for the next prediction
        if self.center_x is not None:
            self.velocity_x = new_cx - self.center_x
            self.velocity_y = new_cy - self.center_y

        # Update saved position and predicted next position
        self.center_x    = new_cx
        self.center_y    = new_cy
        self.predicted_x = new_cx + self.velocity_x
        self.predicted_y = new_cy + self.velocity_y

        # Update size (smoothly — person may be slightly closer/further)
        self.box_w = x2 - x1
        self.box_h = y2 - y1

        # Healthy — reset miss counter
        self.missed_frames = 0
        self.is_lost       = False
