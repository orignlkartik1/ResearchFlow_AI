from dataclasses import dataclass

import pymupdf

MAX_PDF_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_PDF_TEXT_CHARACTERS = 120_000
MIN_EXTRACTABLE_ALPHANUMERIC_CHARACTERS = 20
PDF_HEADER_SEARCH_BYTES = 1024


class InvalidPDFError(ValueError):
    """The uploaded bytes are not a readable, supported PDF."""


class NoExtractableTextError(ValueError):
    """The PDF does not contain enough extractable text for analysis."""


class PDFTooLargeError(ValueError):
    """The PDF exceeds a supported page or extracted-text limit."""


class PDFExtractionError(RuntimeError):
    """Text extraction failed unexpectedly after PDF validation."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    filename: str
    page_count: int
    pages: tuple[ExtractedPage, ...]

    def research_text(self) -> str:
        return "\n\n".join(
            f"[Page {page.page_number}]\n{page.text}" for page in self.pages
        )


def extract_pdf(file_bytes: bytes, filename: str) -> ExtractedDocument:
    if not file_bytes:
        raise InvalidPDFError("The uploaded file is empty.")
    if len(file_bytes) > MAX_PDF_UPLOAD_BYTES:
        raise PDFTooLargeError("The uploaded PDF exceeds the 15 MiB upload limit.")
    if b"%PDF-" not in file_bytes[:PDF_HEADER_SEARCH_BYTES]:
        raise InvalidPDFError("The uploaded file does not have a valid PDF header.")

    try:
        document = pymupdf.open(stream=file_bytes, filetype="pdf")
    except (pymupdf.FileDataError, ValueError) as exc:
        raise InvalidPDFError("The uploaded PDF is malformed or cannot be opened.") from exc

    with document:
        if document.needs_pass:
            raise InvalidPDFError("Password-protected PDFs are not supported.")
        page_count = document.page_count
        if page_count > MAX_PDF_PAGES:
            raise PDFTooLargeError("The PDF exceeds the 100-page analysis limit.")

        pages: list[ExtractedPage] = []
        text_character_count = 0
        alphanumeric_character_count = 0

        try:
            for page_number, page in enumerate(document, start=1):
                text = "\n".join(
                    line.strip()
                    for line in page.get_text("text").replace("\x00", "").splitlines()
                ).strip()
                text_character_count += len(text)
                if text_character_count > MAX_PDF_TEXT_CHARACTERS:
                    raise PDFTooLargeError(
                        "The extracted PDF text exceeds the 120,000-character analysis limit."
                    )
                alphanumeric_character_count += sum(char.isalnum() for char in text)
                pages.append(ExtractedPage(page_number=page_number, text=text))
        except PDFTooLargeError:
            raise
        except Exception as exc:
            raise PDFExtractionError("Text could not be extracted from the PDF.") from exc

    if alphanumeric_character_count < MIN_EXTRACTABLE_ALPHANUMERIC_CHARACTERS:
        raise NoExtractableTextError(
            "No extractable text was found in this PDF. Scanned/image-only PDFs are not supported yet."
        )

    return ExtractedDocument(
        filename=filename,
        page_count=page_count,
        pages=tuple(pages),
    )
