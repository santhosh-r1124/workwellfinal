from html.parser import HTMLParser
from pathlib import Path


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return " ".join(c.strip() for c in self._chunks if c.strip())


def parse_file(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".md", ".txt"):
        return path.read_text(encoding="utf-8")

    if suffix == ".html":
        extractor = _HTMLTextExtractor()
        extractor.feed(path.read_text(encoding="utf-8"))
        return extractor.text()

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        import docx

        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)

    raise ValueError(f"Unsupported document type: {suffix}")
