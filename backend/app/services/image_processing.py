# # # /backend/app/services/image_processing.py

# # import cv2
# # import numpy as np
# # from PIL import Image, ImageEnhance


# # class ImageProcessor:
# #     """Image preprocessing for better OCR results"""

# #     @staticmethod
# #     def preprocess_image(image_path: str) -> np.ndarray:
# #         """
# #         Preprocess image for OCR:
# #         - Load via PIL (handles TIFF, multi-page, 16-bit, palette modes, etc.)
# #         - Convert to grayscale
# #         - Denoise (conservative to preserve fine strokes)
# #         - Adaptive thresholding (handles uneven lighting in scanned forms)
# #         """
# #         # Use PIL to open — cv2.imread() silently fails on many TIFF variants
# #         pil_img = Image.open(image_path)

# #         # Normalize to RGB (handles palette, CMYK, grayscale, 16-bit, etc.)
# #         pil_img = pil_img.convert("RGB")

# #         # Enhance sharpness slightly before converting — helps with soft scans
# #         pil_img = ImageEnhance.Sharpness(pil_img).enhance(1.5)

# #         # Convert to OpenCV BGR array
# #         img = np.array(pil_img)
# #         img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

# #         # Convert to grayscale
# #         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# #         # Conservative denoise — preserves fine character strokes
# #         # Lower h (7 vs 10) avoids blurring thin letterforms
# #         denoised = cv2.fastNlMeansDenoising(
# #             gray,
# #             None,
# #             h=7,
# #             templateWindowSize=7,
# #             searchWindowSize=21,
# #         )

# #         # Adaptive threshold instead of Otsu's global threshold.
# #         # Scanned forms have dark borders, shaded cells, and faint pre-printed
# #         # text — adaptive thresholding handles local contrast zones far better.
# #         binary = cv2.adaptiveThreshold(
# #             denoised,
# #             255,
# #             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
# #             cv2.THRESH_BINARY,
# #             blockSize=31,   # Larger block = more tolerant of shading gradients
# #             C=10,           # Constant subtracted from mean; tune up if background is noisy
# #         )

# #         return binary

# #     @staticmethod
# #     def deskew_image(image: np.ndarray) -> np.ndarray:
# #         """Deskew image if tilted"""
# #         coords = np.column_stack(np.where(image > 0))

# #         if coords.size == 0:
# #             return image

# #         angle = cv2.minAreaRect(coords)[-1]

# #         if angle < -45:
# #             angle = -(90 + angle)
# #         else:
# #             angle = -angle

# #         # Only deskew if angle is significant
# #         if abs(angle) > 0.5:
# #             (h, w) = image.shape[:2]
# #             center = (w // 2, h // 2)
# #             M = cv2.getRotationMatrix2D(center, angle, 1.0)
# #             rotated = cv2.warpAffine(
# #                 image,
# #                 M,
# #                 (w, h),
# #                 flags=cv2.INTER_CUBIC,
# #                 borderMode=cv2.BORDER_REPLICATE,
# #             )
# #             return rotated

# #         return image

# #     @staticmethod
# #     def resize_if_needed(
# #         image: np.ndarray,
# #         target_width: int = 2400,
# #         max_width: int = 3000,
# #     ) -> np.ndarray:
# #         """
# #         Resize image for optimal OCR resolution (~300 DPI equivalent).

# #         - Upscales images narrower than target_width using INTER_CUBIC
# #           (better quality when enlarging).
# #         - Downscales images wider than max_width using INTER_AREA
# #           (better quality when shrinking).
# #         - Leaves images within range untouched.
# #         """
# #         height, width = image.shape[:2]

# #         if width < target_width:
# #             # Upscale — scans at lower resolution need enlarging for Tesseract
# #             ratio = target_width / width
# #             new_size = (target_width, int(height * ratio))
# #             return cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)

# #         if width > max_width:
# #             # Downscale — avoid excessive memory usage and slow processing
# #             ratio = max_width / width
# #             new_size = (max_width, int(height * ratio))
# #             return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

# #         return image

# #     @staticmethod
# #     def get_pil_image(image_path: str) -> Image.Image:
# #         """Get PIL Image object (normalized to RGB)"""
# #         img = Image.open(image_path)
# #         return img.convert("RGB")

# #     @staticmethod
# #     def load_all_pages(image_path: str) -> list[Image.Image]:
# #         """
# #         Load all pages from a multi-page TIFF (or single-page image).

# #         Returns a list of PIL Images, one per page.
# #         """
# #         pages = []
# #         img = Image.open(image_path)
# #         page_index = 0

# #         while True:
# #             try:
# #                 img.seek(page_index)
# #                 pages.append(img.copy().convert("RGB"))
# #                 page_index += 1
# #             except EOFError:
# #                 break

# #         return pages if pages else [img.convert("RGB")]

import cv2
import numpy as np
from PIL import Image, ImageEnhance


class ImageProcessor:
    """Image preprocessing for better OCR results"""

    @staticmethod
    def _load_as_gray(image_path: str) -> np.ndarray:
        """
        Load any image format as a grayscale numpy array.

        Uses PIL instead of cv2.imread() because cv2 silently returns None
        for many TIFF variants (LZW-compressed, RGBA, 16-bit, multi-page).

        Also handles RGBA correctly — drops the alpha channel before converting
        to grayscale. RGBA fed directly to cv2.cvtColor(BGR2GRAY) produces
        wrong results because the alpha channel skews the luminance calculation.
        """
        pil_img = Image.open(image_path)
        pil_img.seek(0)                    # always use first frame/page
        pil_img = pil_img.convert("RGB")   # RGBA/palette/CMYK → clean RGB
        arr = np.array(pil_img)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def _contrast_stretch(gray: np.ndarray, lo: float = 5, hi: float = 95) -> np.ndarray:
        """
        Percentile-based contrast stretch.

        Why not CLAHE alone: this TIFF has 95.9% bright pixels and only 1.9%
        dark (text) pixels. CLAHE's tile-based histogram equalization barely
        moves the needle because each tile is dominated by background pixels.
        Stretching the 5th–95th percentile range to 0–255 first gives CLAHE
        something useful to work with.
        """
        p_lo = np.percentile(gray, lo)
        p_hi = np.percentile(gray, hi)
        denom = max(float(p_hi - p_lo), 1.0)
        stretched = np.clip((gray.astype(np.float32) - p_lo) / denom * 255, 0, 255)
        return stretched.astype(np.uint8)

    @staticmethod
    def preprocess_image(image_path: str) -> np.ndarray:
        """
        Preprocess image for Tesseract OCR → returns binary (0/255) array.

        Tesseract is a classical CV engine — it works best on clean binary
        images where text pixels are black (0) and background is white (255).
        Adaptive thresholding is used instead of Otsu's global threshold
        because scanned forms have shaded cells, dark borders, and stamp ink
        that shift the global histogram and cause Otsu to pick a bad midpoint.
        """
        gray = ImageProcessor._load_as_gray(image_path)

        # Stretch contrast before thresholding so faint text becomes visible
        stretched = ImageProcessor._contrast_stretch(gray)

        # Mild denoise — conservative to preserve thin stroke edges
        denoised = cv2.fastNlMeansDenoising(
            stretched, None, h=7, templateWindowSize=7, searchWindowSize=21
        )

        # Adaptive threshold with a 25-pixel block.
        # Smaller block (vs 31) catches tighter local regions like small
        # handwritten characters; C=8 keeps faint pre-printed text visible.
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=25,
            C=8,
        )

        return binary

    @staticmethod
    def preprocess_image_for_easyocr(image_path: str) -> np.ndarray:
        """
        Preprocess image specifically for EasyOCR → returns grayscale array.

        EasyOCR uses a deep learning text detector (CRAFT) followed by a
        recognition CNN. Both are trained on natural/grayscale images and rely
        on gradient information (stroke edges, ink density variation) that is
        destroyed by binarization.

        Feeding a binary (0/255) image to EasyOCR causes two problems:
          1. CRAFT loses the gradient cues it uses to score text regions,
             producing fewer and weaker detections.
          2. The recognition CNN sees hard black/white edges instead of the
             soft gradients it was trained on, reducing character accuracy.

        This pipeline preserves grayscale while maximising local contrast so
        EasyOCR's detector can find text regions reliably.
        """
        gray = ImageProcessor._load_as_gray(image_path)

        # Contrast stretch — critical for this TIFF which has std≈32 raw
        # (almost all pixels are near-white). Stretch brings std up to ~70+.
        stretched = ImageProcessor._contrast_stretch(gray, lo=5, hi=95)

        # CLAHE after stretch for local contrast boost
        # Smaller tile (4,4) handles the fine-grained contrast variation in
        # handwritten form fill-ins better than the default (8,8)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(stretched)

        # Unsharp mask sharpen — makes character stroke edges crisper for the
        # CRAFT detector without introducing ringing artifacts
        blurred = cv2.GaussianBlur(enhanced, (0, 0), 2)
        sharpened = cv2.addWeighted(enhanced, 1.8, blurred, -0.8, 0)

        return sharpened

    @staticmethod
    def deskew_image(image: np.ndarray) -> np.ndarray:
        """Deskew image if tilted"""
        coords = np.column_stack(np.where(image > 0))

        if coords.size == 0:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > 0.5:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated

        return image

    @staticmethod
    def resize_if_needed(
        image: np.ndarray,
        target_width: int = 2400,
        max_width: int = 3000,
    ) -> np.ndarray:
        """
        Resize image for optimal OCR resolution (~300 DPI equivalent).

        - Upscales images narrower than target_width using INTER_CUBIC
          (better quality when enlarging).
        - Downscales images wider than max_width using INTER_AREA
          (better quality when shrinking).
        - Leaves images within range untouched.
        """
        height, width = image.shape[:2]

        if width < target_width:
            ratio = target_width / width
            new_size = (target_width, int(height * ratio))
            return cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)

        if width > max_width:
            ratio = max_width / width
            new_size = (max_width, int(height * ratio))
            return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

        return image

    @staticmethod
    def get_pil_image(image_path: str) -> Image.Image:
        """Get PIL Image object (normalized to RGB)"""
        img = Image.open(image_path)
        return img.convert("RGB")

    @staticmethod
    def load_all_pages(image_path: str) -> list[Image.Image]:
        """
        Load all pages from a multi-page TIFF (or single-page image).
        Returns a list of PIL Images, one per page.
        """
        pages = []
        img = Image.open(image_path)
        page_index = 0

        while True:
            try:
                img.seek(page_index)
                pages.append(img.copy().convert("RGB"))
                page_index += 1
            except EOFError:
                break

        return pages if pages else [img.convert("RGB")]
