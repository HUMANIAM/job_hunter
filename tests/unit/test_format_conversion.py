from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

import pytest

from infra.format_conversion import (
    convert_to_text,
    docx_to_text,
    pdf_to_text,
    write_markdown_sidecar,
)

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "pdf_test"
CV_PDF_PATH = FIXTURE_DIRECTORY / "Ibrahim_Saad_CV.pdf"
CV_MARKDOWN_PATH = FIXTURE_DIRECTORY / "Ibrahim_Saad_CV.md"


def test_convert_to_text_reads_docx_paragraphs(tmp_path: Path) -> None:
    docx_path = tmp_path / "profile.docx"
    _write_minimal_docx(docx_path, ["Embedded systems", "Python and C++"])

    extracted_text = convert_to_text(docx_path)

    assert extracted_text == "Embedded systems\n\nPython and C++"


def test_convert_to_text_reads_real_pdf_fixture() -> None:
    extracted_text = convert_to_text(CV_PDF_PATH)

    assert "Ibrahim Saad" in extracted_text
    assert "Embedded Software Engineer" in extracted_text
    assert "ASML, Veldhoven, Netherlands" in extracted_text


def test_real_pdf_markdown_sidecar_matches_current_extraction() -> None:
    expected_markdown = f"{convert_to_text(CV_PDF_PATH)}\n"

    assert CV_MARKDOWN_PATH.read_text(encoding="utf-8") == expected_markdown


def test_write_markdown_sidecar_writes_md_next_to_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / CV_PDF_PATH.name
    pdf_path.write_bytes(CV_PDF_PATH.read_bytes())

    markdown_path = write_markdown_sidecar(pdf_path)

    assert markdown_path == tmp_path / "Ibrahim_Saad_CV.md"
    assert markdown_path.read_text(encoding="utf-8") == f"{convert_to_text(pdf_path)}\n"


def test_convert_to_text_rejects_unsupported_suffix(tmp_path: Path) -> None:
    csv_path = tmp_path / "profile.csv"
    csv_path.write_text("name,skill\nSioux,Python\n", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        convert_to_text(csv_path)

    assert str(error.value) == (
        "unsupported input format '.csv'; supported formats: .docx, .md, .pdf, .txt"
    )


def test_docx_to_text_rejects_missing_document_xml(tmp_path: Path) -> None:
    docx_path = tmp_path / "broken.docx"
    with ZipFile(docx_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")

    with pytest.raises(ValueError) as error:
        docx_to_text(docx_path)

    assert "missing word/document.xml" in str(error.value)


def test_pdf_to_text_raises_when_tooling_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "profile.pdf"
    pdf_path.write_bytes(CV_PDF_PATH.read_bytes())

    monkeypatch.setattr("infra.format_conversion.PdfReader", None)
    monkeypatch.setattr("infra.format_conversion.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError) as error:
        pdf_to_text(pdf_path)

    assert str(error.value) == (
        "PDF extraction requires the optional 'pypdf' dependency or the 'pdftotext' command"
    )


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document "
        "xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )

    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("_rels/.rels", "<Relationships />")
        archive.writestr("word/document.xml", document_xml)
