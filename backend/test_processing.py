# /backend/test_preprocessing.py

"""
Quick test to verify aggressive image preprocessing is working
"""

import cv2
import numpy as np
from app.services.image_processing import ImageProcessor

def test_preprocessing():
    """Test both standard and aggressive preprocessing"""
    
    # Test image path - use your uploaded hospital bill
    test_image = "uploads/your_hospital_bill.jpg"  # Change this to actual path
    
    processor = ImageProcessor()
    
    print("=" * 60)
    print("IMAGE PREPROCESSING TEST")
    print("=" * 60)
    
    # Test 1: Check if aggressive parameter exists
    try:
        print("\n1. Testing Standard Preprocessing...")
        standard = processor.preprocess_image(test_image, aggressive=False)
        print(f"   ✓ Standard preprocessing works")
        print(f"   Output shape: {standard.shape}")
    except Exception as e:
        print(f"   ✗ Standard preprocessing failed: {e}")
        return False
    
    # Test 2: Check if aggressive mode works
    try:
        print("\n2. Testing Aggressive Preprocessing...")
        aggressive = processor.preprocess_image(test_image, aggressive=True)
        print(f"   ✓ Aggressive preprocessing works")
        print(f"   Output shape: {aggressive.shape}")
    except Exception as e:
        print(f"   ✗ Aggressive preprocessing failed: {e}")
        return False
    
    # Test 3: Compare outputs
    print("\n3. Comparing Results...")
    print(f"   Standard size: {standard.shape}")
    print(f"   Aggressive size: {aggressive.shape}")
    
    if aggressive.shape[0] > standard.shape[0]:
        print(f"   ✓ Aggressive mode upscaling works! ({aggressive.shape[0] / standard.shape[0]:.2f}x larger)")
    else:
        print(f"   ✗ Aggressive mode NOT upscaling - check implementation")
    
    # Test 4: Save comparison images
    try:
        cv2.imwrite("test_standard.png", standard)
        cv2.imwrite("test_aggressive.png", aggressive)
        print("\n4. Saved test images:")
        print("   - test_standard.png")
        print("   - test_aggressive.png")
        print("   Compare these visually to see the difference")
    except Exception as e:
        print(f"   ✗ Could not save images: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_preprocessing()