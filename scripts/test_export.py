import os
import win32com.client as win32


def test_export():
    ppt_path = os.path.abspath("test_presentation.pptx")

    # Create a dummy PPT if not exists
    app = win32.gencache.EnsureDispatch("PowerPoint.Application")
    # app.Visible = True # Make sure it's visible for creation

    pres = app.Presentations.Add()
    slide = pres.Slides.Add(1, 11)  # ppLayoutTitleOnly
    shape = slide.Shapes.AddShape(1, 100, 100, 100, 100)  # msoShapeRectangle
    shape.Name = "TestShape"
    pres.SaveAs(ppt_path)
    pres.Close()

    print(f"Created {ppt_path}")

    # Try to open with WithWindow=False and Export
    print("Testing WithWindow=False...")
    try:
        pres = app.Presentations.Open(ppt_path, WithWindow=False)
        slide = pres.Slides(1)
        shape = slide.Shapes("TestShape")

        export_path = os.path.abspath("test_export.png")
        shape.Export(export_path, 2)  # ppShapeFormatPNG
        print("Export successful with WithWindow=False")
    except Exception as e:
        print(f"Export FAILED with WithWindow=False: {e}")
    finally:
        try:
            pres.Close()
        except:
            pass

    # Try to open with WithWindow=True
    print("Testing WithWindow=True...")
    try:
        pres = app.Presentations.Open(ppt_path, WithWindow=True)
        slide = pres.Slides(1)
        shape = slide.Shapes("TestShape")

        export_path = os.path.abspath("test_export_window.png")
        shape.Export(export_path, 2)  # ppShapeFormatPNG
        print("Export successful with WithWindow=True")
    except Exception as e:
        print(f"Export FAILED with WithWindow=True: {e}")
    finally:
        try:
            pres.Close()
        except:
            pass

    app.Quit()


if __name__ == "__main__":
    test_export()
