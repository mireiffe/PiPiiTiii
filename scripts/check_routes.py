import sys
import os
from fastapi.routing import APIRoute

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from main import app

print("Registered Routes:")
for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"{route.methods} {route.path}")
    else:
        print(f"Mount: {route.path}")
