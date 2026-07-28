"""Pixel loading, windowing, and contact-sheet rendering for DICOM slices."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pydicom

from health.dicom.discovery import SliceRef

logger = logging.getLogger(__name__)


def load_pixels(slice_ref: SliceRef) -> np.ndarray:
    """Fully read a slice from disk, including pixel data."""

    ds = pydicom.dcmread(str(slice_ref.path), force=True)
    image = ds.pixel_array

    if image.ndim > 2:
        image = image[0]

    return apply_windowing(ds, image)


def apply_windowing(ds: pydicom.Dataset, image: np.ndarray) -> np.ndarray:
    """Apply rescale slope/intercept and window center/width, normalized to [0, 1].

    Falls back to 1st/99th percentile clipping when no window is present, and
    inverts MONOCHROME1 images so they display the same as MONOCHROME2.
    """

    image = image.astype(np.float32)

    slope = float(getattr(ds, "RescaleSlope", 1))
    intercept = float(getattr(ds, "RescaleIntercept", 0))
    image = image * slope + intercept

    wc = getattr(ds, "WindowCenter", None)
    ww = getattr(ds, "WindowWidth", None)

    if wc is not None and ww is not None:
        wc = float(wc[0]) if isinstance(wc, pydicom.multival.MultiValue) else float(wc)
        ww = float(ww[0]) if isinstance(ww, pydicom.multival.MultiValue) else float(ww)
        low = wc - ww / 2
        high = wc + ww / 2
    else:
        low = np.percentile(image, 1)
        high = np.percentile(image, 99)

    image = np.clip(image, low, high)

    if high > low:
        image = (image - low) / (high - low)

    if getattr(ds, "PhotometricInterpretation", None) == "MONOCHROME1":
        image = 1.0 - image

    return image


def build_contact_sheet(
    slices: list[SliceRef],
    output_path: str | Path,
    max_images: int = 20,
    cols: int = 5,
    dpi: int = 150,
) -> None:
    """Render a grid of representative slices from a series to an image file."""

    if len(slices) > max_images:
        indices = np.linspace(0, len(slices) - 1, max_images, dtype=int)
        selected = [slices[i] for i in indices]
    else:
        selected = slices

    rows = int(np.ceil(len(selected) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(15, 3 * rows))
    axes = np.array(axes).reshape(-1)

    for ax in axes:
        ax.axis("off")

    for i, slice_ref in enumerate(selected):
        try:
            image = load_pixels(slice_ref)
            axes[i].imshow(image, cmap="gray")
            instance = slice_ref.get("InstanceNumber", i)
            axes[i].set_title(f"Corte {instance}", fontsize=8)
        except Exception as exc:
            logger.warning("Error renderizando %s: %s", slice_ref.path, exc)
            axes[i].text(0.5, 0.5, f"Error\n{exc}", ha="center", va="center")

    plt.tight_layout()
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
