"""
Text Extraction

Extracts text content from various file formats.
Supports: PDF, DOCX, TXT, CSV, Excel, Markdown.
"""

import csv
import io
from pathlib import Path


def extract_text(file_path: str, extension: str) -> dict:
    """
    Extract text from a file based on its extension.

    Returns dict with:
        - text: extracted text content
        - word_count: number of words
        - page_count: number of pages (if applicable)
        - metadata: additional file-specific metadata
    """
    ext = extension.lower()
    extractors = {
        ".pdf": _extract_pdf,
        ".docx": _extract_docx,
        ".doc": _extract_docx,
        ".txt": _extract_text_file,
        ".md": _extract_text_file,
        ".csv": _extract_csv,
        ".xlsx": _extract_excel,
        ".xls": _extract_excel,
    }

    extractor = extractors.get(ext)
    if not extractor:
        return {
            "text": "",
            "word_count": 0,
            "page_count": 0,
            "metadata": {"note": f"No text extractor for {ext}"}
        }

    try:
        return extractor(file_path)
    except Exception as e:
        return {
            "text": "",
            "word_count": 0,
            "page_count": 0,
            "metadata": {"error": str(e)}
        }


def _extract_pdf(file_path: str) -> dict:
    """Extract text from PDF using pdfplumber."""
    import pdfplumber

    text_parts = []
    page_count = 0

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n\n".join(text_parts)
    return {
        "text": full_text,
        "word_count": len(full_text.split()),
        "page_count": page_count,
        "metadata": {"pages": page_count}
    }


def _extract_docx(file_path: str) -> dict:
    """Extract text from Word documents."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)

    # Also extract tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                full_text += "\n" + row_text

    return {
        "text": full_text,
        "word_count": len(full_text.split()),
        "page_count": len(doc.sections),
        "metadata": {
            "paragraphs": len(doc.paragraphs),
            "tables": len(doc.tables),
        }
    }


def _extract_text_file(file_path: str) -> dict:
    """Extract text from plain text or markdown files."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    lines = text.split("\n")
    return {
        "text": text,
        "word_count": len(text.split()),
        "page_count": 1,
        "metadata": {"lines": len(lines)}
    }


def _extract_csv(file_path: str) -> dict:
    """Extract data summary from CSV files."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return {"text": "", "word_count": 0, "page_count": 1, "metadata": {}}

    headers = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []

    # Build a text summary
    text_parts = [f"CSV with {len(headers)} columns and {len(data_rows)} rows"]
    text_parts.append(f"Columns: {', '.join(headers)}")

    # Include first few rows as sample
    for row in data_rows[:10]:
        text_parts.append(" | ".join(row))

    full_text = "\n".join(text_parts)
    return {
        "text": full_text,
        "word_count": len(full_text.split()),
        "page_count": 1,
        "metadata": {
            "columns": headers,
            "row_count": len(data_rows),
            "column_count": len(headers),
        }
    }


def _extract_excel(file_path: str) -> dict:
    """Extract data summary from Excel files."""
    from openpyxl import load_workbook

    wb = load_workbook(file_path, read_only=True, data_only=True)
    text_parts = []
    total_rows = 0
    sheet_info = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        total_rows += len(rows)

        headers = [str(h) if h else "" for h in rows[0]] if rows else []
        data_count = len(rows) - 1 if len(rows) > 1 else 0

        sheet_info.append({
            "name": sheet_name,
            "columns": headers,
            "row_count": data_count,
        })

        text_parts.append(f"Sheet: {sheet_name} ({data_count} rows, {len(headers)} columns)")
        text_parts.append(f"Columns: {', '.join(headers)}")

        # Include sample rows
        for row in rows[1:6]:
            row_text = " | ".join(str(v) if v else "" for v in row)
            text_parts.append(row_text)

    wb.close()
    full_text = "\n".join(text_parts)
    return {
        "text": full_text,
        "word_count": len(full_text.split()),
        "page_count": len(wb.sheetnames),
        "metadata": {
            "sheets": sheet_info,
            "total_rows": total_rows,
        }
    }
