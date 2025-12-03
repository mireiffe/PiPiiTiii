import os
from .utils import make_safe_filename
from .constants import PP_SHAPE_FORMAT_PNG, SHAPE_PNG_SIZE


def export_shape_image(shape, slide_index, shape_index, image_dir):
    os.makedirs(image_dir, exist_ok=True)

    shape_name_safe = make_safe_filename(shape.Name)
    slide_str = f"{slide_index:02d}"
    shape_str = str(shape_index)
    filename = f"slide{slide_str}_shape{shape_str}_{shape_name_safe}.png"
    full_path = os.path.join(image_dir, filename)

    try:
        orig_width = shape.Width
        orig_height = shape.Height

        # 목표 크기 계산
        aspect_ratio = orig_width / orig_height

        # 임시로 크기 조정
        shape.Height = SHAPE_PNG_SIZE
        shape.Width = SHAPE_PNG_SIZE * aspect_ratio

        # Always use forward slashes for cross-platform compatibility
        shape.Export(full_path, PP_SHAPE_FORMAT_PNG)
        
        # 원본 크기 복원
        shape.Width = orig_width
        shape.Height = orig_height
        return f"images/{filename}"
    except Exception as e:
        print(
            f"[WARN] Failed to export image for slide {slide_index}, shape {shape_index} ({shape.Name}): {e}"
        )
        return None
