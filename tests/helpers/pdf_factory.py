from collections.abc import Sequence


def build_text_pdf(
    pages: Sequence[Sequence[str]],
) -> bytes:
    """Build a minimal PDF containing simple Helvetica text."""

    if not pages:
        raise ValueError("At least one page is required.")

    objects: dict[int, bytes] = {}

    page_ids: list[int] = []
    content_ids: list[int] = []

    next_object_id = 3

    for _ in pages:
        page_ids.append(next_object_id)
        content_ids.append(next_object_id + 1)
        next_object_id += 2

    font_id = next_object_id

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)

    objects[2] = (f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>").encode(
        "ascii"
    )

    for page_id, content_id, lines in zip(
        page_ids,
        content_ids,
        pages,
        strict=True,
    ):
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] "
            f"/Resources << /Font "
            f"<< /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")

        stream = _build_text_stream(lines)

        objects[content_id] = (
            (f"<< /Length {len(stream)} >>\nstream\n").encode("ascii")
            + stream
            + b"\nendstream"
        )

    objects[font_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    return _serialize_pdf(objects)


def _build_text_stream(
    lines: Sequence[str],
) -> bytes:
    """Create a small PDF text content stream."""

    commands = [
        "BT",
        "/F1 12 Tf",
        "72 720 Td",
    ]

    for index, line in enumerate(lines):
        if index:
            commands.append("0 -18 Td")

        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        commands.append(f"({escaped}) Tj")

    commands.append("ET")

    return "\n".join(commands).encode("latin-1")


def _serialize_pdf(
    objects: dict[int, bytes],
) -> bytes:
    """Serialize contiguous PDF objects with an xref table."""

    pdf = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

    offsets: dict[int, int] = {}

    for object_id in sorted(objects):
        offsets[object_id] = len(pdf)

        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_id])
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    object_count = max(objects) + 1

    pdf.extend(f"xref\n0 {object_count}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")

    for object_id in range(1, object_count):
        pdf.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            f"trailer\n"
            f"<< /Size {object_count} "
            f"/Root 1 0 R >>\n"
            f"startxref\n"
            f"{xref_offset}\n"
            f"%%EOF\n"
        ).encode("ascii")
    )

    return bytes(pdf)
