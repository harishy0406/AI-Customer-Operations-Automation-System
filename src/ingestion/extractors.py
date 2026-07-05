from typing import BinaryIO


def extract_text(file_stream: BinaryIO, source_type: str) -> str:
    source_type = source_type.lower()
    if source_type == "pdf":
        return _extract_pdf(file_stream)
    elif source_type == "html":
        return _extract_html(file_stream)
    elif source_type == "csv":
        return _extract_csv(file_stream)
    else:
        return file_stream.read().decode("utf-8", errors="replace")


def _extract_pdf(file_stream: BinaryIO) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except ImportError:
        return file_stream.read().decode("utf-8", errors="replace")


def _extract_html(file_stream: BinaryIO) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(file_stream.read(), "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        return file_stream.read().decode("utf-8", errors="replace")


def _extract_csv(file_stream: BinaryIO) -> str:
    import csv
    content = file_stream.read().decode("utf-8", errors="replace")
    lines = []
    reader = csv.reader(content.splitlines())
    for row in reader:
        lines.append(" | ".join(row))
    return "\n".join(lines)
