"""Find and group DICOM files under a directory tree without loading pixel data."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pydicom

logger = logging.getLogger(__name__)

UNKNOWN_STUDY = "UNKNOWN_STUDY"
UNKNOWN_SERIES = "UNKNOWN_SERIES"


def is_dicom_file(path: Path) -> bool:
    """Detect whether a file looks like a DICOM dataset, extension notwithstanding."""

    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
    except Exception:
        return False

    return (
        hasattr(ds, "SOPClassUID")
        or hasattr(ds, "Modality")
        or hasattr(ds, "SeriesInstanceUID")
    )


@dataclass
class SliceRef:
    """Header-only reference to a single DICOM slice on disk."""

    path: Path
    dataset: pydicom.Dataset = field(repr=False)

    @property
    def sort_key(self) -> float:
        if hasattr(self.dataset, "InstanceNumber"):
            try:
                return int(self.dataset.InstanceNumber)
            except Exception:
                pass

        if hasattr(self.dataset, "ImagePositionPatient"):
            try:
                return float(self.dataset.ImagePositionPatient[2])
            except Exception:
                pass

        return 0

    def get(self, tag: str, default=None):
        return getattr(self.dataset, tag, default)


def _series_sort_key(series: list[SliceRef]) -> tuple:
    try:
        return (int(series[0].get("SeriesNumber", 0) or 0),)
    except Exception:
        return (0,)


def group_series(
    root_folder: str | Path,
) -> dict[str, dict[str, list[SliceRef]]]:
    """Recursively find DICOM files below root_folder and group them by study/series.

    Only headers are read (stop_before_pixels=True) - no pixel data is loaded
    here, so this stays cheap even for studies with hundreds of slices.
    Series within a study are ordered by SeriesNumber, and slices within a
    series are ordered by instance number / slice position.
    """

    root = Path(root_folder)
    logger.info("Buscando DICOMs en: %s", root)

    raw: dict[str, dict[str, list[SliceRef]]] = defaultdict(lambda: defaultdict(list))

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        try:
            ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        except Exception as exc:
            logger.debug("Omitido %s: %s", path, exc)
            continue

        if not (
            hasattr(ds, "SOPClassUID")
            or hasattr(ds, "Modality")
            or hasattr(ds, "SeriesInstanceUID")
        ):
            continue

        study_uid = getattr(ds, "StudyInstanceUID", UNKNOWN_STUDY)
        series_uid = getattr(ds, "SeriesInstanceUID", UNKNOWN_SERIES)

        raw[study_uid][series_uid].append(SliceRef(path=path, dataset=ds))
        logger.debug(
            "[OK] %s | Study=%s | Series=%s",
            path.name,
            study_uid[-8:],
            series_uid[-8:],
        )

    studies: dict[str, dict[str, list[SliceRef]]] = {}
    for study_uid, series_dict in raw.items():
        ordered_series = sorted(series_dict.items(), key=lambda kv: _series_sort_key(kv[1]))
        studies[study_uid] = {
            series_uid: sorted(slices, key=lambda s: s.sort_key)
            for series_uid, slices in ordered_series
        }

    return studies
