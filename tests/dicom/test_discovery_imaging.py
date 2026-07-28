import numpy as np
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset

from health.dicom.discovery import group_series
from health.dicom.imaging import apply_windowing


def _make_dicom(path, *, study_uid, series_uid, instance_number, photometric="MONOCHROME2"):
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "MR"
    ds.SeriesNumber = 1
    ds.InstanceNumber = instance_number
    ds.SeriesDescription = "T1"
    ds.BodyPartExamined = "BRAIN"
    ds.PhotometricInterpretation = photometric
    ds.SamplesPerPixel = 1
    ds.Rows = 4
    ds.Columns = 4
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    pixels = np.arange(16, dtype=np.uint16).reshape(4, 4)
    ds.PixelData = pixels.tobytes()

    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(str(path))
    return pixels


def test_group_series_orders_by_instance_number(tmp_path):
    study_uid = pydicom.uid.generate_uid()
    series_uid = pydicom.uid.generate_uid()

    for n in [2, 0, 1]:
        _make_dicom(
            tmp_path / f"slice_{n}.dcm",
            study_uid=study_uid,
            series_uid=series_uid,
            instance_number=n,
        )

    studies = group_series(tmp_path)

    assert list(studies.keys()) == [study_uid]
    slices = studies[study_uid][series_uid]
    assert [s.get("InstanceNumber") for s in slices] == [0, 1, 2]


def test_apply_windowing_inverts_monochrome1():
    ds = pydicom.Dataset()
    ds.PhotometricInterpretation = "MONOCHROME1"

    image = np.array([[0, 100], [200, 255]], dtype=np.float32)
    normal = apply_windowing(ds, image.copy())

    ds.PhotometricInterpretation = "MONOCHROME2"
    inverted_reference = apply_windowing(ds, image.copy())

    assert np.allclose(normal, 1.0 - inverted_reference)
