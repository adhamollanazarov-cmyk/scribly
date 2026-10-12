"""Draws Scribbly's face as PNG icons (no image library needed). Run once; outputs are committed."""

import math
import sys
import zlib
from pathlib import Path

BODY = (127, 119, 221)
INK = (38, 33, 92)
TIP = (239, 159, 39)
WHITE = (255, 255, 255)


def shade(u: float, v: float) -> tuple[tuple[int, int, int], float] | None:
    """Colour at unit coordinates (0..1), or None for transparent."""
    def inside(cx: float, cy: float, r: float) -> bool:
        return (u - cx) ** 2 + (v - cy) ** 2 <= r * r

    def ring(cx: float, cy: float, r: float, w: float) -> bool:
        d = math.hypot(u - cx, v - cy)
        return abs(d - r) <= w / 2

    if inside(0.70, 0.12, 0.07):
        return TIP, 1
    # antenna stalk
    if abs(u - 0.6) < 0.025 and 0.12 < v < 0.25 or abs(v - 0.12) < 0.025 and 0.6 < u < 0.68:
        return BODY, 1
    if not inside(0.5, 0.58, 0.40):
        return None
    for ex in (0.36, 0.64):
        if ring(ex, 0.52, 0.12, 0.035):
            return INK, 1
        if inside(ex + 0.015, 0.54, 0.04):
            return INK, 1
        if inside(ex, 0.52, 0.095):
            return WHITE, 1
    # smile
    d = math.hypot(u - 0.5, v - 0.62)
    if abs(d - 0.17) < 0.022 and v > 0.70:
        return INK, 1
    return BODY, 1


def render(size: int, ss: int = 4) -> bytes:
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            acc = [0.0, 0.0, 0.0, 0.0]
            for sy in range(ss):
                for sx in range(ss):
                    hit = shade((x + (sx + 0.5) / ss) / size, (y + (sy + 0.5) / ss) / size)
                    if hit:
                        (r, g, b), a = hit
                        acc[0] += r * a
                        acc[1] += g * a
                        acc[2] += b * a
                        acc[3] += a
            n = ss * ss
            alpha = acc[3] / n
            if acc[3]:
                row += bytes(round(c / acc[3]) for c in acc[:3]) + bytes([round(alpha * 255)])
            else:
                row += b"\0\0\0\0"
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return len(data).to_bytes(4, "big") + kind + data + zlib.crc32(kind + data).to_bytes(4, "big")

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
