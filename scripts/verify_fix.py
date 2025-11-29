import os
import sys

# Add backend to sys.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

from ppt_parser.slides import parse_single_slide


def verify_fix():
    ppt_path = os.path.abspath("test_pres.pptx")
    if not os.path.exists(ppt_path):
        # Create it if it doesn't exist (using the logic from test_export.py)
        import win32com.client as win32

        app = win32.gencache.EnsureDispatch("PowerPoint.Application")
        pres = app.Presentations.Add()
        slide = pres.Slides.Add(1, 11)
        shape = slide.Shapes.AddShape(1, 100, 100, 100, 100)
        shape.Name = "TestShape"
        pres.SaveAs(ppt_path)
        pres.Close()
        # app.Quit() # Keep app open for speed

    out_dir = os.path.abspath("results/verify_fix")

    print(f"Testing parse_single_slide on {ppt_path}...")
    result = parse_single_slide(ppt_path, 1, out_dir)

    if result:
        print("[SUCCESS] parse_single_slide returned result.")
        # Check if image was created
        image_dir = os.path.join(out_dir, "images")
        images = os.listdir(image_dir)
        if images:
            print(f"[SUCCESS] Images generated: {images}")
        else:
            print("[ERROR] No images generated.")
    else:
        print("[ERROR] parse_single_slide returned None.")


if __name__ == "__main__":
    verify_fix()
