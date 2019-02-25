def sign(value) -> float:
    if value == 0:
        return 0
    elif value > 0:
        return 1
    return -1

def clamp_sign(value) -> float:
    return min(1, max(-1, value))
