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

        # 0 보호
        if orig_width == 0 or orig_height == 0:
            # 그냥 원본 크기로 export
            shape.Export(full_path, PP_SHAPE_FORMAT_PNG)
        else:
            # === 1) 긴 변을 기준으로 스케일 계산 ===
            max_side = max(orig_width, orig_height)
            scale = SHAPE_PNG_SIZE / max_side

            new_width = orig_width * scale
            new_height = orig_height * scale

            # === 2) 텍스트 폰트 사이즈 저장 ===
            text_range = None
            orig_font_size = None

            try:
                # PowerPoint object model:
                # shape.HasTextFrame == -1 이면 텍스트 프레임 있음
                if getattr(shape, "HasTextFrame", 0) and shape.TextFrame.HasText:
                    text_range = shape.TextFrame.TextRange

                    # 단일 폰트 사이즈 기준 (혼합된 사이즈면 Size 가 0일 수 있음)
                    if text_range.Font.Size > 0:
                        orig_font_size = text_range.Font.Size
                    else:
                        # 혼합 폰트 사이즈 케이스는 필요하면 Characters 루프 돌면서 처리 가능
                        pass
            except Exception:
                text_range = None
                orig_font_size = None

            # === 크기 및 폰트 스케일 적용 ===
            shape.Width = new_width
            shape.Height = new_height

            if text_range is not None and orig_font_size is not None:
                text_range.Font.Size = orig_font_size * scale

            # Always use forward slashes for cross-platform compatibility
            shape.Export(full_path, PP_SHAPE_FORMAT_PNG)

            # === 원본 크기 복원 ===
            shape.Width = orig_width
            shape.Height = orig_height

            if text_range is not None and orig_font_size is not None:
                text_range.Font.Size = orig_font_size
        return f"images/{filename}"
    except Exception as e:
        print(
            f"[WARN] Failed to export image for slide {slide_index}, shape {shape_index} ({shape.Name}): {e}"
        )
        return None
