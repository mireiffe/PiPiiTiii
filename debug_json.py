import json
import os

json_path = r"c:\Users\KimSeongeun\world\PiPiiTiii\results\8bfaf9ac-01cc-4c47-99fb-fdf38b0dde02\8bfaf9ac-01cc-4c47-99fb-fdf38b0dde02.json"

if not os.path.exists(json_path):
    print(f"File not found: {json_path}")
    exit(1)

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Slides: {len(data.get('slides', []))}")

for slide in data.get("slides", []):
    for shape in slide.get("shapes", []):
        # Check for connector types
        # msoConnector = 3
        # msoConnectorElbow = 2 (AutoShapeType)

        is_connector = False
        if shape.get("type_code") == 3:
            is_connector = True
        if shape.get("auto_shape_type") == 2:
            is_connector = True

        if is_connector or "connector" in shape.get("name", "").lower():
            print(f"Found Connector: {shape['name']}")
            print(f"  Type: {shape.get('type_code')}")
            print(f"  AutoShapeType: {shape.get('auto_shape_type')}")
            print(f"  Geometry: {shape.get('geometry')}")
            print(f"  Fill: {shape.get('fill')}")
            print(f"  Line: {shape.get('line')}")
            print("-" * 20)
