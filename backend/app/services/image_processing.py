# /backend/app/services/image_processing.py

import io
import cv2
import numpy as np
from PIL import Image, ImageEnhance


# ── Constants ────────────────────────────────────────────────────────────────

# DPI to embed in all intermediate images handed to Tesseract.
# The source TIFFs often carry broken metadata (e.g. dpi=1,1).  Tesseract uses
# DPI to estimate character size; wrong DPI → complete misread.
TESSERACT_DPI = 300

# Fixed-threshold value used for clean / digital-style scans.
# Pixels darker than this become black; everything else white.
# 180 keeps light-grey form-field text while dropping the blue/grey fill.
CLEAN_SCAN_THRESHOLD = 180

# Only run fastNlMeansDenoising when image noise exceeds this std-dev level.
NOISE_STDDEV_THRESHOLD = 15.0


class ImageProcessor:
    """Image preprocessing for better OCR results."""

    # ── Public helpers ────────────────────────────────────────────────────────

    @staticmethod
    def pil_to_tesseract_png(pil_img: Image.Image, dpi: int = TESSERACT_DPI) -> Image.Image:
        """
        Round-trip a PIL image through an in-memory PNG so that DPI metadata
        is correctly embedded.  This is the single most important fix: TIFFs
        (and numpy arrays) handed to Tesseract without DPI info cause Tesseract
        to misestimate character size and produce garbage output.
        """
        buf = io.BytesIO()
        # Convert to RGB/L first — PNG doesn't support RGBA with dpi kwarg
        mode = "L" if pil_img.mode == "L" else "RGB"
        pil_img.convert(mode).save(buf, format="PNG", dpi=(dpi, dpi))
        buf.seek(0)
        return Image.open(buf)

    @staticmethod
    def _estimate_noise(gray: np.ndarray) -> float:
        """Return a simple noise estimate (local std-dev via Laplacian variance)."""
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return float(lap.var() ** 0.5)

    @staticmethod
    def preprocess_image(image_path: str) -> Image.Image:
        """
        Preprocess an image for OCR and return a DPI-stamped PIL image.

        Pipeline (all steps justified below):

        1.  Open via PIL — handles TIFF variants, RGBA, palette, 16-bit, etc.
        2.  Contrast + sharpness boost — makes light-grey field text pop against
            the blue/grey form background before we go monochrome.
        3.  Convert to grayscale.
        4.  Conditional denoising — skip for clean scans (noise blurs fine
            strokes and degrades accuracy); only run when noise std-dev is high.
        5.  Fixed threshold at 180 — adaptive threshold with blockSize=31
            uses the local neighbourhood mean as reference.  When text sits
            inside a lightly-filled box the box background *is* the local mean,
            so the threshold nearly equals the text luminance → text disappears.
            A fixed threshold of 180 reliably separates dark text from light
            fills while retaining grey-on-white field entries.
        6.  Embed DPI=300 metadata — critical for Tesseract accuracy.
        """
        # ── 1. Open ──────────────────────────────────────────────────────────
        pil_img = Image.open(image_path)

        # ── 2. Contrast / sharpness boost ────────────────────────────────────
        # Boost contrast before grayscale so that light-grey field text (which
        # lives in blue/grey boxes) isn't collapsed into the background.
        pil_img = pil_img.convert("RGB")
        pil_img = ImageEnhance.Contrast(pil_img).enhance(2.0)
        pil_img = ImageEnhance.Sharpness(pil_img).enhance(2.0)

        # ── 3. Grayscale ──────────────────────────────────────────────────────
        gray_pil = pil_img.convert("L")
        gray = np.array(gray_pil)

        # ── 4. Conditional denoising ──────────────────────────────────────────
        noise = ImageProcessor._estimate_noise(gray)
        if noise > NOISE_STDDEV_THRESHOLD:
            gray = cv2.fastNlMeansDenoising(
                gray, None, h=7, templateWindowSize=7, searchWindowSize=21
            )

        # ── 5. Fixed threshold ────────────────────────────────────────────────
        _, binary = cv2.threshold(gray, CLEAN_SCAN_THRESHOLD, 255, cv2.THRESH_BINARY)

        # ── 6. Embed DPI metadata ─────────────────────────────────────────────
        pil_binary = Image.fromarray(binary)
        return ImageProcessor.pil_to_tesseract_png(pil_binary)

    @staticmethod
    def deskew_image(image: np.ndarray) -> np.ndarray:
        """Deskew image if tilted (operates on numpy arrays only)."""
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
            image = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

        return image

    @staticmethod
    def resize_if_needed(
        image: np.ndarray,
        target_width: int = 2400,
        max_width: int = 3000,
    ) -> np.ndarray:
        """
        Resize image for optimal OCR resolution (~300 DPI equivalent).

        - Upscales images narrower than target_width using INTER_CUBIC.
        - Downscales images wider than max_width using INTER_AREA.
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
        """Return a normalised RGB PIL image."""
        return Image.open(image_path).convert("RGB")

    @staticmethod
    def load_all_pages(image_path: str) -> list[Image.Image]:
        """
        Load all pages from a multi-page TIFF (or any single-page image).
        Returns a list of PIL Images (one per page) normalised to RGB.
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