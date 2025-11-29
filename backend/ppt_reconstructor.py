import os
import win32com.client as win32


def rgb_to_com_int(rgb_list):
    if not rgb_list or len(rgb_list) != 3:
        return 0
    r, g, b = rgb_list
    # PowerPoint RGB is BGR (0xBBGGRR) -> B*65536 + G*256 + R
    return r + (g * 256) + (b * 65536)


def apply_fill_format(shape, fill_data):
    if not fill_data:
        return

    try:
        # Color
        fore_color = fill_data.get("fore_color_rgb")
        if fore_color:
            shape.Fill.ForeColor.RGB = rgb_to_com_int(fore_color)

        back_color = fill_data.get("back_color_rgb")
        if back_color:
            shape.Fill.BackColor.RGB = rgb_to_com_int(back_color)

        # Visibility (set last to ensure it overrides any side effects of setting color)
        visible = fill_data.get("visible")
        if visible is not None:
            shape.Fill.Visible = visible

    except Exception as e:
        print(f"[WARN] Failed to apply fill format: {e}")


def apply_line_format(shape, line_data):
    if not line_data:
        return

    try:
        weight = line_data.get("weight")
        # Validate weight: must be positive and not the "undefined" large negative number
        if weight is not None and weight > 0:
            shape.Line.Weight = weight

        color = line_data.get("color_rgb")
        if color:
            shape.Line.ForeColor.RGB = rgb_to_com_int(color)

        dash_style = line_data.get("dash_style")
        # Validate dash_style: must be positive
        if dash_style is not None and dash_style > 0:
            shape.Line.DashStyle = dash_style

        line_style = line_data.get("line_style")
        # Validate line_style: must be positive
        if line_style is not None and line_style > 0:
            shape.Line.Style = line_style

        # Visibility (set last)
        visible = line_data.get("visible")
        if visible is not None:
            shape.Line.Visible = visible

    except Exception as e:
        print(f"[WARN] Failed to apply line format: {e}")


def apply_text_style(shape, text_style):
    if not text_style:
        return

    try:
        # Check if shape has text frame
        if not shape.HasTextFrame:
            return

        tr = shape.TextFrame.TextRange
        font = tr.Font

        if "font_size" in text_style:
            font.Size = text_style["font_size"]

        if "font_name" in text_style:
            font.Name = text_style["font_name"]

        if "bold" in text_style:
            font.Bold = text_style["bold"]

        if "italic" in text_style:
            font.Italic = text_style["italic"]

        if "underline" in text_style:
            font.Underline = text_style["underline"]

        if "color_rgb" in text_style:
            font.Color.RGB = rgb_to_com_int(text_style["color_rgb"])

    except Exception as e:
        print(f"[WARN] Failed to apply text style: {e}")


def reconstruct_shape(slide, shape_data, image_dir=None):
    try:
        # Basic properties
        left = shape_data.get("left", 0)
        top = shape_data.get("top", 0)
        width = shape_data.get("width", 100)
        height = shape_data.get("height", 100)
        type_code = shape_data.get("type_code", 1)  # Default to Rectangle
        image_file = shape_data.get("image_file")
        children = shape_data.get("children", [])

        # Create shape
        shape = None

        # Extract text early to decide on reconstruction strategy
        text = shape_data.get("text", "")

        # 1. Handle Groups (Recursive)
        if children:
            child_names = []
            for child_data in children:
                child_shape = reconstruct_shape(slide, child_data, image_dir)
                if child_shape:
                    child_names.append(child_shape.Name)

            if child_names:
                try:
                    # Group the children
                    # Note: In win32com, Range() accepts a list of names
                    shape = slide.Shapes.Range(child_names).Group()
                except Exception as e:
                    print(f"[WARN] Failed to group shapes {child_names}: {e}")
                    # If grouping fails, the children still exist, so we don't return None.
                    pass

        # 2. Handle Images
        elif image_file:
            # Check if we should prefer text reconstruction
            # If the shape has text and is a type that supports text (AutoShape, Placeholder, Textbox),
            # we prefer to reconstruct it as a shape with text rather than an image.
            prefer_text = False
            if text and str(text).strip() and type_code in [1, 14, 17]:
                prefer_text = True

            if not prefer_text:
                full_image_path = image_file
                if image_dir:
                    full_image_path = os.path.join(image_dir, image_file)

                # Ensure absolute path for AddPicture
                full_image_path = os.path.abspath(full_image_path)

                if os.path.exists(full_image_path):
                    # LinkToFile=False, SaveWithDocument=True
                    try:
                        shape = slide.Shapes.AddPicture(
                            full_image_path, False, True, left, top, width, height
                        )
                        # Phase 1: Force exact dimensions (PowerPoint may auto-adjust based on DPI/aspect ratio)
                        shape.Left = left
                        shape.Top = top
                        shape.Width = width
                        shape.Height = height
                    except Exception as e:
                        print(f"[WARN] Failed to add picture {full_image_path}: {e}")
                else:
                    print(f"[WARN] Image file not found: {full_image_path}")

        # 3. Handle Standard Shapes (if not a group and not an image, or image failed)
        if shape is None and not children:
            # msoTextBox = 17
            if type_code == 17:
                # msoTextOrientationHorizontal = 1
                shape = slide.Shapes.AddTextbox(1, left, top, width, height)
            elif type_code == 14:  # Placeholder
                # Treat as textbox for now as they often contain text
                shape = slide.Shapes.AddTextbox(1, left, top, width, height)
            else:
                # Default to AutoShape (Rectangle)
                try:
                    shape = slide.Shapes.AddShape(1, left, top, width, height)
                except Exception:
                    print(
                        f"[WARN] Failed to add shape type {type_code}, falling back to Rectangle"
                    )
                    shape = slide.Shapes.AddShape(1, left, top, width, height)

        # Common Post-Creation Logic
        if shape:
            # Set Name
            name = shape_data.get("name")
            if name:
                try:
                    shape.Name = name
                except Exception as e:
                    # Phase 1: Better logging for name failures
                    print(f"[WARN] Failed to set shape name to '{name}': {e}")

            # Phase 2: Embed original shape_index in AlternativeText for preservation
            original_index = shape_data.get("shape_index")
            if original_index:
                try:
                    shape.AlternativeText = f"##idx_{original_index}##"
                except Exception as e:
                    print(
                        f"[WARN] Failed to set AlternativeText for shape '{name}': {e}"
                    )

            # Phase 1: Text - validate HasTextFrame first
            if text:
                try:
                    if shape.HasTextFrame:
                        shape.TextFrame.TextRange.Text = text
                    else:
                        print(
                            f"[WARN] Shape '{name}' does not support text frame, skipping text"
                        )
                except Exception as e:
                    print(f"[WARN] Failed to set text for shape '{name}': {e}")

            # Styles
            apply_fill_format(shape, shape_data.get("fill"))
            apply_line_format(shape, shape_data.get("line"))
            apply_text_style(shape, shape_data.get("text_style"))

            # Phase 2: Z-order adjustment
            target_z = shape_data.get("z_order_position")
            if target_z:
                try:
                    current_z = shape.ZOrderPosition
                    # msoBringForward = 0, msoSendBackward = 1
                    if target_z > current_z:
                        for _ in range(target_z - current_z):
                            shape.ZOrder(0)  # msoBringForward
                    elif target_z < current_z:
                        for _ in range(current_z - target_z):
                            shape.ZOrder(1)  # msoSendBackward
                except Exception as e:
                    print(f"[WARN] Failed to adjust z-order for shape '{name}': {e}")

        return shape

    except Exception as e:
        print(f"[WARN] Failed to reconstruct shape: {e}")
        return None


def reconstruct_presentation(json_data, output_path, image_dir=None):
    """
    Reconstructs a PowerPoint presentation from the parsed JSON data.

    Args:
        json_data: Dictionary containing slide data
        output_path: Path to save the reconstructed PPT
        image_dir: Base directory for resolving relative image paths (optional)
    """
    print(f"=== Reconstructing PowerPoint: {output_path} ===")

    app = win32.gencache.EnsureDispatch("PowerPoint.Application")
    # app.Visible = True # Optional: make it visible during processing

    try:
        pres = app.Presentations.Add()

        # Set slide size if available
        if "slide_width" in json_data and "slide_height" in json_data:
            pres.PageSetup.SlideWidth = json_data["slide_width"]
            pres.PageSetup.SlideHeight = json_data["slide_height"]

        slides_data = json_data.get("slides", [])
        # Sort slides by index just in case
        slides_data.sort(key=lambda x: x.get("slide_index", 0))

        for slide_data in slides_data:
            slide_index = slide_data.get("slide_index")
            print(f"Creating Slide {slide_index}...")

            # Add a blank slide (Layout 12 is usually blank)
            # ppLayoutBlank = 12
            slide = pres.Slides.Add(pres.Slides.Count + 1, 12)

            shapes_data = slide_data.get("shapes", [])
            # Sort shapes by z_order_position if available
            # shapes_data.sort(key=lambda x: x.get("z_order_position", 0))
            # (Optional, but good practice if z-order is critical)

            for shape_data in shapes_data:
                reconstruct_shape(slide, shape_data, image_dir=image_dir)

        pres.SaveAs(os.path.abspath(output_path))
        print(f"[SUCCESS] Reconstructed PPT saved to: {output_path}")

        # Export slides as images to 'recon' folder
        output_dir = os.path.dirname(os.path.abspath(output_path))
        recon_dir = os.path.join(output_dir, "recon")
        os.makedirs(recon_dir, exist_ok=True)
        print(f"Exporting reconstructed slides to: {recon_dir}")

        for i, slide in enumerate(pres.Slides):
            slide_num = i + 1
            image_path = os.path.join(recon_dir, f"slide_{slide_num:02d}.png")
            try:
                slide.Export(image_path, "PNG")
            except Exception as e:
                print(f"[WARN] Failed to export slide {slide_num}: {e}")
        return True

    except Exception as e:
        print(f"[ERROR] Reconstruction failed: {e}")
        return False
    finally:
        if "pres" in locals():
            pres.Close()
        # app.Quit()
        pass
