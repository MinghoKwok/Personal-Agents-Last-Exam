"""Text extraction and amount parsing shared by the Task #129 verifier.

Copied from the Task #102 verifier (same rules, same tests): amounts are numbers with a "$",
thousands separators or two decimals; PDFs with a text layer are read line by line, with
text on one baseline joined by " | ". Standard library only.
"""
import re
import zlib

# An amount is a number with a "$", thousands separators or two decimals: "$100,000", "100,000",
# "375.00". A bare integer ("2" in "box 2", "2025") is not an amount, except as a whole table cell.
MONEY = re.compile(r"(?<![\w.\-])(?<!\d,)(\$\s?)?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{2}))?(?![\w\-]|[.,]\d)")
CELL_AMOUNT = re.compile(r"\$?\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{2}))?")


def cents_in(text):
    return [int(a.replace(",", "")) * 100 + int(c or 0) for d, a, c in MONEY.findall(text) if d or c or "," in a]


def cell_cents(cell):
    m = CELL_AMOUNT.fullmatch(cell.strip())
    return [int(m.group(1).replace(",", "")) * 100 + int(m.group(2) or 0)] if m else cents_in(cell)


# Literal strings may contain balanced, unescaped parentheses (two levels handled).
PDF_TOKEN = re.compile(rb"\((?:\\.|[^\\()]|\((?:\\.|[^\\()]|\((?:\\.|[^\\()])*\))*\))*\)|<[0-9A-Fa-f\s]*>|\[|\]|/[^\s/\[\]()<>{}%]+|[-+]?(?:\d+\.?\d*|\.\d+)|[A-Za-z'\"*]+\d?|%[^\r\n]*")
PDF_NUM = re.compile(rb"[-+]?(?:\d+\.?\d*|\.\d+)")
PDF_ESC = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}


def pdf_string(tok):
    if tok[:1] == b"<":
        hexs = re.sub(rb"\s", b"", tok[1:-1])
        return bytes.fromhex((hexs + b"0" * (len(hexs) % 2)).decode()).decode("latin-1")
    raw = re.sub(rb"\\([0-7]{1,3}|.)", lambda m: bytes([int(m.group(1), 8) & 255]) if m.group(1)[:1].isdigit() else PDF_ESC.get(m.group(1), m.group(1)), tok[1:-1], flags=re.S)
    return raw.decode("latin-1")


def pdf_streams(data):
    """Content streams, inflated when Flate-compressed (what most PDF libraries write)."""
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        chunk = m.group(1)
        try:
            chunk = zlib.decompressobj().decompress(chunk) or chunk
        except zlib.error:
            pass
        if b"BT" in chunk:
            yield chunk


def pdf_text(data):
    """Text layer as lines: text drawn on the same baseline is joined left to right, with " | "
    between separately placed pieces (so a label and its amount, or table cells, stay on one line).
    Handles Tj/TJ/'/" with Td/TD/Tm/T* positioning; enough for text written by common PDF libraries.
    Returns None when there is no text layer (for example a scan)."""
    pieces = []  # (y, x, text)
    for chunk in pdf_streams(data):
        x = y = lead = 0.0
        stack, arr, moved = [], None, True
        for tok in PDF_TOKEN.findall(chunk):
            if tok[:1] == b"%":
                continue
            if tok == b"[":
                arr = []
                continue
            if tok == b"]":
                stack.append(arr or [])
                arr = None
                continue
            if arr is not None:
                arr.append(tok)
                continue
            if tok[:1] in (b"(", b"<", b"/") or PDF_NUM.fullmatch(tok):
                stack.append(tok)
                continue
            nums = [float(t) for t in stack if isinstance(t, bytes) and PDF_NUM.fullmatch(t)]
            text = None
            if tok == b"BT":
                x = y = 0.0
                moved = True
            elif tok in (b"Td", b"TD") and len(nums) >= 2:
                x, y = x + nums[-2], y + nums[-1]
                lead = -nums[-1] if tok == b"TD" else lead
                moved = True
            elif tok == b"Tm" and len(nums) >= 6:
                x, y = nums[-2], nums[-1]
                moved = True
            elif tok == b"TL" and nums:
                lead = nums[-1]
            elif tok == b"T*":
                y -= lead
                moved = True
            elif tok in (b"Tj", b"'", b'"') and stack and isinstance(stack[-1], bytes) and stack[-1][:1] in (b"(", b"<"):
                if tok != b"Tj":
                    y -= lead
                    moved = True
                text = pdf_string(stack[-1])
            elif tok == b"TJ" and stack and isinstance(stack[-1], list):
                text = "".join(pdf_string(t) if t[:1] in (b"(", b"<") else (" " if PDF_NUM.fullmatch(t) and float(t) < -200 else "") for t in stack[-1])
            if text is not None:
                if not moved and pieces:
                    pieces[-1][2] += text
                else:
                    pieces.append([y, x, text])
                moved = False
            stack = []
    if not pieces:
        return None
    rows = []
    for y, x, t in sorted(pieces, key=lambda p: (-p[0], p[1])):
        if rows and abs(rows[-1][0] - y) <= 2:
            rows[-1][1].append((x, t))
        else:
            rows.append([y, [(x, t)]])
    return "\n".join(" | ".join(t.strip() for _, t in sorted(cells) if t.strip()) for _, cells in rows)


def to_text(name, mime, data):
    if mime == "application/pdf" or name.lower().endswith(".pdf") or data[:5] == b"%PDF-":
        return pdf_text(data)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
