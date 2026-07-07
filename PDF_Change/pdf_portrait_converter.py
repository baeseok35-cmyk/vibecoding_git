from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf._page import PageObject
except ImportError:  # pragma: no cover - handled at runtime for users.
    PdfReader = None
    PdfWriter = None
    Transformation = None
    PageObject = None


TEMP_SUFFIX = ".__split_tmp__"
MODIFIED_FILES_LOG = Path(__file__).with_name("modified_files.txt")


@dataclass
class ConversionResult:
    source: Path
    output: Path | None
    converted_pages: int
    total_pages: int
    status: str


def visible_page_size(page) -> tuple[float, float]:
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    if page.rotation % 180 == 90:
        return height, width
    return width, height


def is_landscape(page) -> bool:
    width, height = visible_page_size(page)
    return width > height


def normalized_page(page):
    normalized = copy.copy(page)
    if normalized.rotation:
        normalized.transfer_rotation_to_content()
    return normalized


def split_landscape_page(page) -> list:
    source = normalized_page(page)
    left = float(source.mediabox.left)
    bottom = float(source.mediabox.bottom)
    right = float(source.mediabox.right)
    top = float(source.mediabox.top)
    width = right - left
    height = top - bottom
    half_width = width / 2
    midpoint = left + half_width

    split_pages = []
    for x_offset in (left, midpoint):
        new_page = PageObject.create_blank_page(width=half_width, height=height)
        new_page.merge_transformed_page(
            source,
            Transformation().translate(tx=-x_offset, ty=-bottom),
        )
        split_pages.append(new_page)

    return split_pages


def temp_path_for(pdf_path: Path) -> Path:
    index = 1
    while True:
        candidate = pdf_path.with_name(
            f"{pdf_path.stem}{TEMP_SUFFIX}{index}{pdf_path.suffix}"
        )
        if not candidate.exists():
            return candidate
        index += 1


def convert_pdf(pdf_path: Path) -> ConversionResult:
    if PdfReader is None or PdfWriter is None or PageObject is None or Transformation is None:
        raise RuntimeError(
            "pypdf is not installed. Install it with: python -m pip install -r requirements.txt"
        )

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    converted_pages = 0

    for page in reader.pages:
        if is_landscape(page):
            for split_page in split_landscape_page(page):
                writer.add_page(split_page)
            converted_pages += 1
        else:
            writer.add_page(page)

    total_pages = len(reader.pages)
    if converted_pages == 0:
        return ConversionResult(
            source=pdf_path,
            output=None,
            converted_pages=0,
            total_pages=total_pages,
            status="skipped_portrait",
        )

    temp_path = temp_path_for(pdf_path)
    try:
        with temp_path.open("wb") as output_file:
            writer.write(output_file)
        temp_path.replace(pdf_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return ConversionResult(
        source=pdf_path,
        output=pdf_path,
        converted_pages=converted_pages,
        total_pages=total_pages,
        status="converted",
    )


def iter_pdf_files(folder: Path, recursive: bool = False):
    pattern = "**/*.pdf" if recursive else "*.pdf"
    for pdf_path in sorted(folder.glob(pattern)):
        if pdf_path.is_file() and TEMP_SUFFIX not in pdf_path.stem:
            yield pdf_path


def convert_folder(
    folder: Path,
    recursive: bool = False,
) -> list[ConversionResult]:
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder does not exist: {folder}")

    results: list[ConversionResult] = []
    for pdf_path in iter_pdf_files(folder, recursive=recursive):
        try:
            results.append(convert_pdf(pdf_path))
        except Exception as exc:
            results.append(
                ConversionResult(
                    source=pdf_path,
                    output=None,
                    converted_pages=0,
                    total_pages=0,
                    status=f"error: {exc}",
                )
            )
    return results


def write_modified_files_log(
    results: list[ConversionResult],
    base_folder: Path,
    log_path: Path = MODIFIED_FILES_LOG,
) -> None:
    changed_files = []
    for result in results:
        if result.status == "converted":
            try:
                changed_files.append(str(result.source.relative_to(base_folder)))
            except ValueError:
                changed_files.append(result.source.name)

    log_text = "\n".join(changed_files)
    if log_text:
        log_text += "\n"
    log_path.write_text(log_text, encoding="utf-8")


def print_results(results: list[ConversionResult]) -> None:
    if not results:
        print("No PDF files found.")
        return

    for result in results:
        if result.status == "converted":
            print(
                f"[OK] {result.source.name} overwritten "
                f"({result.converted_pages}/{result.total_pages} landscape pages split)"
            )
        elif result.status == "skipped_portrait":
            print(f"[SKIP] {result.source.name} is already portrait.")
        else:
            print(f"[ERROR] {result.source.name}: {result.status}")


def choose_folder_with_gui() -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    selected = filedialog.askdirectory(title="PDF files folder")
    root.destroy()
    return Path(selected) if selected else None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split two-up landscape PDF pages into portrait pages."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        type=Path,
        help="Folder containing PDF files. If omitted, a folder picker opens.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Include PDF files inside subfolders.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    folder = args.folder or choose_folder_with_gui()
    if folder is None:
        print("Canceled.")
        return 1

    try:
        resolved_folder = folder.resolve()
        results = convert_folder(
            resolved_folder,
            recursive=args.recursive,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    write_modified_files_log(results, resolved_folder)
    print_results(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
