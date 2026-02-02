# /backend/app/services/image_processing.py

import cv2
import numpy as np
from PIL import Image

class ImageProcessor:
    """Image preprocessing for better OCR results"""
    
    @staticmethod
    def preprocess_image(image_path: str) -> np.ndarray:
        """
        Preprocess image for OCR:
        - Convert to grayscale
        - Denoise
        - Increase contrast
        - Binarization
        """
        # Read image
        img = cv2.imread(image_path)
        
        if img is None:
            raise ValueError(f"Could not read image from {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(denoised)
        
        # Binarization using Otsu's method
        _, binary = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    @staticmethod
    def deskew_image(image: np.ndarray) -> np.ndarray:
        """Deskew image if tilted"""
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only deskew if angle is significant
        if abs(angle) > 0.5:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
        
        return image
    
    @staticmethod
    def resize_if_needed(image: np.ndarray, max_width: int = 2000) -> np.ndarray:
        """Resize image if too large"""
        height, width = image.shape[:2]
        
        if width > max_width:
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            return resized
        
        return image
    
    @staticmethod
    def get_pil_image(image_path: str) -> Image.Image:
        """Get PIL Image object"""
        return Image.open(image_path)