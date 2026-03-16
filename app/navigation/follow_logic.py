from app.config.settings import SEARCH_CMD, FOLLOW_CMD, STOP_CMD, STOP_AREA_THRESHOLD


def compute_follow_command(frame_width, target):
    frame_center = frame_width // 2

    if target is None:
        return {
            "cmd": SEARCH_CMD,
            "steer": 0.0,
            "error": 0,
            "cx": None,
            "area": 0,
        }

    cx = (target["x1"] + target["x2"]) // 2
    error = cx - frame_center

    steer = float(error) / float(frame_center)
    steer = max(-1.0, min(1.0, steer))

    cmd = STOP_CMD if target["area"] > STOP_AREA_THRESHOLD else FOLLOW_CMD

    return {
        "cmd": cmd,
        "steer": steer,
        "error": error,
        "cx": cx,
        "area": target["area"],
    }