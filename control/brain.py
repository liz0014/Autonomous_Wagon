def decide_command(target_area: int, has_target: bool, stop_area_threshold: int = 90000):
    """
    Returns (cmd_string).
    - SEARCH: no person
    - FOLLOW: person found, not too close
    - STOP: person too close (using area proxy)
    """
    if not has_target:
        return "SEARCH"
    return "STOP" if target_area > stop_area_threshold else "FOLLOW"