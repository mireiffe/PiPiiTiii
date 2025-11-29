import os
from .utils import make_safe_filename
from .constants import PP_SHAPE_FORMAT_PNG


def export_shape_image(shape, slide_index, shape_index, image_dir):
    os.makedirs(image_dir, exist_ok=True)

    shape_name_safe = make_safe_filename(shape.Name)
    slide_str = f"{slide_index:02d}"
    shape_str = str(shape_index)
    filename = f"slide{slide_str}_shape{shape_str}_{shape_name_safe}.png"
    full_path = os.path.join(image_dir, filename)

    try:
        shape.Export(full_path, PP_SHAPE_FORMAT_PNG)
        return os.path.join("images", filename)
    except Exception as e:
        print(
            f"[WARN] Failed to export image for slide {slide_index}, shape {shape_index} ({shape.Name}): {e}"
        )
        return None
