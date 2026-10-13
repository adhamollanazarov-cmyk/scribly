"""Draws Scribbly's head (round body, pencil tip, face) as PNG icons, no image library needed.

Same shapes and colors as web/src/mascot (docs/brand/scribbly-sheet.png). Run once; the
outputs are committed: python desktop/scripts/make_icons.py desktop/resources
"""

import math
import sys
import zlib
from pathlib import Path

RGB = tuple[int, int, int]

# web/src/mascot/scribbly.css
BODY: RGB = (253, 249, 238)
SHADE: RGB = (239, 230, 207)
INK: RGB = (23, 50, 61)
WOOD: RGB = (246, 196, 94)
GRAPHITE: RGB = (52, 68, 77)
CHEEK: RGB = (246, 169, 78)
WHITE: RGB = (255, 255, 255)

# Head geometry in icon units (0..1), from Scribbly.tsx: body radius R, tip 1.4 R above center.
CX, CY, R = 0.5, 0.6, 0.36
TIP = (CX + 0.02 * R, CY - 1.4 * R)
BASE_L = (CX - 0.55 * R, CY - 0.83 * R)
BASE_R = (CX + 0.55 * R, CY - 0.83 * R)


def _edge_distance(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _in_cone(u: float, v: float) -> bool:
    def side(a: tuple[float, float], b: tuple[float, float]) -> float:
        return (b[0] - a[0]) * (v - a[1]) - (b[1] - a[1]) * (u - a[0])

    s = [side(TIP, BASE_R), side(BASE_R, BASE_L), side(BASE_L, TIP)]
    return all(x >= 0 for x in s) or all(x <= 0 for x in s)


def _cone_distance(u: float, v: float) -> float:
    """Signed distance to the cone's two slanted sides (negative inside)."""
    d = min(_edge_distance((u, v), TIP, BASE_L), _edge_distance((u, v), TIP, BASE_R))
    return -d if _in_cone(u, v) else d


def _in_head(u: float, v: float, grow: float) -> bool:
    """Inside the body circle or the pencil cone, grown (or shrunk, grow < 0) by `grow`."""
    if math.hypot(u - CX, v - CY) <= R + grow:
        return True
    if v > BASE_L[1]:
        return False  # the cone's base is inside the circle
    return _cone_distance(u, v) <= grow


def _in_ellipse(u: float, v: float, cx: float, cy: float, rx: float, ry: float) -> bool:
    return ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2 <= 1


def _wood_line(u: float) -> float:
    """Scalloped bottom edge of the sharpened wood (5 bumps across the cone base)."""
    left, right = CX - 0.62 * R, CX + 0.62 * R
    top, dip = CY - 0.76 * R, CY - 0.62 * R
    if not left <= u <= right:
        return top
    t = (u - left) / (right - left) * 5
    return top + (dip - top) * math.sin(math.pi * (t % 1))


def _face(u: float, v: float, line: float, small: bool) -> RGB | None:
    for side in (-1, 1):
        ex, ey = CX + side * 0.46 * R, CY + 0.1 * R
        if _in_ellipse(u, v, ex, ey, 0.19 * R, 0.24 * R):
            # Two highlights: a large one up right, a small one down left (too small for a tray).
            if math.hypot(u - ex - 0.055 * R, v - ey + 0.09 * R) <= 0.075 * R:
                return WHITE
            if not small and math.hypot(u - ex + 0.065 * R, v - ey - 0.1 * R) <= 0.035 * R:
                return WHITE
            return INK
        if not small and _in_ellipse(u, v, CX + side * 0.6 * R, CY + 0.38 * R, 0.15 * R, 0.09 * R):
            return CHEEK
    d = math.hypot(u - CX, v - CY - 0.2 * R)
    if v > CY + 0.27 * R and abs(d - 0.17 * R) <= line / 2:
        return INK
    return None


def shade(u: float, v: float, line: float, small: bool = False) -> RGB | None:
    """Colour at icon coordinates (0..1), or None for transparent. `line` = outline width;
    `small` drops the details a tray icon cannot show (cheeks, small highlight, shading)."""
    if not _in_head(u, v, line / 2):
        return None
    if not _in_head(u, v, -line / 2):
        return INK
    if v < TIP[1] + 0.42 * (BASE_L[1] - TIP[1]):
        return GRAPHITE
    if v < _wood_line(u):
        return WOOD
    face = _face(u, v, max(line * 0.8, 0.03), small)
    if face:
        return face
    # Soft shading on the lower right, like the sheet.
    if not small and math.hypot(u - CX + 0.1 * R, v - CY + 0.14 * R) > R:
        return SHADE
    return BODY


def render(size: int, ss: int = 4) -> bytes:
    # The art's outline is 0.076 R; tray icons get at least ~1.3 px so the head stays readable.
    line = max(0.076 * R, 1.3 / size)
    small = size < 24
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            acc = [0.0, 0.0, 0.0]
            hits = 0
            for sy in range(ss):
                for sx in range(ss):
                    u, v = (x + (sx + 0.5) / ss) / size, (y + (sy + 0.5) / ss) / size
                    hit = shade(u, v, line, small)
                    if hit:
                        hits += 1
                        for i in range(3):
                            acc[i] += hit[i]
            if hits:
                alpha = round(hits / (ss * ss) * 255)
                row += bytes(round(c / hits) for c in acc) + bytes([alpha])
            else:
                row += b"\0\0\0\0"
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data).to_bytes(4, "big")
        return len(data).to_bytes(4, "big") + kind + data + crc

    header = size.to_bytes(4, "big") * 2 + bytes([8, 6, 0, 0, 0])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "icon.png").write_bytes(render(256))
    (out / "tray.png").write_bytes(render(16))
    (out / "tray@2x.png").write_bytes(render(32))
    print("ok")
