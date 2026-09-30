import time

_cooldowns = {}


def remaining(key):
    value = _cooldowns.get(key)
    if value is None:
        return 0
    left = value - time.time()
    if left <= 0:
        _cooldowns.pop(key, None)
        return 0
    return int(left)


def set_cooldown(key, seconds):
    _cooldowns[key] = time.time() + seconds
