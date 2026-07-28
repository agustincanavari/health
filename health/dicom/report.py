"""Assemble a PDF report (cover/index page + per-series contact sheets)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from health.dicom.discovery import SliceRef
from health.dicom.imaging import build_contact_sheet

logger = logging.getLogger(__name__)

REDACTED = "Anonimizado"
UNKNOWN = "Desconocido"


@dataclass
class PatientInfo:
    name: str
    study_date: str

    @classmethod
    def from_slice(cls, slice_ref: SliceRef) -> "PatientInfo":
        return cls(
            name=str(slice_ref.get("PatientName", UNKNOWN)),
            study_date=str(slice_ref.get("StudyDate", UNKNOWN)),
        )

    def redacted(self) -> "PatientInfo":
        return PatientInfo(name=REDACTED, study_date=self.study_date)


def series_description(series: list[SliceRef]) -> str:
    first = series[0]
    description = first.get("SeriesDescription", "Sin descripción")
    modality = first.get("Modality", "?")
    body_part = first.get("BodyPartExamined", "?")
    return f"{description} | Modalidad: {modality} | Zona: {body_part}"


def render_pdf(
    studies: dict[str, dict[str, list[SliceRef]]],
    output_path: str | Path,
    *,
    temp_dir: str | Path,
    images_per_series: int = 20,
    cols: int = 5,
    dpi: int = 150,
    anonymize: bool = False,
) -> None:
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    all_series = [
        (series_uid, series)
        for series_dict in studies.values()
        for series_uid, series in series_dict.items()
    ]
    total_images = sum(len(series) for _, series in all_series)

    patient = PatientInfo.from_slice(all_series[0][1][0]) if all_series else None
    if patient and anonymize:
        patient = patient.redacted()

    story = []
    story.append(Paragraph("DICOM MRI Viewer - Resumen", styles["Title"]))
    story.append(Spacer(1, 0.3 * cm))

    if patient:
        story.append(
            Paragraph(
                f"<b>Paciente:</b> {patient.name} | <b>Fecha:</b> {patient.study_date}",
                styles["Normal"],
            )
        )

    story.append(
        Paragraph(
            f"Estudios: {len(studies)} | "
            f"Series: {len(all_series)} | "
            f"Imágenes: {total_images}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    index_rows = [["#", "Descripción", "Modalidad", "Zona", "Cortes"]]
    for i, (_, series) in enumerate(all_series, start=1):
        first = series[0]
        index_rows.append(
            [
                str(i),
                str(first.get("SeriesDescription", "Sin descripción")),
                str(first.get("Modality", "?")),
                str(first.get("BodyPartExamined", "?")),
                str(len(series)),
            ]
        )

    index_table = Table(index_rows, hAlign="LEFT")
    index_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dddddd")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(index_table)
    story.append(PageBreak())

    for i, (_, series) in enumerate(all_series, start=1):
        first = series[0]
        description = series_description(series)

        output_image = temp_dir / f"series_{i}.png"
        logger.info("Generando serie %d: %s", i, description)
        build_contact_sheet(series, output_image, images_per_series, cols, dpi)

        story.append(Paragraph(f"Serie {i}", styles["Heading1"]))
        story.append(
            Paragraph(
                f"<b>Descripción:</b> {description}<br/>"
                f"<b>Cortes totales:</b> {len(series)}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.4 * cm))

        img = Image(str(output_image))
        max_width, max_height = 25 * cm, 16 * cm
        scale = min(max_width / img.imageWidth, max_height / img.imageHeight)
        img.drawWidth *= scale
        img.drawHeight *= scale
        story.append(img)
        story.append(PageBreak())

    doc.build(story)
