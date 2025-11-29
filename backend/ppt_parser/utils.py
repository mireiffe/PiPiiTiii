import re
from .constants import shape_type_map


def make_safe_filename(name: str) -> str:
    if not name:
        return "noname"
    safe = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", name)
    return safe[:80]


def rgb_from_com_rgb(rgb_val):
    try:
        r = rgb_val & 0xFF
        g = (rgb_val >> 8) & 0xFF
        b = (rgb_val >> 16) & 0xFF
        return [int(r), int(g), int(b)]
    except Exception:
        return None


def get_shape_type_name(shape):
    return shape_type_map.get(shape.Type, f"Unknown({shape.Type})")
