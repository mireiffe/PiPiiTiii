import os
import win32com.client


def debug_fonts():
    ppt_path = os.path.abspath("uploads/260dcc56-5f1b-4189-9978-95aac007f029.pptx")
    if not os.path.exists(ppt_path):
        print(f"File not found: {ppt_path}")
        return

    try:
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        # powerpoint.Visible = True # Uncomment if you want to see it
        pres = powerpoint.Presentations.Open(ppt_path, WithWindow=False)

        slide = pres.Slides(1)
        print(f"Inspecting Slide 1 of {ppt_path}")

        for shape in slide.Shapes:
            print(f"Shape: {shape.Name} (Type: {shape.Type})")

            # Check TextFrame
            try:
                if shape.HasTextFrame:
                    tf = shape.TextFrame
                    if tf.HasText:
                        tr = tf.TextRange
                        print(f"  TextFrame.Text: {tr.Text[:20]}...")
                        print(f"  TextFrame.Font.Size: {tr.Font.Size}")
            except Exception as e:
                print(f"  TextFrame Error: {e}")

            # Check TextFrame2
            try:
                # HasTextFrame property might not exist for TextFrame2, check existence
                tf2 = shape.TextFrame2
                if tf2.HasText:
                    tr2 = tf2.TextRange
                    print(f"  TextFrame2.Text: {tr2.Text[:20]}...")
                    print(f"  TextFrame2.Font.Size: {tr2.Font.Size}")
            except Exception as e:
                print(f"  TextFrame2 Error: {e}")

            print("-" * 20)

        pres.Close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_fonts()
