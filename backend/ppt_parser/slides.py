import os
import json
import win32com.client as win32
from .shapes import parse_shape


def parse_single_master(master, image_dir, design_name=""):
    master_info = {
        "design_name": design_name,
        "master_name": getattr(master, "Name", ""),
        "shapes_count": master.Shapes.Count if master.Shapes is not None else 0,
        "shapes": [],
        "layouts": [],
    }

    shapes_count = master_info["shapes_count"]
    for idx in range(1, shapes_count + 1):
        try:
            shape = master.Shapes.Item(idx)
            shape_info = parse_shape(
                shape,
                slide_index=0,
                shape_index=f"M{idx}",
                image_dir=image_dir,
                indent=2,
                max_z=shapes_count,
                context="master",
            )
            master_info["shapes"].append(shape_info)
        except Exception as e:
            print(f"[WARN] Failed to parse master shape {idx}: {e}")

    try:
        layouts = master.CustomLayouts
        for l_idx in range(1, layouts.Count + 1):
            layout = layouts.Item(l_idx)
            layout_shapes_count = layout.Shapes.Count

            layout_info = {
                "layout_index": l_idx,
                "layout_name": getattr(layout, "Name", ""),
                "shapes_count": layout_shapes_count,
                "shapes": [],
            }

            for s_idx in range(1, layout_shapes_count + 1):
                try:
                    lshape = layout.Shapes.Item(s_idx)
                    lshape_info = parse_shape(
                        lshape,
                        slide_index=0,
                        shape_index=f"L{l_idx}_{s_idx}",
                        image_dir=image_dir,
                        indent=4,
                        max_z=layout_shapes_count,
                        context="layout",
                    )
                    layout_info["shapes"].append(lshape_info)
                except Exception as e_ls:
                    print(
                        f"[WARN] Failed to parse layout {l_idx} shape {s_idx}: {e_ls}"
                    )

            master_info["layouts"].append(layout_info)
    except Exception as e:
        print(
            f"[WARN] Failed to parse CustomLayouts for master '{master_info['master_name']}': {e}"
        )

    return master_info


def parse_masters(presentation, image_dir):
    masters = []

    try:
        designs = presentation.Designs
        for d_idx in range(1, designs.Count + 1):
            try:
                design = designs.Item(d_idx)
                master = design.SlideMaster
                design_name = getattr(design, "Name", f"Design{d_idx}")
                print(f"=== Parsing Master: {design_name} ===")
                master_info = parse_single_master(
                    master, image_dir, design_name=design_name
                )
                masters.append(master_info)
            except Exception as e_d:
                print(f"[WARN] Failed to parse design {d_idx}: {e_d}")
    except Exception as e:
        print(f"[WARN] Failed to access presentation.Designs: {e}")

    if not masters:
        try:
            sm = presentation.SlideMaster
            if sm is not None:
                print("=== Parsing default SlideMaster ===")
                masters.append(
                    parse_single_master(sm, image_dir, design_name="Default")
                )
        except Exception:
            pass

    return masters


def parse_single_slide(ppt_path, slide_index, out_dir, preserved_data=None):
    """
    단일 슬라이드만 파싱하여 해당 슬라이드의 정보(dict)를 반환합니다.
    이미지도 out_dir/images 에 새로 export 됩니다.
    """
    if not os.path.exists(ppt_path):
        print(f"[ERROR] File not found: {ppt_path}")
        return None

    os.makedirs(out_dir, exist_ok=True)
    image_dir = os.path.join(out_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    thumbnail_dir = os.path.join(out_dir, "thumbnails")
    os.makedirs(thumbnail_dir, exist_ok=True)

    print(f"=== Parsing Single Slide {slide_index}: {ppt_path} ===")

    powerpoint = win32.gencache.EnsureDispatch("PowerPoint.Application")
    presentation = None

    try:
        # Untitled=True로 열어서 사본으로 작업 (Protected View 등 회피 시도)
        presentation = powerpoint.Presentations.Open(
            ppt_path, ReadOnly=False, Untitled=False, WithWindow=True
        )

        try:
            slide = presentation.Slides.Item(slide_index)
        except Exception:
            print(f"[ERROR] Slide {slide_index} not found.")
            return None

        shapes_count = slide.Shapes.Count

        try:
            design_name = slide.Design.Name
        except Exception:
            design_name = None

        try:
            layout_name = slide.CustomLayout.Name
        except Exception:
            layout_name = None

        # Generate thumbnail for this slide
        thumbnail_filename = generate_slide_thumbnail(
            slide, slide_index, thumbnail_dir
        )

        slide_info = {
            "slide_index": slide_index,
            "slide_id": slide.SlideID,
            "shapes_count": shapes_count,
            "design_name": design_name,
            "layout_name": layout_name,
            "thumbnail": thumbnail_filename,
            "metadata": extract_metadata(presentation),
            "shapes": [],
        }

        print(f"--- Slide {slide_index} (Design: {design_name}) ---")

        for shape_index, shape in enumerate(slide.Shapes):
            try:
                shape_index += 1
                shape_info_data = parse_shape(
                    shape,
                    slide_index=slide_index,
                    shape_index=shape_index,
                    image_dir=image_dir,
                    indent=2,
                )

                # Apply preserved description if available
                if preserved_data:
                    key = (slide_index, shape.Name)
                    if key in preserved_data:
                        shape_info_data["description"] = preserved_data[key]
                        print(f"  [INFO] Preserved description for {shape.Name}")

                slide_info["shapes"].append(shape_info_data)
            except Exception as e:
                print(
                    f"[WARN] Failed to parse shape {shape_index} on slide {slide_index}: {e}"
                )

        return slide_info

    except Exception as e:
        print(f"[ERROR] Parsing failed: {e}")
        return None
    finally:
        if presentation:
            presentation.Close()


def extract_metadata(presentation) -> dict:
    metadata = {
        "builtin_properties": {},
        "custom_properties": {},
    }

    try:
        for prop in presentation.BuiltInDocumentProperties:
            name = prop.Name
            try:
                value = prop.Value
            except Exception:
                value = None
            metadata["builtin_properties"][name] = value
    except Exception as e:
        print(f"[WARN] Failed to extract BuiltInDocumentProperties: {e}")

    try:
        for prop in presentation.CustomDocumentProperties:
            name = prop.Name
            try:
                value = prop.Value
            except Exception:
                value = None
            metadata["custom_properties"][name] = value
    except Exception as e:
        print(f"[WARN] Failed to extract CustomDocumentProperties: {e}")

    return metadata


def get_presentation_metadata(ppt_path):
    """
    Opens the presentation to extract metadata needed for deterministic UID generation.
    Returns a dict with 'title' and 'slide_count'.
    """
    if not os.path.exists(ppt_path):
        return None

    powerpoint = win32.gencache.EnsureDispatch("PowerPoint.Application")
    presentation = None

    try:
        # Open ReadOnly to be faster and safer
        presentation = powerpoint.Presentations.Open(
            ppt_path, ReadOnly=True, Untitled=False, WithWindow=False
        )

        slide_count = presentation.Slides.Count

        def get_prop(name):
            try:
                val = presentation.BuiltInDocumentProperties(name).Value
                return str(val) if val else ""
            except Exception:
                return ""

        return {
            "title": get_prop("Title"),
            "subject": get_prop("Subject"),
            "author": get_prop("Author"),
            "last_modified_by": get_prop("Last Author"),
            "revision_number": get_prop("Revision Number"),
            "slide_count": slide_count,
        }

    except Exception as e:
        print(f"[ERROR] Failed to extract metadata from {ppt_path}: {e}")
        return None
    finally:
        if presentation:
            try:
                presentation.Close()
            except Exception:
                pass


def generate_slide_thumbnail(slide, slide_index, thumbnail_dir, max_dimension=1920):
    """
    Generate a thumbnail image for a single slide.
    The thumbnail maintains the slide's aspect ratio with the longest side set to max_dimension.
    Returns the relative path to the thumbnail file, or None if failed.
    """
    try:
        os.makedirs(thumbnail_dir, exist_ok=True)
        thumbnail_filename = f"slide_{slide_index:03d}_thumb.png"
        thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

        # Get slide dimensions from presentation
        presentation = slide.Parent
        slide_width = float(presentation.PageSetup.SlideWidth)
        slide_height = float(presentation.PageSetup.SlideHeight)

        # Calculate thumbnail dimensions maintaining aspect ratio
        # Set the longer side to max_dimension
        if slide_width >= slide_height:
            # Landscape or square
            thumb_width = max_dimension
            thumb_height = int(max_dimension * slide_height / slide_width)
        else:
            # Portrait
            thumb_height = max_dimension
            thumb_width = int(max_dimension * slide_width / slide_height)

        # Export slide as image
        slide.Export(thumbnail_path, "PNG", ScaleWidth=thumb_width, ScaleHeight=thumb_height)

        print(f"  [INFO] Generated thumbnail: {thumbnail_filename} ({thumb_width}x{thumb_height})")
        return thumbnail_filename
    except Exception as e:
        print(f"  [WARN] Failed to generate thumbnail for slide {slide_index}: {e}")
        return None


def parse_presentation(
    ppt_path, out_dir, debug=False, progress_callback=None, preserved_data=None
):
    if not os.path.exists(ppt_path):
        print(f"[ERROR] File not found: {ppt_path}")
        return None

    os.makedirs(out_dir, exist_ok=True)
    image_dir = os.path.join(out_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    thumbnail_dir = os.path.join(out_dir, "thumbnails")
    os.makedirs(thumbnail_dir, exist_ok=True)

    print(f"=== Parsing PowerPoint: {ppt_path} ===")

    powerpoint = win32.gencache.EnsureDispatch("PowerPoint.Application")
    presentation = None

    try:
        # Untitled=True로 열어서 사본으로 작업 (Protected View 등 회피 시도)
        presentation = powerpoint.Presentations.Open(
            ppt_path, ReadOnly=False, Untitled=True, WithWindow=True
        )

        slide_width = float(presentation.PageSetup.SlideWidth)
        slide_height = float(presentation.PageSetup.SlideHeight)

        slides_count = presentation.Slides.Count
        print(f"Slides Count: {slides_count}")

        # Convert to relative path from project root (3 levels up from backend/ppt_parser)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        abs_ppt_path = os.path.abspath(ppt_path)
        try:
            rel_ppt_path = os.path.relpath(abs_ppt_path, project_root)
            # Convert to forward slashes
            rel_ppt_path = rel_ppt_path.replace(os.sep, "/")
        except ValueError:
            # If relpath fails (different drives on Windows), use absolute path
            rel_ppt_path = abs_ppt_path.replace(os.sep, "/")

        result = {
            "ppt_path": rel_ppt_path,
            "slides_count": slides_count,
            "slide_width": slide_width,
            "slide_height": slide_height,
            "metadata": extract_metadata(presentation),
            "masters": [],
            "slides": [],
        }

        # 마스터 / 레이아웃
        if progress_callback:
            progress_callback(10, "Parsing Masters...")
        masters_info = parse_masters(presentation, image_dir)
        result["masters"] = masters_info

        # 슬라이드
        target_indices = list(range(1, slides_count + 1))
        target_indices = list(range(1, slides_count + 1))

        total_slides = len(target_indices)
        for i, slide_index in enumerate(target_indices):
            if progress_callback:
                # 10% ~ 90% mapped to slides
                percent = 10 + int((i / total_slides) * 80)
                progress_callback(percent, f"Parsing Slide {i + 1}/{total_slides}")

            try:
                slide = presentation.Slides(slide_index)
                shapes_count = slide.Shapes.Count

                try:
                    design_name = slide.Design.Name
                except Exception:
                    design_name = None

                try:
                    layout_name = slide.CustomLayout.Name
                except Exception:
                    layout_name = None

                # Generate thumbnail for this slide
                thumbnail_filename = generate_slide_thumbnail(
                    slide, slide_index, thumbnail_dir
                )

                slide_info = {
                    "slide_index": slide_index,
                    "slide_id": slide.SlideID,
                    "shapes_count": shapes_count,
                    "design_name": design_name,
                    "layout_name": layout_name,
                    "thumbnail": thumbnail_filename,
                    "shapes": [],
                }

                print(f"--- Slide {slide_index} (Design: {design_name}) ---")

                for shape_index, shape in enumerate(slide.Shapes):
                    shape_index += 1
                    shape_info = parse_shape(
                        shape,
                        slide_index=slide_index,
                        shape_index=shape_index,
                        image_dir=image_dir,
                        indent=2,
                        max_z=shapes_count,
                        context="slide",
                    )

                    # Apply preserved description if available
                    if preserved_data:
                        key = (slide_index, shape.Name)
                        if key in preserved_data:
                            shape_info["description"] = preserved_data[key]
                            print(f"  [INFO] Preserved description for {shape.Name}")

                    slide_info["shapes"].append(shape_info)

                result["slides"].append(slide_info)

            except Exception as e:
                print(f"[ERROR] Failed to parse slide {slide_index}: {e}")

        if progress_callback:
            progress_callback(95, "Saving JSON...")

        base_name = os.path.splitext(os.path.basename(out_dir))[0]
        json_path = os.path.join(out_dir, f"{base_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        print(f"[INFO] JSON metadata saved to: {json_path}")
        print(f"[INFO] Images saved under : {image_dir}")

        if progress_callback:
            progress_callback(100, "Done")

        return json_path

    except Exception as e:
        print(f"[ERROR] Parsing failed: {e}")
        if progress_callback:
            progress_callback(-1, f"Error: {e}")
        return None
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        try:
            powerpoint.Quit()
        except Exception:
            pass
        print("=== Parse Done ===")
