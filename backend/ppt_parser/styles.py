from .utils import rgb_from_com_rgb
from .constants import MSO_TYPE_LINE, MSO_TYPE_FREEFORM


def get_shape_text(shape):
    # TextFrame
    try:
        tf = shape.TextFrame
        if tf is not None:
            try:
                if getattr(tf, "HasText", False):
                    return tf.TextRange.Text
            except Exception:
                try:
                    return tf.TextRange.Text
                except Exception:
                    pass
    except Exception:
        pass

    # TextFrame2
    try:
        tf2 = shape.TextFrame2
        if tf2 is not None:
            try:
                if getattr(tf2, "HasText", False):
                    return tf2.TextRange.Text
            except Exception:
                try:
                    return tf2.TextRange.Text
                except Exception:
                    pass
    except Exception:
        pass

    return ""


def extract_style_from_textrange(tr):
    try:
        f = tr.Font
    except Exception:
        return None

    style = {}

    try:
        size = float(getattr(f, "Size", 0) or 0)
        if size > 0:
            style["font_size"] = size
    except Exception:
        pass

    try:
        name = getattr(f, "Name", None) or getattr(f, "NameAscii", None)
        if name:
            style["font_name"] = name
    except Exception:
        pass

    try:
        style["bold"] = bool(getattr(f, "Bold", 0))
    except Exception:
        pass

    try:
        style["italic"] = bool(getattr(f, "Italic", 0))
    except Exception:
        pass

    try:
        ul = getattr(f, "Underline", 0)
        style["underline"] = bool(ul) and ul != 0
    except Exception:
        pass

    try:
        rgb_val = f.Color.RGB
        rgb = rgb_from_com_rgb(rgb_val)
        if rgb:
            style["color_rgb"] = rgb
    except Exception:
        pass

    return style or None


def get_text_and_style_from_shape(shape):
    text = get_shape_text(shape)
    style = None
    try:
        tf = shape.TextFrame
        if tf is not None:
            tr = tf.TextRange
            if tr is not None and tr.Text:
                style = extract_style_from_textrange(tr)
    except Exception:
        pass
    return text, style


def extract_fill_format(fill):
    if fill is None:
        return None

    info = {}
    try:
        vis = getattr(fill, "Visible", None)
        if vis is not None:
            info["visible"] = bool(vis)
    except Exception:
        pass

    try:
        fore = getattr(fill, "ForeColor", None)
        if fore is not None:
            rgb = rgb_from_com_rgb(fore.RGB)
            if rgb:
                info["fore_color_rgb"] = rgb
    except Exception:
        pass

    try:
        back = getattr(fill, "BackColor", None)
        if back is not None:
            rgb = rgb_from_com_rgb(back.RGB)
            if rgb:
                info["back_color_rgb"] = rgb
    except Exception:
        pass

    try:
        fill_type = getattr(fill, "Type", None)
        if fill_type is not None:
            info["fill_type"] = int(fill_type)
    except Exception:
        pass

    return info or None


def extract_line_format(line):
    if line is None:
        return None

    info = {}
    try:
        vis = getattr(line, "Visible", None)
        if vis is not None:
            info["visible"] = bool(vis)
    except Exception:
        pass

    try:
        w = getattr(line, "Weight", None)
        if w is not None:
            info["weight"] = float(w)
    except Exception:
        pass

    try:
        dash = getattr(line, "DashStyle", None)
        if dash is not None:
            info["dash_style"] = int(dash)
    except Exception:
        pass

    try:
        style = getattr(line, "Style", None)
        if style is not None:
            info["line_style"] = int(style)
    except Exception:
        pass

    try:
        col = getattr(line, "ForeColor", None)
        if col is not None:
            rgb = rgb_from_com_rgb(col.RGB)
            if rgb:
                info["color_rgb"] = rgb
    except Exception:
        pass

    return info or None


def extract_geometry_info(shape):
    info = {}
    try:
        if shape.Type == MSO_TYPE_LINE:
            info["kind"] = "line"
        elif shape.Type == MSO_TYPE_FREEFORM:
            info["kind"] = "freeform"
            try:
                nodes = shape.Nodes
                info["nodes_count"] = nodes.Count
            except Exception:
                pass
        else:
            info["kind"] = "shape"
    except Exception:
        return None
    return info or None
