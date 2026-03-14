import threading
import time

_LOCK = threading.Lock()

_STATE = {
    "led": {
        "count": 0,
        "pixels": [],
        "write_count": 0,
        "last_write_ms": 0,
    },
    "display": {
        "width": 0,
        "height": 0,
        "fill": 0,
        "ops": [],
        "show_count": 0,
        "last_show_ms": 0,
    },
}


def _now_ms():
    return int(time.time() * 1000)


def init_led(count):
    with _LOCK:
        _STATE["led"]["count"] = count
        _STATE["led"]["pixels"] = [[0, 0, 0] for _ in range(count)]


def set_led(index, rgb):
    with _LOCK:
        if 0 <= index < _STATE["led"]["count"]:
            _STATE["led"]["pixels"][index] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]


def fill_led(rgb):
    with _LOCK:
        _STATE["led"]["pixels"] = [[int(rgb[0]), int(rgb[1]), int(rgb[2])] for _ in range(_STATE["led"]["count"])]


def mark_led_write():
    with _LOCK:
        _STATE["led"]["write_count"] += 1
        _STATE["led"]["last_write_ms"] = _now_ms()


def init_display(width, height):
    with _LOCK:
        _STATE["display"]["width"] = int(width)
        _STATE["display"]["height"] = int(height)
        _STATE["display"]["ops"] = []


def display_fill(color):
    with _LOCK:
        _STATE["display"]["fill"] = int(color)
        _STATE["display"]["ops"] = []


def display_text(text, x, y, color):
    with _LOCK:
        _STATE["display"]["ops"].append({
            "text": str(text),
            "x": int(x),
            "y": int(y),
            "color": int(color),
        })


def mark_display_show():
    with _LOCK:
        _STATE["display"]["show_count"] += 1
        _STATE["display"]["last_show_ms"] = _now_ms()


def snapshot():
    with _LOCK:
        return {
            "led": {
                "count": _STATE["led"]["count"],
                "pixels": [px[:] for px in _STATE["led"]["pixels"]],
                "write_count": _STATE["led"]["write_count"],
                "last_write_ms": _STATE["led"]["last_write_ms"],
            },
            "display": {
                "width": _STATE["display"]["width"],
                "height": _STATE["display"]["height"],
                "fill": _STATE["display"]["fill"],
                "ops": list(_STATE["display"]["ops"]),
                "show_count": _STATE["display"]["show_count"],
                "last_show_ms": _STATE["display"]["last_show_ms"],
            },
        }
