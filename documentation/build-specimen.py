#!/usr/bin/env python3
# Specimen images for DotMatrix, and the presentation image.
#
# The specimens are printouts on continuous form paper, as the Epson FX-80 would
# have printed them: greenbar paper with tractor holes, struck in the print mode
# the page is about. The glyphs are the real glyphs of the fonts, so the dots are
# the dots of the fonts; the paper and the ribbon are the only simulation.
#
# One specimen per group, its six widths from the narrowest to the widest:
#
#   DotMatrix-Sample1.jpg   DotMatrix Mono
#   DotMatrix-Sample2.jpg   DotMatrix Sans (the proportional mode)
#   DotMatrix-Sample3.jpg   the character set
#
# Every page has a title. Each width is a block of four lines, one per style
# (Regular, Bold, Italic and Bold Italic), and the blocks are in pairs side by
# side: the plain width and Condensed, SemiExpanded and Expanded, ExtraExpanded
# and UltraExpanded.
#
# Every glyph of DotMatrix is a composite of one round element glyph, so the
# position of every dot (its jitter, and the second strike of the double-strike
# styles) is read from the .ttf files, and every dot is struck on its own:
# under the microscope a dot is not a black disk. Its outline is ragged and a
# little oval, its rim holds more ink than its middle, the threads of the
# ribbon print into it, and the ink wicks out along the fibers of the paper.
#
# The presentation image is a macro photograph of a printout, DotMatrix-
# Presentation.jpg: the word struck dot by dot, on greenbar paper laid as in the
# specimens, photographed at an angle: the paper is tilted and in perspective,
# the focus falls on the word and the lines below it are out of focus, and a
# raking light pools on the word. The paper has fibers and the pins dimple it.
# The photograph has a scale: a dot is 1.10 of a print row of 1/72 inch, 0.39 mm (the pins of the
# FX-80 are 0.34 mm wide, and the ink of the ribbon spreads), and everything else is sized from it in
# millimeters: the paper fibers, the screen of the green bars and the threads
# of the ribbon.
#
# The fonts must be built (fonts/ttf) before the images are.
#
# (C) 2024-2026 Gissio
#
# License: MIT

import argparse
import math
import random
import textwrap
import unicodedata
from pathlib import Path
from typing import NamedTuple

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT_PATH = Path(__file__).resolve().parent.parent
FONTS_PATH = ROOT_PATH / "fonts" / "ttf"
OUT_PATH = Path(__file__).resolve().parent

JPG_QUALITY = 95


# =============================================================================
# The dots
# =============================================================================

# The width of a dot: 1.10 of a print row of 1/72 inch, 224 of the 204 font units of a row
# (ELEMENT_WEIGHT 440 of scripts/build-dotmatrix-sources.py)
ELEMENT_UNITS = 224
DOT_MM = ELEMENT_UNITS / 204 * 25.4 / 72

# The thread pitch of the ribbon
WEAVE_MM = 0.085


def dot_ink(dx, dy, radius, rng, pitch, local=0.0):
    """The ink of one dot, on a grid of offsets from its center.

    Every dot is struck anew: a little oval and ragged, with its own pressure.
    The rim holds more ink than the middle (the pin pushes the ink out), and a
    hard strike leaves the middle lighter. The threads of the ribbon print into
    the dot, with gaps between them, and the ink wicks out along the fibers.

    Args:
        dx, dy: offsets from the center of the dot, in pixels.
        radius: the radius of the dot, in pixels.
        pitch: the thread pitch of the ribbon, in pixels.
        local: the fibers of the paper under the dot (0 to 1).

    Returns:
        The ink of the dot (0 to 1), the ink wicked out (0 to 1), the pressure
        of the strike, and the distance from the center, in radii.
    """
    theta = np.arctan2(dy, dx)

    # Oval: the pin and the ribbon do not meet squarely
    stretch = rng.normal(0, 0.04)
    phi = rng.uniform(0, math.pi)
    u = dx * math.cos(phi) + dy * math.sin(phi)
    v = -dx * math.sin(phi) + dy * math.cos(phi)
    rho = np.hypot(u * (1 + stretch), v * (1 - stretch))

    # The outline: out of round, and ragged
    outline = np.ones_like(rho)
    for harmonic in range(2, 6):
        outline += rng.normal(0, 0.03 / (harmonic - 1)) * np.cos(
            harmonic * theta + rng.uniform(0, math.tau)
        )
    for harmonic in range(6, 15):
        outline += rng.normal(0, 0.014) * np.cos(
            harmonic * theta + rng.uniform(0, math.tau)
        )
    rn = rho / (radius * rng.normal(1.0, 0.03) * outline)

    # The edge of the ink follows the fibers of the paper
    rn = rn + 0.16 * (local - 0.25) * (rn > 0.6)

    coverage = np.clip((1.05 - rn) / 0.13, 0, 1)
    coverage = coverage * coverage * (3 - 2 * coverage)

    # The weave of the ribbon, printed into the dot: the ribbon moves between
    # strikes, so every dot carries its own phase and angle
    angle = rng.normal(0, 0.05)
    a = dx * math.cos(angle) + dy * math.sin(angle) + rng.uniform(0, pitch)
    b = -dx * math.sin(angle) + dy * math.cos(angle) + rng.uniform(0, pitch)
    # The threads are not straight, nor evenly spaced
    a = a + 0.22 * pitch * np.sin(math.tau * b / (2.9 * pitch) + rng.uniform(0, math.tau))
    b = b + 0.22 * pitch * np.sin(math.tau * a / (3.3 * pitch) + rng.uniform(0, math.tau))
    warp = 0.5 + 0.5 * np.cos(math.tau * a / pitch)
    weft = 0.5 + 0.5 * np.cos(math.tau * b / pitch)
    weave = np.sqrt(np.clip(warp + weft - warp * weft, 0, 1))

    # The strike: the rim holds more ink, a hard strike empties the middle
    pressure = float(np.clip(rng.normal(0.95, 0.04), 0.78, 1.0))
    rim = rng.uniform(0.0, 0.5)
    hollow = rng.uniform(0.0, 0.30) if rng.random() < 0.35 else 0.0
    core = (
        pressure * (0.70 + 0.30 * weave)
        + 0.30 * rim * np.exp(-(((rn - 0.86) / 0.16) ** 2))
        - hollow * np.exp(-((rn / 0.5) ** 2))
    )
    density = coverage * (1 - (1 - np.clip(core, 0, 1)) ** 1.5)

    # Ink wicks out along the fibers, in tufts around the dot
    feather = np.zeros_like(rho)
    for harmonic in range(7, 20):
        feather += rng.normal(0, 0.9 / harmonic) * np.cos(
            harmonic * theta + rng.uniform(0, math.tau)
        )
    wick = (
        np.exp(-(((rn - 1.02 - 0.12 * feather) / 0.30) ** 2))
        * (rn > 0.9)
        * (0.10 + 0.55 * local)
    )

    return density, wick * pressure * 0.55, pressure, rn


# =============================================================================
# The specimens
# =============================================================================

# --- The page ----------------------------------------------------------------

CANVAS = (1920, 1080)
JPG_QUALITY = 95

# The text is drawn at this many times the canvas size and reduced, so the dots
# come out smooth
SUPERSAMPLE = 2

# One font size for every font, as on the printer: the dots are the same size,
# and the pitch sets the width of the characters. A print row (1/72 inch) is
# 204 of the 2048 font units, and a font has 10 of them.
FONT_SIZE = 50
PRINT_ROW = FONT_SIZE * 204 / 2048
LINE_HEIGHT = 60                    # 6 lines per inch: 12 pt, at 10 pt = 50 pixels
LINES = CANVAS[1] // LINE_HEIGHT    # the lines of a page
BASELINE = round((LINE_HEIGHT - 10 * PRINT_ROW) / 2 + 8 * PRINT_ROW)

BAR_LINES = 3                       # greenbar paper: bars of half an inch
TRACTOR_WIDTH = 135                 # the tractor strip, with the sprocket holes
TEXT_LEFT = TRACTOR_WIDTH + 30
TEXT_RIGHT = CANVAS[0] - 15

# --- The paper and the ribbon ------------------------------------------------

PAPER_COLOR = (250, 249, 246)
PAPER_GRAIN = 9                     # depth of the paper grain, of 255
BAR_COLOR = (216, 236, 228)
INK = (38, 35, 42)
INK_SPREAD = 0.5                    # ink soaking into the paper, in pixels
SKEW = 0.15                         # the paper feeds in slightly askew, in degrees
WEAVE_PITCH = 4.0                   # the thread pitch of the ribbon, in supersampled pixels
PASS_OFFSET = 1                     # the head lands off on every other line, in pixels
PATCH_SIZE = 24                     # the patches the ribbon inks unevenly, in pixels / 8
PATCH_LEVEL = 165                   # the ink level of the faintest patch, of 255
WEAK_PINS = 2                       # pins that strike faintly, the same on every line
NOISE_SEED = 5                      # every imperfection is reproducible

# --- The print modes ---------------------------------------------------------


class Mode(NamedTuple):
    """A print mode: the name of the font that prints it, as a font menu lists it."""

    name: str


class Style(NamedTuple):
    """A style: its font file suffix and its name."""

    key: str
    name: str


STYLES = [
    Style("Regular", "Regular"),
    Style("Bold", "Bold"),
    Style("Italic", "Italic"),
    Style("BoldItalic", "Bold Italic"),
]

# The widths of a page, in pairs of blocks side by side: Elite (the plain font)
# and Compressed, Pica and Expanded Compressed, Expanded Elite and Expanded Pica
PAGE_WIDTHS = [
    ["", "Condensed"],
    ["SemiExpanded", "Expanded"],
    ["ExtraExpanded", "UltraExpanded"],
]
COLUMN_GAP = 30


def group_mode(group, width):
    return Mode(" ".join(filter(None, ["DotMatrix", group, width])))

# --- The fonts ---------------------------------------------------------------


class Face:
    """A font as the specimen needs it: the advances of its characters, and the
    dots of its glyphs."""

    def __init__(self, path):
        font = TTFont(path)
        self.glyf = font["glyf"]
        self.hmtx = font["hmtx"]
        self.cmap = font.getBestCmap()
        element = self.glyf["_"]
        self.radius = (element.xMax - element.xMin) / 2     # in font units

    def width(self, text):
        """The width of a text, in canvas pixels."""
        return sum(self.hmtx[self.cmap[ord(c)]][0] for c in text) * FONT_SIZE / 2048

    def dots(self, text):
        """The dots of a text, as (x, y) in font units: x from the start of the
        text, y up from the baseline."""
        pen = 0
        for character in text:
            name = self.cmap[ord(character)]
            glyph = self.glyf[name]
            if glyph.isComposite():
                for component in glyph.components:
                    yield pen + component.x, component.y
            pen += self.hmtx[name][0]


_faces = {}


def get_font(fonts_path, name, style):
    path = fonts_path / f"{name.replace(' ', '')}-{style}.ttf"
    if path not in _faces:
        _faces[path] = Face(path)

    return _faces[path]


def text_width(face, text):
    """Return the width of a text, in canvas pixels."""
    return face.width(text)


# --- The pages ---------------------------------------------------------------

# A page is a list of lines, one per print line: None for a blank line, or a
# list of cells, (text, font, x), x being the start of the text in pixels


def text_line(face, text):
    return [(text, face, TEXT_LEFT)]


# The title is in SemiExpanded (Pica) Bold, ruled off below
TITLE_WIDTH = "SemiExpanded"
RULE_CHARACTER = "═"


def title_lines(fonts_path, text, group="Mono"):
    """A title: centered, in the title width of the group, in Bold, and a
    double rule across the page below it, in the plain width."""
    face = get_font(fonts_path, group_mode(group, TITLE_WIDTH).name, "Bold")
    title = [(text, face, (TEXT_LEFT + TEXT_RIGHT - text_width(face, text)) / 2)]

    rule_face = get_font(fonts_path, "DotMatrix Mono", "Regular")
    count = int((TEXT_RIGHT - TEXT_LEFT) // text_width(rule_face, RULE_CHARACTER))
    rule = text_line(rule_face, RULE_CHARACTER * count)

    return [title, rule]


def centered(lines):
    """Center the lines of a page on the page."""
    if len(lines) > LINES:
        raise ValueError("The lines do not fit one page")

    return [None] * ((LINES - len(lines)) // 2) + lines


def style_initials(style):
    """The style abbreviated to its initials: Bold Italic is BI."""
    return "".join(word[0] for word in style.name.split())


# The groups, a page each
GROUPS = ["Mono", "Sans"]


def block_cells(fonts_path, group, width, column_width):
    """The cells of the block of a width, a style each. A cell names its font:
    the width (none for the plain width) and the style. The width is written in
    full if all the styles fit with it, or with Expanded abbreviated (Exp). If a
    style still does not fit, all the styles of the block are abbreviated to
    their initials (R, B, I, BI). A width is named the same on the pages of
    all the groups: the names must fit in every group."""

    def labels(word, initials):
        return [f"{word} {style_initials(style) if initials else style.name}".strip()
                for style in STYLES]

    def fits(word, initials):
        return all(
            text_width(get_font(fonts_path, group_mode(g, width).name, style.key), text)
            <= column_width
            for g in GROUPS
            for style, text in zip(STYLES, labels(word, initials))
        )

    choices = [(word, initials)
               for initials in (False, True)
               for word in (width, width.replace("Expanded", "Exp"))]
    word, initials = next(
        (choice for choice in choices if fits(*choice)), (None, None)
    )
    if word is None:
        raise ValueError(f"The styles of {width or 'the plain width'} do not fit a column")

    mode = group_mode(group, width)
    return [(text, get_font(fonts_path, mode.name, style.key))
            for style, text in zip(STYLES, labels(word, initials))]


def group_page(fonts_path, group):
    """The page of a group: its title, and the blocks of its widths in pairs,
    with a blank line between the pairs."""
    family = f"DotMatrix {group}"
    columns = len(PAGE_WIDTHS[0])
    column_width = (TEXT_RIGHT - TEXT_LEFT - (columns - 1) * COLUMN_GAP) / columns

    lines = title_lines(fonts_path, family, group)
    for widths in PAGE_WIDTHS:
        # The rule sets the first pair off from the title
        if widths is not PAGE_WIDTHS[0]:
            lines.append(None)
        blocks = [block_cells(fonts_path, group, width, column_width) for width in widths]
        for row in zip(*blocks):
            lines.append([
                (text, face, TEXT_LEFT + column * (column_width + COLUMN_GAP))
                for column, (text, face) in enumerate(row)
            ])

    return centered(lines)


def mono_page(fonts_path):
    return group_page(fonts_path, "Mono")


def sans_page(fonts_path):
    return group_page(fonts_path, "Sans")


def character_set_page(fonts_path):
    """The character set in code point order, as many characters as a line
    holds, without the combining marks (they have no cell of their own)."""
    font = get_font(fonts_path, "DotMatrix Mono", "Regular")
    cmap = font.cmap
    characters = [
        chr(code)
        for code in sorted(cmap)
        if unicodedata.category(chr(code)) not in ("Mn", "Me", "Cc", "Cf", "Zs")
    ]

    width = TEXT_RIGHT - TEXT_LEFT
    # The title counts all the characters of the font, the marks included
    lines = title_lines(fonts_path, f"{len(cmap)} characters")

    line = ""
    for character in characters:
        if text_width(font, line + character) > width:
            lines.append(text_line(font, line))
            line = ""
        line += character
    lines.append(text_line(font, line))

    # The title and the characters are centered on the page
    return centered(lines)


# --- The printout ------------------------------------------------------------


def noise_image(size, rng):
    return Image.frombytes("L", size, rng.randbytes(size[0] * size[1]))


def grain_field(size, rng, depth):
    """A fine multiplicative grain field: the fibers of the paper."""
    return noise_image(size, rng).point(lambda v: 255 - depth + v * depth // 255)


def draw_paper(rng):
    """Draw greenbar paper: bars of three lines, the perforated tractor strip
    and its sprocket holes, and the grain of the paper."""
    img = Image.new("RGB", CANVAS, PAPER_COLOR)
    draw = ImageDraw.Draw(img)

    bar = BAR_LINES * LINE_HEIGHT
    for top in range(0, CANVAS[1], 2 * bar):
        draw.rectangle(
            xy=[(TRACTOR_WIDTH, top), (CANVAS[0], top + bar - 1)], fill=BAR_COLOR
        )

    # The perforation
    draw.rectangle(xy=[(TRACTOR_WIDTH - 2, 0), (TRACTOR_WIDTH + 1, CANVAS[1])],
                   fill=(230, 230, 227))
    for y in range(0, CANVAS[1], 24):
        draw.rectangle(xy=[(TRACTOR_WIDTH - 2, y), (TRACTOR_WIDTH + 1, y + 11)],
                       fill=(202, 202, 199))

    # The sprocket holes, punched through to the dark platen, one per bar
    for y in range(bar // 2, CANVAS[1], bar):
        xy = (TRACTOR_WIDTH // 2, y)
        draw.circle(xy=xy, radius=24, fill=(208, 208, 205))
        draw.circle(xy=xy, radius=22, fill=(28, 26, 30))

    return ImageChops.multiply(img, grain_field(CANVAS, rng, PAPER_GRAIN).convert("RGB"))


def ink_mask(lines, rng):
    """Strike the lines of a page: the ink laid on the paper, from 0 to 255.

    The imperfections: the ribbon inks in patches, worn pins strike faintly, the
    head lands slightly off on every other line, and the paper feeds in a little
    askew.
    """
    size = (CANVAS[0] * SUPERSAMPLE, CANVAS[1] * SUPERSAMPLE)
    ink = np.zeros((size[1], size[0]), np.float32)
    np_rng = np.random.default_rng(NOISE_SEED)

    unit = FONT_SIZE * SUPERSAMPLE / 2048           # pixels per font unit

    for index, line in enumerate(lines):
        if line is None:
            continue

        y = index * LINE_HEIGHT + BASELINE
        for text, face, x in line:
            x += PASS_OFFSET * (index % 2)

            radius = face.radius * unit
            half = int(radius * 2.1)
            grid_y, grid_x = np.mgrid[-half : half + 1, -half : half + 1].astype(np.float32)

            for dot_x, dot_y in face.dots(text):
                cx = x * SUPERSAMPLE + dot_x * unit
                cy = y * SUPERSAMPLE - dot_y * unit
                x0, y0 = int(round(cx)) - half, int(round(cy)) - half
                if x0 < 0 or y0 < 0 or x0 + 2 * half + 1 > size[0] or y0 + 2 * half + 1 > size[1]:
                    continue

                density, wick, _, _ = dot_ink(
                    grid_x - (cx - round(cx)), grid_y - (cy - round(cy)),
                    radius, np_rng, WEAVE_PITCH,
                )
                patch = ink[y0 : y0 + 2 * half + 1, x0 : x0 + 2 * half + 1]
                patch[:] = 1 - (1 - patch) * (1 - np.maximum(density, wick))

    ink = Image.fromarray((ink * 255).clip(0, 255).astype(np.uint8))
    ink = ink.resize(CANVAS, Image.LANCZOS)

    # The ribbon inks unevenly, in patches
    patches = (max(CANVAS[0] // (PATCH_SIZE * 8), 1), max(CANVAS[1] // (PATCH_SIZE * 8), 1))
    blotch = noise_image(patches, rng).resize(CANVAS, Image.BICUBIC)
    blotch = blotch.point(lambda v: PATCH_LEVEL + v * (255 - PATCH_LEVEL) // 255)
    ink = ImageChops.multiply(ink, blotch)

    # Worn pins strike faintly, the same pin rows on every line
    pins = Image.new("L", CANVAS, 255)
    pins_draw = ImageDraw.Draw(pins)
    top_row = (LINE_HEIGHT - 10 * PRINT_ROW) / 2
    for pin in rng.sample(range(10), WEAK_PINS):
        level = rng.randrange(150, 230)
        for line in range(LINES):
            y = line * LINE_HEIGHT + top_row + pin * PRINT_ROW
            pins_draw.rectangle(xy=[(0, y), (CANVAS[0], y + PRINT_ROW - 1)], fill=level)
    ink = ImageChops.multiply(ink, pins)

    # Ink soaks into the paper, and the paper feeds in slightly askew
    ink = ink.filter(ImageFilter.GaussianBlur(INK_SPREAD))

    return ink.rotate(SKEW, resample=Image.BILINEAR)


def build_page(lines, name, out_path):
    rng = random.Random(NOISE_SEED)

    img = draw_paper(rng)
    img.paste(Image.new("RGB", CANVAS, INK), (0, 0), ink_mask(lines, rng))

    img.save(out_path / name, optimize=True, quality=JPG_QUALITY)
    print(name)


# =============================================================================
# The presentation image
# =============================================================================

MACRO_SEED = 1983

# --- The shot ----------------------------------------------------------------

# The photograph is rendered at this size, and reduced to the size asked for
MACRO_OUTPUT = (3840, 2160)

# The printout is laid flat at this size, larger than the photograph so that
# the tilt of the paper never shows its edge
MACRO_RENDER = (5632, 3456)

# The word, set in the font of the print mode, Pica Regular. It spans MACRO_SPAN
# of the width of the photograph, and its ink is centered on MACRO_WORD. Under it, the
# start of the description of the font is set in small print, as the FX-80 sets
# the body of a document: in Compressed, in lines of a page, which run off the
# photograph. The lines start under the first letter of the word, as on a printout.
MACRO_TITLE = ("DotMatrix", "DotMatrixMonoSemiExpanded-Regular.ttf")
MACRO_BODY = (
    "A contemporary revival of classic 1980s dot matrix printing, faithfully "
    "recreating the texture, rhythm, and mechanical imperfections of early "
    "impact printers."
)
MACRO_BODY_FONT = "DotMatrixMonoCondensed-Regular.ttf"
MACRO_BODY_COLUMNS = 70             # characters of a line of the body: a line of a page
MACRO_BODY_LINES = 3                # two on the white lines, and one on the green below
MACRO_SPAN = 0.62
MACRO_WORD = (0.42, 0.42)           # where the ink of the word is centered, of the size of
                                    # the photograph: the lines run off to the right
MACRO_LINE_ROWS = 12                # print rows between baselines: 1/6 inch


def macro_lines():
    """The lines of the printout: the word, and its body in the small print."""
    body = textwrap.wrap(MACRO_BODY, MACRO_BODY_COLUMNS)[:MACRO_BODY_LINES]

    return [MACRO_TITLE] + [(line, MACRO_BODY_FONT) for line in body]


# --- The paper ---------------------------------------------------------------

MACRO_PAPER = (0.965, 0.953, 0.925)       # albedo of the paper
MACRO_BAR = (0.82, 0.945, 0.905)          # the green of the bars, over the paper
MACRO_BAR_LINES = 3                       # three lines of green, three of white, as in the specimens
MACRO_BAR_GAP_ROWS = 9                    # a white band starts where the line of the word starts:
                                          # its baseline is 9 print rows below, as in the specimens
MACRO_BAR_SCREEN_MM = 0.19                # the pitch of the screen the bars are printed in

# The fibers of the paper, from the pulp: length and width in mm, and how many
# lie in the frame (a sheet of 75 g/m2 shows a few hundred on its surface).
# Fibers lie along the machine direction of the paper, which feeds vertically.
MACRO_FIBERS = [
    # (count, length, width): softwood, hardwood, and the fines between them
    (45, (1.6, 3.2), (0.026, 0.040)),
    (130, (0.55, 1.2), (0.016, 0.024)),
    (500, (0.08, 0.35), (0.004, 0.010)),
]
MACRO_BURIED = 9.0                        # as many more lie beneath the surface, fainter
MACRO_MACHINE_DIRECTION = math.pi / 2     # the angle of the machine direction
MACRO_FIBER_SPREAD = 0.50                 # how far fibers stray from it, in radians
MACRO_FIBER_HEIGHT = 0.9                  # the height of a fiber over the sheet, in pixels

# --- The fold ---------------------------------------------------------------

# Continuous paper is folded between pages: a ridge across the paper, between two
# of the lines (the line count is from the word)
MACRO_FOLD_LINE = 2
MACRO_FOLD_MM = 0.5                       # the width of the ridge
MACRO_FOLD_HEIGHT = 5                     # its height, in pixels

# --- The ink -----------------------------------------------------------------

MACRO_INK = (0.075, 0.058, 0.105)         # a nylon ribbon: black, a little violet
MACRO_PIN_DIMPLE = 5.0                    # how deep a pin dents the paper
MACRO_SHEEN = 0.08                        # the gloss of the ink under the light
MACRO_BODY_INK = 0.97                     # the ink of the body, against the ink of the word

# --- The camera --------------------------------------------------------------

# The paper is tilted: the left side is nearer to the lens, and so is the bottom
MACRO_YAW = 8                             # in degrees, around the vertical axis
MACRO_PITCH = 20                          # in degrees, around the horizontal axis
MACRO_ROLL = -6                             # in degrees, around the lens
MACRO_DISTANCE_MM = 110                   # from the lens to the word
MACRO_FOCAL_MM = 100                      # the macro lens
MACRO_F_NUMBER = 11                       # its aperture: the pupil is the focal length / this
MACRO_MAX_BLUR = 22                       # in pixels
MACRO_LIGHT = (-0.55, -0.62, 0.56)        # raking light, from the top left
MACRO_RELIEF = 1.10                       # how much the surface relief shades
MACRO_POOL = (0.38, 0.40)                 # the pool of light, of the size of the photograph
MACRO_POOL_SIZE = (0.52, 0.50)
MACRO_POOL_DARK = 0.55                    # the light far from the pool
MACRO_VIGNETTE = 0.14


# --- The dots ----------------------------------------------------------------


def read_dots(fonts_path, lines):
    """Read the dots of the lines of text from the fonts.

    Args:
        fonts_path: The folder of the fonts.
        lines: The lines, as (text, font file). The first is the word.

    Returns:
        The dots, as (x, y, diameter) in pixels, the pixels per millimeter, and
        the y where the bar ends.
    """
    scene_width, scene_height = MACRO_RENDER
    loaded = {}

    def load(file):
        if file not in loaded:
            font = TTFont(fonts_path / file)
            loaded[file] = (font["glyf"], font["hmtx"], font.getBestCmap())

        return loaded[file]

    # Pixels per font unit, so that the word spans its share of the photograph
    word, word_file = lines[0]
    glyf, hmtx, cmap = load(word_file)
    unit = MACRO_SPAN * MACRO_OUTPUT[0] / sum(hmtx[cmap[ord(c)]][0] for c in word)

    # The element of the font, a round dot, the same size in every font
    element = glyf["_"]
    diameter = (element.xMax - element.xMin) * unit

    # The lines start at the same x, and the baseline of the word is y = 0
    pitch = MACRO_LINE_ROWS * 204 * unit
    dots = []
    word_dots = []
    for index, (text, file) in enumerate(lines):
        glyf, hmtx, cmap = load(file)
        pen = 0
        for character in text:
            name = cmap[ord(character)]
            glyph = glyf[name]

            if glyph.isComposite():
                for component in glyph.components:
                    dot = (pen + component.x * unit, index * pitch - component.y * unit, diameter)
                    dots.append(dot)
                    if index == 0:
                        word_dots.append(dot)

            pen += hmtx[name][0] * unit

    # Center the ink of the word, not its advances or its rows: the last
    # character has spacing after it, and the capitals do not fill the rows
    left = min(x - d / 2 for x, _, d in word_dots)
    right = max(x + d / 2 for x, _, d in word_dots)
    top = min(y - d / 2 for _, y, d in word_dots)
    bottom = max(y + d / 2 for _, y, d in word_dots)
    shift_x = scene_width / 2 - (left + right) / 2
    shift_y = scene_height / 2 - (top + bottom) / 2
    dots = [(x + shift_x, y + shift_y, d) for x, y, d in dots]

    # The bar ends at the top of the line of the word
    edge = shift_y - MACRO_BAR_GAP_ROWS * 204 * unit

    return dots, diameter / DOT_MM, edge


# --- The paper ---------------------------------------------------------------


def smooth_noise(size, scale, rng):
    """Noise at 1/scale of the size, smoothly scaled up: -1 to 1."""
    small = (
        rng.random((max(size[1] // scale, 2), max(size[0] // scale, 2)), np.float32)
        * 255
    ).astype(np.uint8)
    big = Image.fromarray(small).resize(size, Image.BICUBIC)

    return np.asarray(big, np.float32) / 127.5 - 1


def fibers(size, rng, count, length, width, value, direction=None):
    """Draw random curved fibers: cellulose in the paper, nylon from the
    ribbon. The lengths and the widths are in pixels. Returns the layer, from
    0 to 1: how thick a fiber is there."""
    layer = Image.new("L", size, 0)
    draw = ImageDraw.Draw(layer)
    step = 6

    for _ in range(count):
        x = rng.uniform(0, size[0])
        y = rng.uniform(0, size[1])
        if direction is not None and rng.random() < 0.75:
            angle = direction + rng.normal(0, MACRO_FIBER_SPREAD)
        else:
            angle = rng.uniform(0, math.tau)
        bend = rng.normal(0, 0.012)
        fiber_length = rng.uniform(*length)
        points = [(x, y)]
        for _ in range(max(int(fiber_length / step), 2)):
            angle += bend + rng.normal(0, 0.035)
            x += step * math.cos(angle)
            y += step * math.sin(angle)
            points.append((x, y))

        draw.line(points, fill=int(rng.uniform(*value)),
                  width=max(int(round(rng.uniform(*width))), 1), joint="curve")

    return np.asarray(layer, np.float32) / 255


def paper_relief(size, rng, mm):
    """The paper surface: its fibers, its grain, its waviness. Returns the
    fibers (0 to 1, the ones on the surface), and the height of the surface in
    pixels."""
    surface = np.zeros((size[1], size[0]), np.float32)
    buried = np.zeros_like(surface)

    for count, length, width in MACRO_FIBERS:
        scaled = ((length[0] * mm, length[1] * mm), (width[0] * mm, width[1] * mm))
        surface = np.maximum(surface, fibers(size, rng, count, *scaled, (150, 255),
                                             MACRO_MACHINE_DIRECTION))
        buried = np.maximum(buried, fibers(size, rng, int(count * MACRO_BURIED), *scaled,
                                           (30, 95), MACRO_MACHINE_DIRECTION))

    def soften(array, radius):
        image = Image.fromarray((array * 255).clip(0, 255).astype(np.uint8))

        return np.asarray(image.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255

    # A fiber is a rounded ridge: softer than the line it was drawn with
    ridge = soften(surface, 1.6 * mm / 187)
    ridge_buried = soften(buried, 3.2 * mm / 187)

    height = (
        MACRO_FIBER_HEIGHT * ridge
        + 1.6 * MACRO_FIBER_HEIGHT * ridge_buried
        + 0.22 * smooth_noise(size, max(int(0.02 * mm), 2), rng)    # the filler of the sheet
        + 0.45 * smooth_noise(size, int(0.12 * mm), rng)
        + 1.30 * smooth_noise(size, int(1.2 * mm), rng)             # the formation of the sheet
        + 2.00 * smooth_noise(size, int(5.0 * mm), rng)
    )

    return np.clip(ridge * 1.2 + 0.5 * ridge_buried, 0, 1), height.astype(np.float32)


# --- The strike --------------------------------------------------------------


def strike(dots, fiber, rng, mm):
    """Strike the dots. Returns the ink laid on the paper (0 to 1), the
    dimples in the paper, and the ink that wicked into the fibers."""
    height, width = fiber.shape
    ink = np.zeros((height, width), np.float32)
    dimple = np.zeros((height, width), np.float32)

    for x, y, diameter in dots:
        radius = diameter / 2
        half = int(radius * 2.1)
        x0, y0 = int(round(x)) - half, int(round(y)) - half
        x1, y1 = x0 + 2 * half + 1, y0 + 2 * half + 1
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
            continue

        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = xs - x, ys - y
        rho = np.hypot(dx, dy)

        density, wick, pressure, _ = dot_ink(
            dx, dy, radius, rng, max(WEAVE_MM * mm, 3.0), fiber[y0:y1, x0:x1]
        )

        patch = ink[y0:y1, x0:x1]
        ink[y0:y1, x0:x1] = 1 - (1 - patch) * (1 - np.maximum(density, wick))

        # The paper is dented under the pin, and raised in a ring around it
        dent = np.exp(-((rho / (0.70 * radius)) ** 2))
        ring = np.exp(-(((rho - 1.12 * radius) / (0.22 * radius)) ** 2))
        dimple[y0:y1, x0:x1] += pressure * (-MACRO_PIN_DIMPLE * dent + 0.30 * MACRO_PIN_DIMPLE * ring)

    # Ink spatter: the ribbon throws specks around the strikes
    speck_layer = Image.new("L", (width, height), 0)
    speck_draw = ImageDraw.Draw(speck_layer)
    for _ in range(700):
        x_dot, y_dot, _ = dots[rng.integers(len(dots))]
        angle = rng.uniform(0, math.tau)
        distance = 0.9 * mm * math.sqrt(rng.random())
        x = x_dot + distance * math.cos(angle)
        y = y_dot + distance * math.sin(angle)
        r = rng.uniform(0.010, 0.034) * mm * rng.uniform(0.4, 1) ** 2
        speck_draw.ellipse(xy=[x - r, y - r, x + r, y + r], fill=int(rng.uniform(70, 230)))
    ink = np.maximum(ink, np.asarray(speck_layer, np.float32) / 255 * 0.8)

    return ink, dimple


# --- The light ---------------------------------------------------------------


def blur(array, radius):
    """Gaussian blur of a float image."""
    scale = 255 / max(float(array.max() - array.min()), 1e-6)
    low = float(array.min())
    image = Image.fromarray(((array - low) * scale).clip(0, 255).astype(np.uint8))
    image = image.filter(ImageFilter.GaussianBlur(radius))

    return np.asarray(image, np.float32) / scale + low


def light(relief, ink):
    """Light the surface: diffuse light from the side, shadow in the dimples,
    and the faint sheen of the ink. Returns the shade of the paper, the shade of
    the ink, and the sheen."""
    gradient_y, gradient_x = np.gradient(blur(relief, 0.7))
    normal = np.stack([-MACRO_RELIEF * gradient_x, -MACRO_RELIEF * gradient_y, np.ones_like(relief)])
    normal /= np.linalg.norm(normal, axis=0)

    light_vector = np.array(MACRO_LIGHT, np.float32)
    light_vector /= np.linalg.norm(light_vector)
    diffuse = np.clip(np.tensordot(light_vector, normal, axes=1), 0, None)
    diffuse /= light_vector[2]

    # Ambient light is occluded in the dimples
    occlusion = np.clip(blur(relief, 12) - relief, 0, None)
    occlusion = 1 - np.clip(occlusion * 0.10, 0, 0.45)

    shade = (0.30 + 0.70 * diffuse) * occlusion

    # The ink is matte, with a little sheen where the ribbon pressed it smooth
    half = light_vector + np.array([0, 0, 1], np.float32)
    half /= np.linalg.norm(half)
    sheen = np.clip(np.tensordot(half, normal, axes=1), 0, None) ** 14

    return shade, 0.62 * shade, sheen


# --- The camera --------------------------------------------------------------


def projection(mm):
    """The camera: the matrix that takes a point of the flat printout (in pixels
    from its center) to the photograph, the rotation of the paper, and the
    distance to its center, in pixels."""
    yaw, pitch, roll = (math.radians(a) for a in (MACRO_YAW, MACRO_PITCH, MACRO_ROLL))
    rotate_y = np.array([[math.cos(yaw), 0, math.sin(yaw)], [0, 1, 0],
                         [-math.sin(yaw), 0, math.cos(yaw)]])
    rotate_x = np.array([[1, 0, 0], [0, math.cos(pitch), -math.sin(pitch)],
                         [0, math.sin(pitch), math.cos(pitch)]])
    rotate_z = np.array([[math.cos(roll), -math.sin(roll), 0],
                         [math.sin(roll), math.cos(roll), 0], [0, 0, 1]])
    rotation = rotate_z @ rotate_x @ rotate_y

    distance = MACRO_DISTANCE_MM * mm
    focal = distance                    # the word is at scale 1
    cx, cy = MACRO_OUTPUT[0] * MACRO_WORD[0], MACRO_OUTPUT[1] * MACRO_WORD[1]
    r = rotation
    matrix = np.array([
        [focal * r[0, 0] - cx * r[2, 0], focal * r[0, 1] - cx * r[2, 1], cx * distance],
        [focal * r[1, 0] - cy * r[2, 0], focal * r[1, 1] - cy * r[2, 1], cy * distance],
        [-r[2, 0], -r[2, 1], distance],
    ])
    center = np.array([[1, 0, -MACRO_RENDER[0] / 2], [0, 1, -MACRO_RENDER[1] / 2], [0, 0, 1]])

    return matrix @ center, rotation, distance


def photograph(image, mm):
    """Lay the printout in front of the camera. Returns the photograph, and the
    blur of every pixel: how far its paper is from the plane of focus."""
    matrix, rotation, distance = projection(mm)
    inverse = np.linalg.inv(matrix)
    inverse /= inverse[2, 2]
    coefficients = (*inverse[0], *inverse[1], *inverse[2][:2])

    # The photograph, a channel at a time
    channels = []
    for channel in list(np.moveaxis(image, 2, 0)) + [np.ones(image.shape[:2], np.float32)]:
        warped = Image.fromarray(np.ascontiguousarray(channel, np.float32)).transform(
            MACRO_OUTPUT, Image.PERSPECTIVE, coefficients, Image.BICUBIC
        )
        channels.append(np.asarray(warped, np.float32))
    covered = channels.pop()
    if covered.min() < 0.999:
        print("warning: the tilted printout does not cover the photograph")
    photo = np.stack(channels, axis=2)

    # Where the paper is: the depth of every pixel, from the plane of focus
    ys, xs = np.mgrid[0 : MACRO_OUTPUT[1], 0 : MACRO_OUTPUT[0]].astype(np.float32)
    w = inverse[2, 0] * xs + inverse[2, 1] * ys + inverse[2, 2]
    x = (inverse[0, 0] * xs + inverse[0, 1] * ys + inverse[0, 2]) / w - MACRO_RENDER[0] / 2
    y = (inverse[1, 0] * xs + inverse[1, 1] * ys + inverse[1, 2]) / w - MACRO_RENDER[1] / 2
    depth = rotation[2, 0] * x + rotation[2, 1] * y

    # The blur of a lens: the circle of confusion grows with the distance from
    # the plane of focus, and shrinks with the distance from the lens. In pixels,
    # the pupil of the lens is its focal length over its f-number.
    pupil = MACRO_FOCAL_MM / MACRO_F_NUMBER * mm
    blur_radius = np.clip(
        0.5 * pupil * np.abs(depth) / (distance - depth), 0, MACRO_MAX_BLUR
    )

    return photo, blur_radius


def depth_of_field(image, radius):
    """Blur the image by the radius of every pixel."""
    levels = [0, 2.5, 5, 8.5, 12, 16, MACRO_MAX_BLUR]
    source = Image.fromarray((image * 255).clip(0, 255).astype(np.uint8))
    stack = [
        np.asarray(source.filter(ImageFilter.GaussianBlur(level)) if level else source,
                   np.float32) / 255
        for level in levels
    ]

    output = np.zeros_like(image)
    for low, high, a, b in zip(levels, levels[1:], stack, stack[1:]):
        weight = np.clip((radius - low) / (high - low), 0, 1)[..., None]
        inside = ((radius >= low) & (radius <= high))[..., None]
        output = np.where(inside, a * (1 - weight) + b * weight, output)

    return output


def camera(image, radius, rng):
    """The lens and the sensor: depth of field, a little chromatic aberration,
    the pool of light, vignetting, and the noise of the sensor."""
    height, width, _ = image.shape

    image = depth_of_field(image, radius)

    # Chromatic aberration: the red image is a little larger than the blue one
    margin = 0.0005
    red = Image.fromarray((image[..., 0] * 255).clip(0, 255).astype(np.uint8)).resize(
        (width, height),
        Image.BICUBIC,
        box=(width * margin, height * margin, width * (1 - margin), height * (1 - margin)),
    )
    image[..., 0] = np.asarray(red, np.float32) / 255

    # The raking light pools on the word and falls off toward the far corner
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    r2 = ((xs / width - MACRO_POOL[0]) / MACRO_POOL_SIZE[0]) ** 2 + (
        (ys / height - MACRO_POOL[1]) / MACRO_POOL_SIZE[1]
    ) ** 2
    pool = MACRO_POOL_DARK + (1 - MACRO_POOL_DARK) * np.exp(-r2)
    image *= (pool ** (1 / 2.2))[..., None]

    # A cool tint in the shadows
    shadow = np.clip(1 - image.mean(axis=2, keepdims=True), 0, 1) ** 2
    image += shadow * np.array([-0.012, 0.0, 0.020], np.float32)

    # Vignetting
    r = np.hypot((xs / width - 0.5) * 2, (ys / height - 0.5) * 2) / math.sqrt(2)
    image *= (1 - MACRO_VIGNETTE * r**2.2)[..., None]

    # Sensor noise: more in the shadows, and a little in color
    luma = image.mean(axis=2, keepdims=True)
    sigma = (0.004 + 0.010 * np.sqrt(np.clip(luma, 0, 1))) * 0.9
    image += rng.standard_normal(image.shape, np.float32) * sigma
    image += rng.standard_normal((height, width, 1), np.float32) * 0.003

    return image


# --- The picture -------------------------------------------------------------


def build_presentation(fonts_path, size, out_path):
    rng = np.random.default_rng(MACRO_SEED)
    width, height = MACRO_RENDER

    dots, mm, bar_end = read_dots(fonts_path, macro_lines())
    fiber, relief = paper_relief(MACRO_RENDER, rng, mm)

    # Dots and dimples
    ink, dimple = strike(dots, fiber, rng, mm)
    relief = relief + dimple

    # The lines are a line apart: the body is struck lighter than the word
    line = MACRO_LINE_ROWS * 204 * (mm * DOT_MM / ELEMENT_UNITS)
    rows = np.arange(height, dtype=np.float32)[:, None]
    body = np.clip((rows - (bar_end + line)) / (0.4 * line), 0, 1)
    ink = ink * (1 - (1 - MACRO_BODY_INK) * body)

    # The fold of the paper between two lines
    fold = bar_end + MACRO_FOLD_LINE * line + 2 * smooth_noise((width, 8), 400, rng)[0, :][None, :]
    ridge = np.exp(-(((rows - fold) / (MACRO_FOLD_MM * mm)) ** 2))
    relief = relief + MACRO_FOLD_HEIGHT * ridge * (0.85 + 0.15 * smooth_noise((width, 8), 90, rng)[0, :][None, :])

    # Greenbar: bars of three lines (half an inch) alternate with three white
    # lines, as in the specimens. The word is on the first white line, under a
    # green bar. The bars are printed in a screen.
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    wobble = 5 * smooth_noise(MACRO_RENDER, 120, rng)[0, :][None, :] + 2.2 * fiber
    band = MACRO_BAR_LINES * MACRO_LINE_ROWS * 204 * (mm * DOT_MM / ELEMENT_UNITS)
    phase = (ys + wobble - bar_end) % (2 * band)
    bar = np.clip((phase - band) / 3.0, 0, 1) * np.clip((2 * band - phase) / 3.0, 0, 1)
    screen_pitch = MACRO_BAR_SCREEN_MM * mm
    screen = 0.5 + 0.25 * (
        np.cos(math.tau * (xs + ys) / (screen_pitch * 1.414))
        + np.cos(math.tau * (xs - ys) / (screen_pitch * 1.414))
    )
    bar *= (0.78 + 0.22 * screen) * (0.92 + 0.10 * (fiber - 0.4))
    bar = np.clip(bar, 0, 1)[..., None]

    # The albedo, in linear light
    mottle = (
        1
        + 0.014 * smooth_noise(MACRO_RENDER, 22, rng)
        + 0.020 * smooth_noise(MACRO_RENDER, 340, rng)
        + 0.012 * (fiber - 0.4)
    )[..., None]
    paper = np.array(MACRO_PAPER, np.float32) * mottle
    bar_color = np.array(MACRO_BAR, np.float32)
    albedo = paper * (1 - bar + bar * bar_color)
    albedo = np.clip(albedo, 0, 1) ** 2.2

    # Light the paper and the ink
    shade, ink_shade, sheen = light(relief, ink)
    paper_lit = albedo * shade[..., None]
    ink_color = np.array(MACRO_INK, np.float32) ** 2.2 * ink_shade[..., None]
    image = paper_lit * (1 - ink[..., None]) + ink_color * ink[..., None]
    image += MACRO_SHEEN * (sheen * ink)[..., None] * np.array([0.95, 0.97, 1.0], np.float32)

    # Lint from the ribbon: nylon fibers on the paper near the strikes
    lint = fibers(MACRO_RENDER, rng, 16, (0.2 * mm, 0.9 * mm), (0.025 * mm, 0.040 * mm), (110, 200))
    near = np.zeros((height, width), np.float32)
    for x_dot, y_dot, _ in dots[::6]:
        near[int(max(y_dot - 260, 0)) : int(y_dot + 260), int(max(x_dot - 260, 0)) : int(x_dot + 260)] = 1
    lint = lint * near * 0.75
    image = image * (1 - lint[..., None]) + (ink_color * 1.4 + 0.012) * lint[..., None]

    # To the display, then the camera
    image = np.clip(image, 0, 1) ** (1 / 2.2)
    image, radius = photograph(image, mm)
    image = camera(image, radius, rng)

    # A gentle curve, and out
    image = np.clip(image, 0, 1)
    image = image * image * (3 - 2 * image) * 0.35 + image * 0.65
    picture = Image.fromarray((image * 255).astype(np.uint8))
    if size != MACRO_OUTPUT:
        picture = picture.resize(size, Image.LANCZOS)

    out_path.mkdir(parents=True, exist_ok=True)
    name = "DotMatrix-Presentation.jpg"
    picture.save(out_path / name, optimize=True, quality=JPG_QUALITY)
    print(name)


def main():
    parser = argparse.ArgumentParser(
        description="Builds the DotMatrix specimens and its presentation image."
    )
    parser.add_argument("--fonts", type=Path, default=FONTS_PATH,
                        help="the folder of the static .ttf fonts")
    parser.add_argument("--output", type=Path, default=OUT_PATH,
                        help="the folder of the images")
    parser.add_argument("--only", choices=["specimens", "presentation"],
                        help="build only the specimens, or only the presentation image")
    parser.add_argument("--width", type=int, default=1920,
                        help="the width of the presentation image; it is rendered at 3840")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    if args.only != "presentation":
        pages = [mono_page, sans_page, character_set_page]
        for number, page in enumerate(pages, start=1):
            build_page(page(args.fonts), f"DotMatrix-Sample{number}.jpg", args.output)

    if args.only != "specimens":
        build_presentation(
            args.fonts,
            (args.width, args.width * MACRO_OUTPUT[1] // MACRO_OUTPUT[0]),
            args.output,
        )


if __name__ == "__main__":
    main()
