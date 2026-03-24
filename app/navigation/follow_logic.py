"""
navigation/follow_logic.py
--------------------------
Takes the best-person target tuple from person_detection_logic
<<<<<<< HEAD
and computes the steering value and command string.
=======
and computes the steering value, command string, and a proportional
speed factor based on how far the target is (bbox area as proxy).
>>>>>>> 404f2e000986a15dc4759eb136cb94cd9a5514a4

Target is always a tuple: (x1, y1, x2, y2, confidence)
or None if no person was detected.
"""

<<<<<<< HEAD
from app.config.settings import STOP_AREA_THRESHOLD, FRAME_CENTER_FRACTION
=======
from app.config.settings import (
    STOP_AREA_THRESHOLD, FRAME_CENTER_FRACTION,
    TARGET_AREA, MIN_AREA,
)
>>>>>>> 404f2e000986a15dc4759eb136cb94cd9a5514a4


def compute_follow_cmd(frame, target, area):
    """
    Args:
        frame  : numpy BGR image — used only for width/height
        target : (x1, y1, x2, y2, conf) in pixels, or None
        area   : int pixel area of the target bounding box

    Returns:
        cmd          : str   "SEARCH" | "FOLLOW" | "STOP"
        steer        : float [-1.0, +1.0]
                         negative = target is left  → steer left
                         positive = target is right → steer right
<<<<<<< HEAD
=======
        speed_factor : float [0.0, 1.0]  proportional speed based on distance
>>>>>>> 404f2e000986a15dc4759eb136cb94cd9a5514a4
        frame_center : int   pixel x of frame centre (used by HUD)
    """
    h, w = frame.shape[:2]
    frame_center = int(w * FRAME_CENTER_FRACTION)

    # No person visible — tell the wagon to spin and scan
    if target is None:
<<<<<<< HEAD
        return "SEARCH", 0.0, frame_center
=======
        return "SEARCH", 0.0, 0.0, frame_center
>>>>>>> 404f2e000986a15dc4759eb136cb94cd9a5514a4

    x1, y1, x2, y2, conf = target   # unpack the tuple

    cx = (x1 + x2) // 2             # horizontal centre of the bounding box
    error = cx - frame_center        # signed pixel offset from frame centre

    # Normalise to -1..+1 so steer is resolution-independent
    steer = float(error) / float(frame_center)
    steer = max(-1.0, min(1.0, steer))

<<<<<<< HEAD
    # Large box area = person is close = stop
    cmd = "STOP" if area > STOP_AREA_THRESHOLD else "FOLLOW"

    return cmd, steer, frame_center
=======
    # ── Proportional distance control ─────────────────────────────────────
    # speed_factor maps bbox area to a 0..1 cruise multiplier:
    #   area ≤ MIN_AREA  (far)  → 1.0  (full cruise)
    #   area = TARGET_AREA (~1m) → ~0.47 (walking-pace follow)
    #   area ≥ STOP_AREA (close) → 0.0  (full stop)
    if area >= STOP_AREA_THRESHOLD:
        cmd = "STOP"
        speed_factor = 0.0
    else:
        cmd = "FOLLOW"
        clamped = max(MIN_AREA, min(area, STOP_AREA_THRESHOLD))
        speed_factor = (STOP_AREA_THRESHOLD - clamped) / (STOP_AREA_THRESHOLD - MIN_AREA)

    return cmd, steer, speed_factor, frame_center
>>>>>>> 404f2e000986a15dc4759eb136cb94cd9a5514a4
