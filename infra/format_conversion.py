from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - exercised via pdftotext fallback in tests
    PdfReader = None

_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_WORD_XML_NAMESPACES = {"w": _WORD_NAMESPACE}
_WORD_DOCUMENT_PATH = "word/document.xml"
_PLAIN_TEXT_SUFFIXES = {".md", ".txt"}


def convert_to_text(path: Path | str) -> str:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix in _PLAIN_TEXT_SUFFIXES:
        return _normalize_text_output(file_path.read_text(encoding="utf-8"))
    if suffix == ".pdf":
        return pdf_to_text(file_path)
    if suffix == ".docx":
        return docx_to_text(file_path)

    supported_suffixes = ", ".join(sorted(_PLAIN_TEXT_SUFFIXES | {".docx", ".pdf"}))
    raise ValueError(
        f"unsupported input format '{suffix or '<no extension>'}'; "
        f"supported formats: {supported_suffixes}"
    )


def write_markdown_sidecar(
    source_path: Path | str,
    output_path: Path | str | None = None,
) -> Path:
    source = Path(source_path)
    destination = Path(output_path) if output_path is not None else source.with_suffix(".md")
    if destination == source:
        raise ValueError("markdown sidecar path must differ from the source path")

    destination.write_text(f"{convert_to_text(source)}\n", encoding="utf-8")
    return destination


def pdf_to_text(path: Path | str) -> str:
    file_path = Path(path)
    if PdfReader is not None:
        reader = PdfReader(str(file_path))
        return _normalize_text_output(
            "\n".join(page.extract_text() or "" for page in reader.pages)
        )

    pdftotext_binary = shutil.which("pdftotext")
    if pdftotext_binary is None:
        raise RuntimeError(
            "PDF extraction requires the optional 'pypdf' dependency or the "
            "'pdftotext' command"
        )

    completed_process = subprocess.run(
        [pdftotext_binary, "-enc", "UTF-8", str(file_path), "-"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed_process.returncode != 0:
        error_message = completed_process.stderr.strip() or "unknown pdftotext failure"
        raise RuntimeError(f"failed to extract PDF text from {file_path}: {error_message}")

    return _normalize_text_output(completed_process.stdout)


def docx_to_text(path: Path | str) -> str:
    file_path = Path(path)
    with ZipFile(file_path) as archive:
        try:
            document_xml = archive.read(_WORD_DOCUMENT_PATH)
        except KeyError as error:
            raise ValueError(
                f"{file_path} is not a valid .docx file: missing {_WORD_DOCUMENT_PATH}"
            ) from error

    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", _WORD_XML_NAMESPACES):
        paragraph_text = _extract_docx_paragraph_text(paragraph).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)

    return _normalize_text_output("\n\n".join(paragraphs))


def _extract_docx_paragraph_text(paragraph: ET.Element) -> str:
    pieces: list[str] = []
    for node in paragraph.iter():
        if node.tag == _word_tag("t"):
            pieces.append(node.text or "")
        elif node.tag == _word_tag("tab"):
            pieces.append("\t")
        elif node.tag in {_word_tag("br"), _word_tag("cr")}:
            pieces.append("\n")

    return "".join(pieces)


def _word_tag(name: str) -> str:
    return f"{{{_WORD_NAMESPACE}}}{name}"


def _normalize_text_output(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n").strip()
