from .utils import get_shape_type_name
from .styles import (
    get_text_and_style_from_shape,
    extract_fill_format,
    extract_line_format,
    extract_geometry_info,
)
from .images import export_shape_image
from .tables import parse_table
from .constants import (
    MSO_TYPE_PICTURE,
    MSO_TYPE_LINKED_PICTURE,
    MSO_TYPE_PLACEHOLDER,
    MSO_TYPE_TABLE,
    MSO_TYPE_GROUP,
)


def parse_shape(
    shape,
    slide_index,
    shape_index,
    image_dir,
    indent=0,
    max_z=None,
    context="slide",  # "slide" | "master" | "layout"
):
    prefix = " " * indent

    shape_type_name = get_shape_type_name(shape)
    text, text_style = get_text_and_style_from_shape(shape)

    try:
        z_pos = int(shape.ZOrderPosition)
    except Exception:
        z_pos = None

    z_level = None
    if z_pos is not None and max_z:
        if z_pos == 1:
            z_level = "back"
        elif z_pos == max_z:
            z_level = "front"
        else:
            z_level = "middle"

    print(f"{prefix}- [{context}] Shape Name : {shape.Name} ({shape_type_name})")

    fill_info = None
    line_info = None
    geometry_info = None
    try:
        fill_info = extract_fill_format(shape.Fill)
    except Exception:
        fill_info = None
    try:
        line_info = extract_line_format(shape.Line)
    except Exception:
        line_info = None
    geometry_info = extract_geometry_info(shape)

    preview = ""
    if text.strip():
        preview = text.replace("\r", " ").replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:80] + "..."

    shape_info = {
        "shape_index": shape_index,
        "name": shape.Name,
        "context": context,
        "type_code": shape.Type,
        "type_name": shape_type_name,
        "left": float(shape.Left),
        "top": float(shape.Top),
        "width": float(shape.Width),
        "height": float(shape.Height),
        "text": text,
        "text_preview": preview,
        "text_style": text_style,
        "image_file": None,
        "z_order_position": z_pos,
        "z_order_level": z_level,
        "fill": fill_info,
        "line": line_info,
        "geometry": geometry_info,
        "children": [],
        "table": None,
    }

    # 이미지 도형 (그림/그래픽/3D 등)
    if shape.Type in (
        MSO_TYPE_PICTURE,
        MSO_TYPE_LINKED_PICTURE,
        MSO_TYPE_PLACEHOLDER,
        28,
        29,
        30,
        31,
    ):
        rel_image_path = export_shape_image(shape, slide_index, shape_index, image_dir)
        if rel_image_path:
            shape_info["image_file"] = rel_image_path
            print(f"{prefix}  Image : {rel_image_path}")

    # 테이블
    if shape.Type == MSO_TYPE_TABLE or shape_type_name == "Table":
        table_info = parse_table(
            shape,
            slide_index=slide_index,
            shape_index=shape_index,
            image_dir=image_dir,
            indent=indent + 2,
        )
        shape_info["table"] = table_info

    # 그룹
    if shape.Type == MSO_TYPE_GROUP:
        try:
            group_items = shape.GroupItems
            children = []
            for i in range(1, group_items.Count + 1):
                child = group_items.Item(i)
                child_index = f"{shape_index}_{i}"
                child_info = parse_shape(
                    child,
                    slide_index=slide_index,
                    shape_index=child_index,
                    image_dir=image_dir,
                    indent=indent + 2,
                    max_z=group_items.Count,
                    context=context,
                )
                children.append(child_info)
            shape_info["children"] = children
        except Exception as e:
            print(f"{prefix}  [WARN] Failed to parse group items: {e}")

    print()
    return shape_info
