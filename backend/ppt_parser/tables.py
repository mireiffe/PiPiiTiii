from .utils import rgb_from_com_rgb
from .styles import (
    extract_line_format,
    extract_fill_format,
    get_text_and_style_from_shape,
)
from .images import export_shape_image
from .constants import (
    MSO_TYPE_PICTURE,
    MSO_TYPE_LINKED_PICTURE,
)


def extract_cell_borders(cell):
    borders_info = {}
    try:
        borders = getattr(cell, "Borders", None)
        if borders is None:
            return None

        for side_name in ("Top", "Bottom", "Left", "Right"):
            try:
                b = getattr(borders, side_name, None)
            except Exception:
                b = None

            if not b:
                continue

            side = {}
            try:
                line = getattr(b, "Line", None)
                lf = extract_line_format(line)
                if lf:
                    side.update(lf)
            except Exception:
                pass

            if "color_rgb" not in side:
                try:
                    col = getattr(b, "Color", None)
                    if col is not None:
                        rgb = rgb_from_com_rgb(col.RGB)
                        if rgb:
                            side["color_rgb"] = rgb
                except Exception:
                    pass

            if side:
                borders_info[side_name.lower()] = side

    except Exception:
        return None

    return borders_info or None


def parse_table(shape, slide_index, shape_index, image_dir, indent=0):
    prefix = " " * indent
    table = shape.Table
    rows = table.Rows.Count
    cols = table.Columns.Count

    print(f"{prefix}Table: {rows} rows x {cols} cols")

    cells = []
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            try:
                cell = table.Cell(r, c)

                try:
                    cell_shape = cell.Shape
                except Exception as e_shape:
                    print(f"{prefix}  [WARN] cell.Shape failed at ({r},{c}): {e_shape}")
                    cell_shape = None

                cell_text = ""
                cell_style = None
                if cell_shape is not None:
                    cell_text, cell_style = get_text_and_style_from_shape(cell_shape)

                preview = ""
                if cell_text and cell_text.strip():
                    preview = cell_text.replace("\r", " ").replace("\n", " ")
                    if len(preview) > 80:
                        preview = preview[:80] + "..."

                left = top = width = height = None
                if cell_shape is not None:
                    try:
                        left = float(cell_shape.Left)
                        top = float(cell_shape.Top)
                        width = float(cell_shape.Width)
                        height = float(cell_shape.Height)
                    except Exception as e_pos:
                        print(
                            f"{prefix}  [WARN] cell position failed at ({r},{c}): {e_pos}"
                        )

                cell_fill = None
                if cell_shape is not None:
                    try:
                        cell_fill = extract_fill_format(cell_shape.Fill)
                    except Exception:
                        cell_fill = None

                cell_borders = extract_cell_borders(cell)

                cell_info = {
                    "row": r,
                    "col": c,
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                    "text": cell_text,
                    "text_preview": preview,
                    "text_style": cell_style,
                    "fill": cell_fill,
                    "borders": cell_borders,
                    "image_file": None,
                }

                if cell_shape is not None:
                    shape_type = None
                    try:
                        shape_type = cell_shape.Type
                    except Exception:
                        shape_type = None

                    if shape_type in (
                        MSO_TYPE_PICTURE,
                        MSO_TYPE_LINKED_PICTURE,
                        28,
                        29,
                        30,
                        31,
                    ):
                        try:
                            cell_shape_index = f"{shape_index}_r{r}c{c}"
                            rel_img = export_shape_image(
                                cell_shape,
                                slide_index,
                                cell_shape_index,
                                image_dir,
                            )
                            if rel_img:
                                cell_info["image_file"] = rel_img
                                print(f"{prefix}  Cell ({r},{c}) Image : {rel_img}")
                        except Exception as e_img:
                            print(
                                f"{prefix}  [WARN] cell image export failed at ({r},{c}): {e_img}"
                            )

                cells.append(cell_info)

            except Exception as e:
                print(f"{prefix}  [WARN] Failed to parse cell ({r},{c}): {e}")

    return {
        "rows": rows,
        "cols": cols,
        "cells": cells,
    }
