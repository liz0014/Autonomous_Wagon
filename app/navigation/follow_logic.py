"""
navigation/follow_logic.py
--------------------------
Takes the best-person target tuple from person_detection_logic
and computes the steering value and command string.

Target is always a tuple: (x1, y1, x2, y2, confidence)
or None if no person was detected.
"""

from app.config.settings import STOP_AREA_THRESHOLD, FRAME_CENTER_FRACTION


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
        frame_center : int   pixel x of frame centre (used by HUD)
    """
    h, w = frame.shape[:2]
    frame_center = int(w * FRAME_CENTER_FRACTION)

    # No person visible — tell the wagon to spin and scan
    if target is None:
        return "SEARCH", 0.0, frame_center

    x1, y1, x2, y2, conf = target   # unpack the tuple

    cx = (x1 + x2) // 2             # horizontal centre of the bounding box
    error = cx - frame_center        # signed pixel offset from frame centre

    # Normalise to -1..+1 so steer is resolution-independent
    steer = float(error) / float(frame_center)
    steer = max(-1.0, min(1.0, steer))

    # Large box area = person is close = stop
    cmd = "STOP" if area > STOP_AREA_THRESHOLD else "FOLLOW"

    return cmd, steer, frame_center