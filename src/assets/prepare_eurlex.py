from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

DATASET_URL = "http://nlp.cs.aueb.gr/software_and_datasets/EURLEX57K/datasets.zip"

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
ZIP_PATH = ASSETS_DIR / "datasets.zip"
EXTRACTED_DIR = ASSETS_DIR / "dataset"
PDFS_DIR = ASSETS_DIR / "pdfs"


def ensure_assets_dirs() -> None:
	ASSETS_DIR.mkdir(parents=True, exist_ok=True)
	PDFS_DIR.mkdir(parents=True, exist_ok=True)


def wget_if_needed(url: str = DATASET_URL, dest: Path = ZIP_PATH) -> Path:
	"""Download with wget only if file does not already exist."""
	ensure_assets_dirs()
	if dest.exists() and dest.stat().st_size > 0:
		return dest
	subprocess.run(["wget", "-O", str(dest), url], check=True)
	return dest


def unzip_if_needed(zip_path: Path = ZIP_PATH, dest_dir: Path = ASSETS_DIR) -> Path:
	"""Extract the zip once; assumes it contains a 'dataset/' directory."""
	ensure_assets_dirs()
	if EXTRACTED_DIR.exists() and any(EXTRACTED_DIR.iterdir()):
		return EXTRACTED_DIR
	with ZipFile(zip_path, "r") as zf:
		zf.extractall(dest_dir)
	return EXTRACTED_DIR


def iter_json_files(split_dir: Path) -> Iterable[Path]:
	for p in sorted(split_dir.glob("*.json")):
		yield p


def json_to_pdf(json_path: Path, output_dir: Path = PDFS_DIR) -> Path:
	"""Convert a single EURLEX JSON file to a PDF using the provided structure."""
	output_dir.mkdir(parents=True, exist_ok=True)
	with json_path.open("r", encoding="utf-8") as f:
		data = json.load(f)

	pdf_path = output_dir / f"{data['celex_id']}.pdf"
	doc = SimpleDocTemplate(
		str(pdf_path),
		pagesize=A4,
		rightMargin=72,
		leftMargin=72,
		topMargin=72,
		bottomMargin=72,
	)

	styles = getSampleStyleSheet()
	styles.add(ParagraphStyle(name="Heading", fontSize=14, leading=18, spaceAfter=10, bold=True))
	styles.add(ParagraphStyle(name="SubHeading", fontSize=12, leading=16, spaceAfter=8, bold=True))
	styles.add(ParagraphStyle(name="Body", fontSize=10, leading=14))

	elements = []
	elements.append(Paragraph(f"<b>Celex ID:</b> {data.get('celex_id','')}", styles["Body"]))
	elements.append(Paragraph(f"<b>URI:</b> {data.get('uri','')}", styles["Body"]))
	elements.append(Paragraph(f"<b>Type:</b> {data.get('type','')}", styles["Body"]))
	concepts = ", ".join(data.get("concepts", []) or [])
	elements.append(Paragraph(f"<b>Concepts:</b> {concepts}", styles["Body"]))
	elements.append(Spacer(1, 0.2 * inch))

	elements.append(Paragraph(f"<b>Title:</b> {data.get('title','')}", styles["Heading"]))
	elements.append(Spacer(1, 0.2 * inch))

	recitals = data.get("recitals")
	if recitals:
		recitals_text = str(recitals).replace("\n", "<br/>")
		elements.append(Paragraph("<b>Recitals:</b>", styles["SubHeading"]))
		elements.append(Paragraph(recitals_text, styles["Body"]))
		elements.append(Spacer(1, 0.3 * inch))

	main_body = data.get("main_body") or []
	if main_body:
		elements.append(Paragraph("<b>Main Body:</b>", styles["SubHeading"]))
		for section in main_body:
			section_text = str(section).replace("\n", "<br/>")
			elements.append(Paragraph(section_text, styles["Body"]))
			elements.append(Spacer(1, 0.2 * inch))

	attachments = data.get("attachments")
	if attachments:
		attachments_text = str(attachments).replace("\n", "<br/>")
		elements.append(Paragraph("<b>Attachments:</b>", styles["SubHeading"]))
		elements.append(Paragraph(attachments_text, styles["Body"]))
		elements.append(Spacer(1, 0.3 * inch))

	doc.build(elements)
	return pdf_path


def convert_split_to_pdfs(split_name: str, dataset_root: Path = EXTRACTED_DIR, output_dir: Path = PDFS_DIR, max_docs: int = -1) -> None:
	split_dir = dataset_root / split_name
	if not split_dir.exists():
		return
	processed = 0
	for json_file in iter_json_files(split_dir):
		if max_docs > 0 and processed >= max_docs:
			break
		json_to_pdf(json_file, output_dir)
		processed += 1


def prepare_eurlex_pdfs() -> None:
	zip_path = wget_if_needed(DATASET_URL, ZIP_PATH)
	_ = unzip_if_needed(zip_path, ASSETS_DIR)
	for split in ("train", "test", "dev"):
		convert_split_to_pdfs(split, EXTRACTED_DIR, PDFS_DIR)


def _parse_args():
	import argparse
	parser = argparse.ArgumentParser(description="Prepare EURLEX PDFs: download, extract, and convert JSONs to PDFs.")
	parser.add_argument("--skipo", action="store_true", help="Skip wget download step (or set env SKIPO=1).")
	parser.add_argument("--no_docs", type=int, default=-1, help="Number of documents to process per split. Use -1 or omit for all documents.")
	return parser.parse_args()


def _should_skip_download(args) -> bool:
	val = os.getenv("SKIPO", "").strip().lower()
	env_skip = val in {"1", "true", "yes", "y"}
	return bool(args.skipo or env_skip)


def main() -> None:
	args = _parse_args()
	ensure_assets_dirs()
	if not _should_skip_download(args):
		zip_path = wget_if_needed(DATASET_URL, ZIP_PATH)
	else:
		zip_path = ZIP_PATH
	_ = unzip_if_needed(zip_path, ASSETS_DIR)
	for split in ("train", "test", "dev"):
		convert_split_to_pdfs(split, EXTRACTED_DIR, PDFS_DIR, max_docs=args.no_docs)


if __name__ == "__main__":
	main()
