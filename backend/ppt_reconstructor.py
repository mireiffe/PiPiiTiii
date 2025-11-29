import os
import win32com.client as win32
from backend.ppt_parser.utils import rgb_from_com_rgb


def reconstruct_presentation(json_data, output_path):
    """
    Reconstructs a PowerPoint presentation from the parsed JSON data.
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
            for shape_data in shapes_data:
                reconstruct_shape(slide, shape_data)

        pres.SaveAs(os.path.abspath(output_path))
        print(f"[SUCCESS] Reconstructed PPT saved to: {output_path}")

        # Export slides as images to 'recon' folder
        output_dir = os.path.dirname(os.path.abspath(output_path))
        recon_dir = os.path.join(output_dir, "recon")
        os.makedirs(recon_dir, exist_ok=True)
        print(f"Exporting reconstructed slides to: {recon_dir}")

        for i, slide in enumerate(pres.Slides):
            # Slide index is 1-based in API, but enumerate is 0-based
            # Let's use 1-based index for filename to match PPT UI
            slide_num = i + 1
            image_path = os.path.join(recon_dir, f"slide_{slide_num:02d}.png")
            # 18 = ppShapeFormatPNG (Wait, Slide.Export takes path and filter name as string usually, or int?)
            # Slide.Export(FileName, FilterName, ScaleWidth, ScaleHeight)
            # FilterName is string like "PNG", "JPG"
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
        # app.Quit() # Don't quit if we want to keep the app instance or if it was already open?
        # Usually better to quit if we started it, but for now let's leave it or handle carefully.
        # If we are running tests, maybe we want to close it.
        # Let's quit to be clean.
        # app.Quit()
        pass


def reconstruct_shape(slide, shape_data):
    try:
        # Basic properties
        left = shape_data.get("left", 0)
        top = shape_data.get("top", 0)
        width = shape_data.get("width", 100)
        height = shape_data.get("height", 100)
        shape_type_name = shape_data.get("type_name", "")
        text_content = shape_data.get("text_content", "")

        # Create shape based on type (simplified)
        # For now, just create a rectangle or text box

        # MsoShapeType enumeration: msoShapeRectangle = 1
        # msoTextOrientationHorizontal = 1

        shape = slide.Shapes.AddShape(1, left, top, width, height)

        # Set text if exists
        if text_content:
            shape.TextFrame.TextRange.Text = text_content

        # Try to restore some formatting if possible (fill color, etc.)
        # This is very basic
        fill = shape_data.get("fill", {})
        if fill and fill.get("type") == "solid":
            fore_color = fill.get("fore_color_rgb")
            if fore_color and isinstance(fore_color, list) and len(fore_color) == 3:
                # RGB list [r, g, b] -> int for PowerPoint (BGR hex structure: 0xBBGGRR)
                r, g, b = fore_color
                # PowerPoint expects RGB property as a Long integer representing the color.
                # The formula is R + G*256 + B*65536
                color_int = r + (g * 256) + (b * 65536)
                shape.Fill.ForeColor.RGB = color_int
                shape.Fill.Visible = True  # Ensure fill is visible

    except Exception as e:
        print(f"[WARN] Failed to reconstruct shape: {e}")
