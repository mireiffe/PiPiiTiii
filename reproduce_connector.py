import win32com.client as win32
import os
import json
from backend.ppt_parser.shapes import parse_shape


def create_ppt_with_connector(ppt_path):
    ppt = win32.gencache.EnsureDispatch("PowerPoint.Application")
    pres = ppt.Presentations.Add()
    slide = pres.Slides.Add(1, 12)  # 12 = ppLayoutBlank

    # Add two rectangles
    shape1 = slide.Shapes.AddShape(1, 100, 100, 50, 50)  # msoShapeRectangle
    shape2 = slide.Shapes.AddShape(1, 300, 300, 50, 50)

    # Add an elbow connector
    connector = slide.Shapes.AddConnector(
        2, 100, 100, 300, 300
    )  # 2 = msoConnectorElbow
    connector.ConnectorFormat.BeginConnect(shape1, 1)
    connector.ConnectorFormat.EndConnect(shape2, 1)
    connector.Name = "TestElbowConnector"

    pres.SaveAs(ppt_path)
    pres.Close()


def test_parse_connector(ppt_path):
    ppt = win32.gencache.EnsureDispatch("PowerPoint.Application")
    pres = ppt.Presentations.Open(ppt_path, WithWindow=False)
    slide = pres.Slides(1)

    for shape in slide.Shapes:
        if shape.Name == "TestElbowConnector":
            print(f"Parsing shape: {shape.Name}")
            image_dir = "tmp_images"
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)

            info = parse_shape(shape, 1, 1, image_dir)

            print(f"Is Connector: {shape.Connector}")

            # Try to access properties directly on shape if it's a connector
            try:
                # Note: In some versions, BeginX/Y are on ConnectorFormat, in others on Shape?
                # Let's try ConnectorFormat first
                cf = shape.ConnectorFormat
                print(f"Connector Format Type: {cf.Type}")
                # print(f"Begin: ({cf.BeginX}, {cf.BeginY})") # This failed before
            except Exception as e:
                print(f"ConnectorFormat error: {e}")

            try:
                # Try accessing via dynamic dispatch if generated wrapper is missing properties
                # But we are using gencache.EnsureDispatch.
                # Let's try accessing BeginX on shape itself?
                # Or maybe we need to cast it?
                pass
            except Exception:
                pass

            # Let's try to print all properties of ConnectorFormat
            try:
                # print(dir(shape.ConnectorFormat))
                pass
            except:
                pass

            # Try to access BeginX/Y on the shape itself?
            # Microsoft docs say ConnectorFormat.BeginConnect(Shape, ConnectionSite)
            # But to get coordinates?
            # Shape.BeginX / Shape.BeginY exist for connectors.
            try:
                print(f"Shape.BeginX: {shape.BeginX}")
                print(f"Shape.BeginY: {shape.BeginY}")
                print(f"Shape.EndX: {shape.EndX}")
                print(f"Shape.EndY: {shape.EndY}")
            except Exception as e:
                print(f"Shape.BeginX error: {e}")

            try:
                print(f"HorizontalFlip: {shape.HorizontalFlip}")
                print(f"VerticalFlip: {shape.VerticalFlip}")
            except Exception as e:
                print(f"Flip error: {e}")

            try:
                print(f"Adjustments Count: {shape.Adjustments.Count}")
                for i in range(1, shape.Adjustments.Count + 1):
                    print(f"  Adj[{i}]: {shape.Adjustments.Item(i)}")
            except Exception as e:
                print(f"Adjustments error: {e}")

            try:
                # Nodes usually for Freeform, but let's check
                print(f"Nodes Count: {shape.Nodes.Count}")
                for i in range(1, shape.Nodes.Count + 1):
                    node = shape.Nodes.Item(i)
                    print(
                        f"  Node[{i}]: ({node.Points(1, 1)}, {node.Points(1, 2)})"
                    )  # Points returns 2D array
            except Exception as e:
                print(f"Nodes error: {e}")

            print(json.dumps(info, indent=2, default=str))

    pres.Close()


if __name__ == "__main__":
    ppt_path = os.path.abspath("test_connector.pptx")
    if os.path.exists(ppt_path):
        os.remove(ppt_path)

    try:
        create_ppt_with_connector(ppt_path)
        test_parse_connector(ppt_path)
    except Exception as e:
        print(f"Error: {e}")
