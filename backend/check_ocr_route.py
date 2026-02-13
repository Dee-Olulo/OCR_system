# /backend/check_ocr_route.py

"""
Check which OCR route is being used and if it's calling the new preprocessing
"""

import os
import re

def check_route_files():
    routes_dir = "app/routes"
    
    print("=" * 60)
    print("OCR ROUTE CHECKER")
    print("=" * 60)
    
    # Check which OCR route files exist
    ocr_files = []
    for filename in os.listdir(routes_dir):
        if 'ocr' in filename.lower() and filename.endswith('.py'):
            ocr_files.append(os.path.join(routes_dir, filename))
    
    print(f"\nFound {len(ocr_files)} OCR route files:")
    for f in ocr_files:
        print(f"  - {f}")
    
    # Check which one is registered in main.py
    with open("app/main.py", "r") as f:
        main_content = f.read()
    
    print("\n" + "=" * 60)
    print("REGISTERED ROUTES IN main.py:")
    print("=" * 60)
    
    route_imports = re.findall(r'from app\.routes import (\w+)', main_content)
    route_includes = re.findall(r'app\.include_router\((\w+)\.router', main_content)
    
    print("\nImported routes:")
    for route in route_imports:
        if 'ocr' in route.lower():
            print(f"  ✓ {route}")
    
    print("\nIncluded routes:")
    for route in route_includes:
        if 'ocr' in route.lower():
            print(f"  ✓ {route}")
    
    # Check ocr_service.py to see if it's calling preprocessing correctly
    print("\n" + "=" * 60)
    print("CHECKING ocr_service.py:")
    print("=" * 60)
    
    with open("app/services/ocr_service.py", "r") as f:
        ocr_service_content = f.read()
    
    # Check for key methods
    checks = {
        "detect_image_quality": "detect_image_quality" in ocr_service_content,
        "_detect_document_layout": "_detect_document_layout" in ocr_service_content,
        "preprocess_thermal_receipt": "preprocess_thermal_receipt" in ocr_service_content,
        "aggressive_preprocessing": "aggressive_preprocessing" in ocr_service_content,
    }
    
    for check_name, exists in checks.items():
        status = "✓" if exists else "✗"
        print(f"  {status} {check_name}")
    
    # Check if main route is calling with aggressive parameter
    print("\n" + "=" * 60)
    print("CHECKING ROUTE CALLS:")
    print("=" * 60)
    
    for ocr_file in ocr_files:
        print(f"\n{ocr_file}:")
        with open(ocr_file, "r") as f:
            route_content = f.read()
        
        # Check if route calls OCR service
        has_ocr_call = "ocr_service.extract_text" in route_content
        has_aggressive_param = "aggressive_preprocessing" in route_content
        
        if has_ocr_call:
            print(f"  ✓ Calls ocr_service.extract_text")
            
            if has_aggressive_param:
                print(f"  ✓ Uses aggressive_preprocessing parameter")
            else:
                print(f"  ✗ Missing aggressive_preprocessing parameter")
                print(f"     ⚠️  This route needs to be updated!")
        else:
            print(f"  - No OCR service calls found")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATION:")
    print("=" * 60)
    
    # Give specific recommendation
    if 'ocr_phase2' in str(route_includes):
        print("\n✓ You're using ocr_phase2.py (good!)")
        print("\nBut the OCR service might not be calling preprocessing correctly.")
        print("\nTo fix:")
        print("1. Replace ocr_service.py with the new version")
        print("2. Restart backend")
    else:
        print("\n⚠️  You're using the old ocr.py route")
        print("\nTo fix:")
        print("1. Update main.py to use ocr_phase2")
        print("2. Replace ocr_service.py")
        print("3. Restart backend")

if __name__ == "__main__":
    check_route_files()