from __future__ import annotations

import re
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "LeetCoach-new-device-handoff.md"
OUTPUT = ROOT / "docs" / "LeetCoach-new-device-handoff.pdf"

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_X = 54
MARGIN_TOP = 54
MARGIN_BOTTOM = 54
BODY_SIZE = 10
H1_SIZE = 18
H2_SIZE = 14
LINE_HEIGHT = 14


def clean_text(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    return text.encode("latin-1", "replace").decode("latin-1")


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_line(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    return textwrap.wrap(text, width=width, break_long_words=False) or [text]


def markdown_to_lines(markdown: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    in_code = False

    for raw_line in markdown.splitlines():
        line = clean_text(raw_line.rstrip())

        if line.startswith("```"):
            in_code = not in_code
            lines.append(("space", ""))
            continue

        if in_code:
            for wrapped in wrap_line(line, 78):
                lines.append(("code", wrapped))
            continue

        if not line:
            lines.append(("space", ""))
            continue

        if line.startswith("# "):
            lines.append(("h1", line[2:].strip()))
            lines.append(("space", ""))
            continue

        if line.startswith("## "):
            lines.append(("h2", line[3:].strip()))
            continue

        if line.startswith("### "):
            lines.append(("h2", line[4:].strip()))
            continue

        if line.startswith("> "):
            for wrapped in wrap_line(line[2:].strip(), 78):
                lines.append(("quote", wrapped))
            continue

        bullet_match = re.match(r"^(\s*)- (.+)$", line)
        if bullet_match:
            indent = "  " * (len(bullet_match.group(1)) // 2)
            for index, wrapped in enumerate(wrap_line(bullet_match.group(2), 84)):
                prefix = f"{indent}- " if index == 0 else f"{indent}  "
                lines.append(("body", f"{prefix}{wrapped}"))
            continue

        numbered_match = re.match(r"^(\d+)\. (.+)$", line)
        if numbered_match:
            number = numbered_match.group(1)
            for index, wrapped in enumerate(wrap_line(numbered_match.group(2), 82)):
                prefix = f"{number}. " if index == 0 else "   "
                lines.append(("body", f"{prefix}{wrapped}"))
            continue

        for wrapped in wrap_line(line, 88):
            lines.append(("body", wrapped))

    return lines


def paginate(lines: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    pages: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    y = PAGE_HEIGHT - MARGIN_TOP

    for style, text in lines:
        if style == "h1":
            needed = 26
        elif style == "h2":
            needed = 22
        elif style == "space":
            needed = 8
        else:
            needed = LINE_HEIGHT

        if y - needed < MARGIN_BOTTOM and current:
            pages.append(current)
            current = []
            y = PAGE_HEIGHT - MARGIN_TOP

        current.append((style, text))
        y -= needed

    if current:
        pages.append(current)

    return pages


def build_page_stream(page: list[tuple[str, str]], page_number: int, page_count: int) -> str:
    commands = ["BT"]
    y = PAGE_HEIGHT - MARGIN_TOP

    for style, text in page:
        if style == "space":
            y -= 8
            continue

        if style == "h1":
            font = "F2"
            size = H1_SIZE
            y -= 4
        elif style == "h2":
            font = "F2"
            size = H2_SIZE
            y -= 10
        elif style == "code":
            font = "F3"
            size = 8
        else:
            font = "F1"
            size = BODY_SIZE

        commands.append(f"/{font} {size} Tf")
        commands.append(f"1 0 0 1 {MARGIN_X} {y} Tm")
        commands.append(f"({escape_pdf_text(text)}) Tj")

        if style == "h1":
            y -= 22
        elif style == "h2":
            y -= 18
        else:
            y -= LINE_HEIGHT

    commands.append("/F1 8 Tf")
    commands.append(f"1 0 0 1 {MARGIN_X} 30 Tm")
    commands.append(
        f"(LeetCoach handoff - page {page_number} of {page_count}) Tj"
    )
    commands.append("ET")
    return "\n".join(commands)


def write_pdf(pages: list[list[tuple[str, str]]]) -> None:
    objects: list[str] = []

    def add_object(content: str) -> int:
        objects.append(content)
        return len(objects)

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object("")
    font_body_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font_bold_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    font_mono_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    page_ids: list[int] = []
    for index, page in enumerate(pages, start=1):
        stream = build_page_stream(page, index, len(pages))
        stream_bytes = stream.encode("latin-1", "replace")
        content_id = add_object(
            f"<< /Length {len(stream_bytes)} >>\nstream\n{stream}\nendstream"
        )
        page_id = add_object(
            "<< /Type /Page "
            f"/Parent {pages_id} 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Contents {content_id} 0 R "
            "/Resources << /Font << "
            f"/F1 {font_body_id} 0 R "
            f"/F2 {font_bold_id} 0 R "
            f"/F3 {font_mono_id} 0 R "
            ">> >> >>"
        )
        page_ids.append(page_id)

    objects[pages_id - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    )

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        encoded = content.encode("latin-1", "replace")
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(encoded)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("latin-1")
    )

    OUTPUT.write_bytes(pdf)


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    lines = markdown_to_lines(markdown)
    pages = paginate(lines)
    write_pdf(pages)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
