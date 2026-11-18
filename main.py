#!/usr/bin/env python3
"""news-image-20261118 — make.fun bounty entry.

Draws a one-image summary of the world news of Wednesday 18 November 2026
as a single 1024x1024 PNG, using only the Python standard library.

Run:
    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py

The program writes entry.png into MAKEFUN_OUTPUT_DIR when set, otherwise
into /output. Output is fully deterministic: no timestamps, no randomness,
fixed zlib level, no tIME chunk — two runs produce byte-identical files.
"""

import os
import struct
import zlib

# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

W, H = 1024, 1024

# Palette
BG = (13, 21, 36)          # deep navy page background
HEADER_BG = (27, 42, 68)   # header band
CELL_BG = (22, 35, 58)     # story card
CELL_BORDER = (42, 59, 87)  # story card border
STRIP_BG = (16, 28, 48)    # bottom briefs strip
TEXT = (245, 247, 250)     # near-white
BODY = (199, 210, 224)     # light grey-blue body text
MUTED = (150, 163, 184)    # dimmer grey-blue
GOLD = (232, 185, 60)      # accent / date rule


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set_pixel(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = rgb

    def fill_rect(self, x, y, w, h, rgb):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(rgb) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def hline(self, x, y, length, rgb, thick=1):
        self.fill_rect(x, y, length, thick, rgb)

    def vline(self, x, y, length, rgb, thick=1):
        self.fill_rect(x, y, thick, length, rgb)

    def line(self, x0, y0, x1, y1, rgb):
        """Bresenham line, 1 px."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set_pixel(x0, y0, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, rgb):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.hline(cx - dx, cy + dy, 2 * dx + 1, rgb)

    def circle(self, cx, cy, r, rgb, thick=2):
        """Outline circle (midpoint), drawn at radius r and r-1 for thickness."""
        for rr in range(r - thick + 1, r + 1):
            x, y, d = 0, rr, 1 - rr
            while x <= y:
                for px, py in ((cx + x, cy + y), (cx + y, cy + x),
                               (cx - x, cy + y), (cx - y, cy + x),
                               (cx + x, cy - y), (cx + y, cy - x),
                               (cx - x, cy - y), (cx - y, cy - x)):
                    self.set_pixel(px, py, rgb)
                if d < 0:
                    d += 2 * x + 3
                else:
                    d += 2 * (x - y) + 5
                    y -= 1
                x += 1


# ---------------------------------------------------------------------------
# 5x7 bitmap font (columns; bit 0 = top row). Classic public-domain 5x7 set.
# ---------------------------------------------------------------------------

FONT = {
    ' ': (0x00, 0x00, 0x00, 0x00, 0x00),
    '!': (0x00, 0x00, 0x5F, 0x00, 0x00),
    '"': (0x00, 0x07, 0x00, 0x07, 0x00),
    '#': (0x14, 0x7F, 0x14, 0x7F, 0x14),
    '$': (0x24, 0x2A, 0x7F, 0x2A, 0x12),
    '%': (0x23, 0x13, 0x08, 0x64, 0x62),
    '&': (0x36, 0x49, 0x55, 0x22, 0x50),
    "'": (0x00, 0x05, 0x03, 0x00, 0x00),
    '(': (0x00, 0x1C, 0x22, 0x41, 0x00),
    ')': (0x00, 0x41, 0x22, 0x1C, 0x00),
    '*': (0x14, 0x08, 0x3E, 0x08, 0x14),
    '+': (0x08, 0x08, 0x3E, 0x08, 0x08),
    ',': (0x00, 0x50, 0x30, 0x00, 0x00),
    '-': (0x08, 0x08, 0x08, 0x08, 0x08),
    '.': (0x00, 0x60, 0x60, 0x00, 0x00),
    '/': (0x20, 0x10, 0x08, 0x04, 0x02),
    '0': (0x3E, 0x51, 0x49, 0x45, 0x3E),
    '1': (0x00, 0x42, 0x7F, 0x40, 0x00),
    '2': (0x42, 0x61, 0x51, 0x49, 0x46),
    '3': (0x21, 0x41, 0x45, 0x4B, 0x31),
    '4': (0x18, 0x14, 0x12, 0x7F, 0x10),
    '5': (0x27, 0x45, 0x45, 0x45, 0x39),
    '6': (0x3C, 0x4A, 0x49, 0x49, 0x30),
    '7': (0x01, 0x71, 0x09, 0x05, 0x03),
    '8': (0x36, 0x49, 0x49, 0x49, 0x36),
    '9': (0x06, 0x49, 0x49, 0x29, 0x1E),
    ':': (0x00, 0x36, 0x36, 0x00, 0x00),
    ';': (0x00, 0x56, 0x36, 0x00, 0x00),
    '<': (0x08, 0x14, 0x22, 0x41, 0x00),
    '=': (0x14, 0x14, 0x14, 0x14, 0x14),
    '>': (0x00, 0x41, 0x22, 0x14, 0x08),
    '?': (0x02, 0x01, 0x51, 0x09, 0x06),
    '@': (0x32, 0x49, 0x79, 0x41, 0x3E),
    'A': (0x7E, 0x11, 0x11, 0x11, 0x7E),
    'B': (0x7F, 0x49, 0x49, 0x49, 0x36),
    'C': (0x3E, 0x41, 0x41, 0x41, 0x22),
    'D': (0x7F, 0x41, 0x41, 0x22, 0x1C),
    'E': (0x7F, 0x49, 0x49, 0x49, 0x41),
    'F': (0x7F, 0x09, 0x09, 0x09, 0x01),
    'G': (0x3E, 0x41, 0x49, 0x49, 0x7A),
    'H': (0x7F, 0x08, 0x08, 0x08, 0x7F),
    'I': (0x00, 0x41, 0x7F, 0x41, 0x00),
    'J': (0x20, 0x40, 0x41, 0x3F, 0x01),
    'K': (0x7F, 0x08, 0x14, 0x22, 0x41),
    'L': (0x7F, 0x40, 0x40, 0x40, 0x40),
    'M': (0x7F, 0x02, 0x0C, 0x02, 0x7F),
    'N': (0x7F, 0x04, 0x08, 0x10, 0x7F),
    'O': (0x3E, 0x41, 0x41, 0x41, 0x3E),
    'P': (0x7F, 0x09, 0x09, 0x09, 0x06),
    'Q': (0x3E, 0x41, 0x51, 0x21, 0x5E),
    'R': (0x7F, 0x09, 0x19, 0x29, 0x46),
    'S': (0x46, 0x49, 0x49, 0x49, 0x31),
    'T': (0x01, 0x01, 0x7F, 0x01, 0x01),
    'U': (0x3F, 0x40, 0x40, 0x40, 0x3F),
    'V': (0x1F, 0x20, 0x40, 0x20, 0x1F),
    'W': (0x3F, 0x40, 0x38, 0x40, 0x3F),
    'X': (0x63, 0x14, 0x08, 0x14, 0x63),
    'Y': (0x07, 0x08, 0x70, 0x08, 0x07),
    'Z': (0x61, 0x51, 0x49, 0x45, 0x43),
    '[': (0x00, 0x7F, 0x41, 0x41, 0x00),
    '\\': (0x02, 0x04, 0x08, 0x10, 0x20),
    ']': (0x00, 0x41, 0x41, 0x7F, 0x00),
    '^': (0x04, 0x02, 0x01, 0x02, 0x04),
    '_': (0x40, 0x40, 0x40, 0x40, 0x40),
    '`': (0x00, 0x01, 0x02, 0x04, 0x00),
    'a': (0x20, 0x54, 0x54, 0x54, 0x78),
    'b': (0x7F, 0x48, 0x44, 0x44, 0x38),
    'c': (0x38, 0x44, 0x44, 0x44, 0x20),
    'd': (0x38, 0x44, 0x44, 0x48, 0x7F),
    'e': (0x38, 0x54, 0x54, 0x54, 0x18),
    'f': (0x08, 0x7E, 0x09, 0x01, 0x02),
    'g': (0x0C, 0x52, 0x52, 0x52, 0x3E),
    'h': (0x7F, 0x08, 0x04, 0x04, 0x78),
    'i': (0x00, 0x44, 0x7D, 0x40, 0x00),
    'j': (0x20, 0x40, 0x44, 0x3D, 0x00),
    'k': (0x7F, 0x10, 0x28, 0x44, 0x00),
    'l': (0x00, 0x41, 0x7F, 0x40, 0x00),
    'm': (0x7C, 0x04, 0x18, 0x04, 0x78),
    'n': (0x7C, 0x08, 0x04, 0x04, 0x78),
    'o': (0x38, 0x44, 0x44, 0x44, 0x38),
    'p': (0x7C, 0x14, 0x14, 0x14, 0x08),
    'q': (0x08, 0x14, 0x14, 0x18, 0x7C),
    'r': (0x7C, 0x08, 0x04, 0x04, 0x08),
    's': (0x48, 0x54, 0x54, 0x54, 0x20),
    't': (0x04, 0x3F, 0x44, 0x40, 0x20),
    'u': (0x3C, 0x40, 0x40, 0x20, 0x7C),
    'v': (0x1C, 0x20, 0x40, 0x20, 0x1C),
    'w': (0x3C, 0x40, 0x30, 0x40, 0x3C),
    'x': (0x44, 0x28, 0x10, 0x28, 0x44),
    'y': (0x0C, 0x50, 0x50, 0x50, 0x3C),
    'z': (0x44, 0x64, 0x54, 0x4C, 0x44),
    '{': (0x00, 0x08, 0x36, 0x41, 0x00),
    '|': (0x00, 0x00, 0x7F, 0x00, 0x00),
    '}': (0x00, 0x41, 0x36, 0x08, 0x00),
    '~': (0x10, 0x08, 0x08, 0x10, 0x08),
}


def text_width(text, scale):
    """Pixel width of text at the given scale (6 px per char cell, minus trailing gap)."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, text, scale, rgb, align="left"):
    if align == "center":
        x -= text_width(text, scale) // 2
    elif align == "right":
        x -= text_width(text, scale)
    cx = x
    for ch in text:
        cols = FONT.get(ch, FONT['?'])
        for col in range(5):
            bits = cols[col]
            for row in range(7):
                if bits & (1 << row):
                    cv.fill_rect(cx + col * scale, y + row * scale, scale, scale, rgb)
        cx += 6 * scale
    return cx


def wrap(text, max_chars):
    """Greedy word wrap into lines of at most max_chars characters."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            if not line:
                line = word
            elif len(line) + 1 + len(word) <= max_chars:
                line += " " + word
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Story icons (simple geometric shapes, drawn in a 40x40 box at ox, oy)
# ---------------------------------------------------------------------------

def icon_ship(cv, ox, oy, c):
    # hull, deck, mast, flag, waves
    cv.fill_rect(ox + 2, oy + 24, 36, 9, c)
    cv.fill_rect(ox + 8, oy + 16, 24, 8, c)
    cv.fill_rect(ox + 18, oy + 6, 3, 11, c)
    cv.fill_rect(ox + 21, oy + 6, 9, 6, c)
    cv.hline(ox + 0, oy + 37, 40, c, 2)


def icon_bridge(cv, ox, oy, c):
    # two towers, deck, suspension cables, water
    cv.fill_rect(ox + 5, oy + 8, 5, 26, c)
    cv.fill_rect(ox + 30, oy + 8, 5, 26, c)
    cv.hline(ox + 0, oy + 30, 40, c, 3)
    cv.line(ox + 7, oy + 10, ox + 20, oy + 28, c)
    cv.line(ox + 33, oy + 10, ox + 20, oy + 28, c)
    cv.hline(ox + 0, oy + 37, 40, c, 2)


def icon_aid(cv, ox, oy, c):
    # aid crate with a cross
    cv.fill_rect(ox + 6, oy + 8, 28, 26, c)
    cv.fill_rect(ox + 17, oy + 12, 6, 18, BG)
    cv.fill_rect(ox + 11, oy + 18, 18, 6, BG)


def icon_columns(cv, ox, oy, c):
    # government building: pediment, columns, base
    cv.fill_rect(ox + 10, oy + 4, 20, 4, c)
    cv.fill_rect(ox + 4, oy + 8, 32, 4, c)
    for cx in (7, 17, 27):
        cv.fill_rect(ox + cx, oy + 12, 5, 18, c)
    cv.fill_rect(ox + 4, oy + 30, 32, 4, c)
    cv.fill_rect(ox + 2, oy + 34, 36, 3, c)


def icon_globe(cv, ox, oy, c):
    # globe: outline circle + latitude lines
    cv.circle(ox + 20, oy + 19, 15, c, thick=2)
    cv.hline(ox + 8, oy + 13, 24, c, 2)
    cv.hline(ox + 5, oy + 19, 30, c, 2)
    cv.hline(ox + 8, oy + 25, 24, c, 2)


def icon_missile(cv, ox, oy, c):
    # missile pointing up, flame below
    cv.fill_rect(ox + 18, oy + 6, 4, 6, c)
    cv.fill_rect(ox + 17, oy + 12, 6, 16, c)
    cv.fill_rect(ox + 12, oy + 24, 5, 5, c)
    cv.fill_rect(ox + 23, oy + 24, 5, 5, c)
    cv.fill_rect(ox + 18, oy + 30, 4, 4, GOLD)
    cv.fill_rect(ox + 19, oy + 34, 2, 4, GOLD)


ICONS = {
    "ship": icon_ship,
    "bridge": icon_bridge,
    "aid": icon_aid,
    "columns": icon_columns,
    "globe": icon_globe,
    "missile": icon_missile,
}

# ---------------------------------------------------------------------------
# Content — world news of Wednesday 18 November 2026 (as reported)
# ---------------------------------------------------------------------------

STORIES = [
    {
        "kicker": "MIDDLE EAST",
        "accent": (229, 72, 77),
        "icon": "ship",
        "headline": "US SINKS 5 IRANIAN TANKERS",
        "body": "US sank five tankers after Iran twice targeted a US warship. Iran hit ships.",
    },
    {
        "kicker": "UKRAINE",
        "accent": (76, 154, 255),
        "icon": "bridge",
        "headline": "UKRAINE HITS KERCH BRIDGE AGAIN",
        "body": "Kyiv hit Kerch Bridge a 2nd night; peace talks went on with US envoys. Russia hit two bridges.",
    },
    {
        "kicker": "GAZA",
        "accent": (45, 212, 191),
        "icon": "aid",
        "headline": "GAZA: CALL FOR OPEN AID ACCESS",
        "body": "Four nations urged open aid access as floods hit. 1.7M displaced; 1.4M face acute hunger.",
    },
    {
        "kicker": "ISRAEL",
        "accent": (177, 140, 255),
        "icon": "columns",
        "headline": "HERZOG TAPS EISENKOT TO FORM GOVT",
        "body": "Herzog asked ex-army chief Eisenkot to form the next government, bypassing Netanyahu.",
    },
    {
        "kicker": "CLIMATE - COP31",
        "accent": (76, 195, 138),
        "icon": "globe",
        "headline": "COP31 CLIMATE TALKS ENTER FINAL DAYS",
        "body": "Draft deal has 144 disputed items; talks end Friday 20 November in Antalya.",
    },
    {
        "kicker": "NORTH KOREA",
        "accent": (245, 166, 35),
        "icon": "missile",
        "headline": "NORTH KOREA FIRES BALLISTIC MISSILE",
        "body": "Pyongyang launched a ballistic missile toward the Sea of Japan.",
    },
]

BRIEFS = [
    "Romania quake 5.3; Russian An-12 crash kills 19 in Kemerovo.",
    "Waymo pulls driverless taxis from all US freeways.",
    "Peltola wins Alaska Senate seat; Democrats hold 56 seats.",
    "US report on $12bn Venezuela oil revenue; measles at 40-year high.",
    "Pattinson is the new James Bond; Trump in Manila; Britain sanctions firms.",
]

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

MARGIN = 24
GRID_TOP = 168
CELL_W = 480
CELL_H = 232
COL_GAP = 16
ROW_GAP = 12
STRIP_TOP = 900


def draw_header(cv):
    cv.fill_rect(0, 0, W, 152, HEADER_BG)
    cv.hline(0, 0, W, GOLD, 4)
    draw_text(cv, W // 2, 26, "WORLD NEWS", 7, TEXT, align="center")
    draw_text(cv, W // 2, 92, "WEDNESDAY, 18 NOVEMBER 2026", 4, GOLD, align="center")
    cv.hline(0, 152, W, GOLD, 3)


def draw_story(cv, x, y, story):
    accent = story["accent"]
    cv.fill_rect(x, y, CELL_W, CELL_H, CELL_BG)
    # border
    cv.hline(x, y, CELL_W, CELL_BORDER, 1)
    cv.hline(x, y + CELL_H - 1, CELL_W, CELL_BORDER, 1)
    cv.vline(x, y, CELL_H, CELL_BORDER, 1)
    cv.vline(x + CELL_W - 1, y, CELL_H, CELL_BORDER, 1)
    # accent bar
    cv.fill_rect(x, y, CELL_W, 6, accent)
    # kicker
    draw_text(cv, x + 16, y + 18, story["kicker"], 2, accent)
    # icon, top-right
    ICONS[story["icon"]](cv, x + CELL_W - 56, y + 12, accent)
    # headline (scale 3, up to 2 lines, 24 chars/line)
    head_lines = wrap(story["headline"], 24)[:2]
    hy = y + 46
    for line in head_lines:
        draw_text(cv, x + 16, hy, line, 3, TEXT)
        hy += 26
    # body (scale 3, up to 4 lines, 24 chars/line)
    body_lines = wrap(story["body"], 24)[:4]
    by = hy + 10
    for line in body_lines:
        draw_text(cv, x + 16, by, line, 3, BODY)
        by += 26


def draw_strip(cv):
    cv.fill_rect(0, STRIP_TOP, W, 100, STRIP_BG)
    cv.hline(0, STRIP_TOP, W, GOLD, 2)
    y = STRIP_TOP + 10
    for i, brief in enumerate(BRIEFS):
        if i == 0:
            draw_text(cv, MARGIN, y, "ALSO TODAY: ", 2, GOLD)
            draw_text(cv, MARGIN + text_width("ALSO TODAY: ", 2), y, brief, 2, BODY)
        else:
            draw_text(cv, MARGIN, y, brief, 2, BODY)
        y += 18


def render():
    cv = Canvas(W, H, BG)
    draw_header(cv)
    for idx, story in enumerate(STORIES):
        col = idx % 2
        row = idx // 2
        x = MARGIN + col * (CELL_W + COL_GAP)
        y = GRID_TOP + row * (CELL_H + ROW_GAP)
        draw_story(cv, x, y, story)
    draw_strip(cv)
    return cv


# ---------------------------------------------------------------------------
# Deterministic PNG writer (stdlib only: struct + zlib, no ancillary chunks)
# ---------------------------------------------------------------------------

def _chunk(chunk_type, data):
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_png(path, cv):
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = bytearray()
    for yy in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.buf[yy * cv.w * 3:(yy + 1) * cv.w * 3]
    idat = zlib.compress(bytes(raw), 9)  # fixed level -> deterministic
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", idat)
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = render()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, cv)
    print(f"Wrote {path} ({cv.w}x{cv.h}, {size} bytes)")


if __name__ == "__main__":
    main()
