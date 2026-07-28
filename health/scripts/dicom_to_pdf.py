"""CLI: join a folder of DICOM files into a single shareable PDF report."""

from __future__ import annotations

import argparse
import logging
import tempfile
from pathlib import Path

from health.dicom.discovery import group_series
from health.dicom.report import render_pdf

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Procesa recursivamente archivos DICOM y genera un PDF resumen."
    )
    parser.add_argument("root_folder", help="Carpeta raíz que contiene los DICOM")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Nombre del PDF de salida (default: <carpeta>_resumen.pdf)",
    )
    parser.add_argument(
        "--images-per-series",
        type=int,
        default=20,
        help="Máximo de cortes por serie en la hoja de contacto (default: 20)",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=5,
        help="Columnas en la grilla de cada hoja de contacto (default: 5)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Resolución de las hojas de contacto (default: 150)",
    )
    parser.add_argument(
        "--anonymize",
        action="store_true",
        help="Omitir el nombre del paciente en el PDF (se incluye por default)",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Conservar la carpeta temporal con las hojas de contacto generadas",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Salida detallada (debug)"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Solo mostrar advertencias y errores"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")

    root = Path(args.root_folder)
    output = Path(args.output) if args.output else Path(f"{root.name}_resumen.pdf")

    studies = group_series(root)

    if not studies:
        logger.warning("No se encontraron archivos DICOM con PixelData.")
        return

    if args.keep_temp:
        temp_dir = Path(f"{output.stem}_temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        render_pdf(
            studies,
            output,
            temp_dir=temp_dir,
            images_per_series=args.images_per_series,
            cols=args.cols,
            dpi=args.dpi,
            anonymize=args.anonymize,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="dicom_to_pdf_") as tmp:
            render_pdf(
                studies,
                output,
                temp_dir=tmp,
                images_per_series=args.images_per_series,
                cols=args.cols,
                dpi=args.dpi,
                anonymize=args.anonymize,
            )

    logger.info("")
    logger.info("=" * 60)
    logger.info("PDF GENERADO")
    logger.info("=" * 60)
    logger.info("Archivo: %s", output)


if __name__ == "__main__":
    main()
