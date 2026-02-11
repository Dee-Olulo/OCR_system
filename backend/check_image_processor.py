# /backend/check_image_processor.py

"""
Check which version of image_processing.py is installed
"""

import inspect
from app.services.image_processing import ImageProcessor

def check_version():
    print("=" * 60)
    print("IMAGE PROCESSOR VERSION CHECK")
    print("=" * 60)
    
    processor = ImageProcessor()
    
    # Get all methods
    methods = [method for method in dir(processor) if not method.startswith('_')]
    
    print(f"\nAvailable methods: {len(methods)}")
    for method in methods:
        print(f"  - {method}")
    
    # Check for aggressive preprocessing support
    print("\n" + "=" * 60)
    print("CHECKING FOR ADVANCED FEATURES:")
    print("=" * 60)
    
    # Check method signature
    sig = inspect.signature(processor.preprocess_image)
    params = sig.parameters
    
    print(f"\npreprocess_image() parameters:")
    for param_name, param in params.items():
        print(f"  - {param_name}: {param.default if param.default != inspect.Parameter.empty else 'required'}")
    
    if 'aggressive' in params:
        print("\n✅ ADVANCED VERSION INSTALLED")
        print("   - Has 'aggressive' parameter")
        print("   - Supports poor quality images")
    else:
        print("\n❌ BASIC VERSION INSTALLED")
        print("   - Missing 'aggressive' parameter")
        print("   - Need to replace with advanced version")
    
    # Check for advanced methods
    required_methods = [
        '_aggressive_preprocessing',
        '_standard_preprocessing', 
        '_upscale_if_needed',
        'preprocess_for_table_detection'
    ]
    
    print("\nAdvanced methods check:")
    has_all = True
    for method in required_methods:
        exists = hasattr(processor, method)
        status = "✓" if exists else "✗"
        print(f"  {status} {method}")
        if not exists:
            has_all = False
    
    print("\n" + "=" * 60)
    if has_all and 'aggressive' in params:
        print("STATUS: ✅ FULLY UPDATED - Advanced preprocessing active")
    else:
        print("STATUS: ❌ NEEDS UPDATE - Replace image_processing.py")
        print("\nTO FIX:")
        print("1. Copy advanced image_processing.py to /backend/app/services/")
        print("2. Restart backend")
        print("3. Re-run this check")
    print("=" * 60)

if __name__ == "__main__":
    check_version()