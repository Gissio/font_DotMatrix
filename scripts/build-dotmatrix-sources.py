#!/usr/bin/env python3
# DotMatrix sources builder
#
# Builds, from the two base .bdf fonts (build/base/DotMatrix-Regular.bdf and
# build/base/DotMatrix-Italic.bdf, converted from the .kbitx sources), what
# gftools builder needs to make the fonts:
#
#   build/<family>-<Regular|Italic>.bdf   the .bdf font of each family
#   build/<font>/*.designspace, *.ufo     the bdf2ufo masters of each font
#   build/<font>/config.yaml              its gftools builder configuration
#
# Like the Epson FX-80, DotMatrix has no continuous controls: each font is one
# print mode. The modes are named by their width and by Emphasized. Elite, at 12
# cpi, is 0.6 em wide at 10 pt, as the common coding fonts are: it is the Normal
# width, and the plain DotMatrix Mono. The widths are ranks, as the width classes
# are:
#
#   Compressed (17.16 cpi)           DotMatrix Mono Condensed                 3
#   Elite (12 cpi)                   DotMatrix Mono                           5
#   Pica (10 cpi)                    DotMatrix Mono SemiExpanded              6
#   Emphasized Pica                  DotMatrix Mono Emphasized SemiExpanded   6
#   Expanded Compressed (8.58 cpi)   DotMatrix Mono Expanded                  7
#   Expanded Elite (6 cpi)           DotMatrix Mono ExtraExpanded             8
#   Expanded Pica (5 cpi)            DotMatrix Mono UltraExpanded             9
#   Emphasized Expanded Pica         DotMatrix Mono Emphasized UltraExpanded  9
#
# Each has a proportional version, DotMatrix Sans: DotMatrix Sans, DotMatrix
# Sans Condensed... The styles are Regular, Bold (double strike), Italic and
# Bold Italic. A font is a mode in a style.
#
# The Emphasized modes are not built (see BUILD_EMPHASIZED): Bold makes the
# text heavier. They can still be generated.
#
# (C) 2024-2026 Gissio
#
# License: MIT

import collections
import copy
import itertools
import logging
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import bdflib.model
import bdflib.reader
import bdflib.writer
import yaml

from bdf2ufo.bdf_font import BDFFont
from bdf2ufo.data import MARKS
from bdf2ufo.decomposition import build_decomposition
from bdf2ufo.designspace import DesignSpace

ROOT = Path(__file__).parent.parent
BUILD_DIR = ROOT / "build"
BASE_DIR = BUILD_DIR / "base"
COMMON_CONFIG = ROOT / "sources" / "DotMatrix-build-config.yaml"

# The width, in pixels, of a character cell in the base fonts
CELL_WIDTH = 12

# The height, in font units, of a row of dots: units per em / 10 pixels. At
# 10 pt, a row is 1/72 inch, the spacing of the 9 pins of the print head.
UNITS_PER_ELEMENT_Y = 204

# The width of a column of dots relative to a row: a Pica character has 12
# columns in 1/10 inch, so a column is 1/120 inch, and a row is 1/72 inch.
COLUMN_ASPECT = 72 / 120

# The advance, in font units, of a Pica character (10 cpi): 0.72 em at 10 pt
PICA_ADVANCE = CELL_WIDTH * COLUMN_ASPECT * UNITS_PER_ELEMENT_Y



# The pitches of the Epson FX-80 are 10 cpi (Pica), 12 cpi (Elite) and 17.16 cpi
# (Compressed). The geometry of a font is its width relative to Pica, which is
# 100: Elite is 10/12 as wide as Pica, and Compressed 10/17.16.
ELITE_WIDTH = 100 * 10 / 12
COMPRESSED_WIDTH = 100 * 10 / 17.16


@dataclass(frozen=True)
class Mode:
    """A print mode of the FX-80, which is a font.

    Attributes:
        width: The name of the width, which is "" for Normal (Elite).
        emphasized: Whether the mode is Emphasized.
        repeat: The number of times each dot is repeated: 1, 2 for Expanded or
            Emphasized, and 4 for Emphasized Expanded.
        scale: The width of the mode relative to the pitch of its dots (wdth of
            the design space): its geometry.
        wdth: The width the font reports (wdth of the user space), the nominal
            value of its width class, so that the name and the class agree.
    """

    width: str
    emphasized: bool
    repeat: int
    scale: float
    wdth: float

    def family_name(self, proportional):
        words = ["DotMatrix", "Sans" if proportional else "Mono"]
        if self.emphasized:
            words.append("Emphasized")
        if self.width:
            words.append(self.width)

        return " ".join(words)


# Emphasized Pica prints every dot twice at the pitch of Pica, so its dots are
# made as the dots of Expanded Pica at half the width
MODES = [
    Mode("Condensed", False, 1, COMPRESSED_WIDTH, 75),
    Mode("", False, 1, ELITE_WIDTH, 100),
    Mode("SemiExpanded", False, 1, 100, 112.5),
    Mode("SemiExpanded", True, 2, 50, 112.5),
    Mode("Expanded", False, 2, COMPRESSED_WIDTH, 125),
    Mode("ExtraExpanded", False, 2, ELITE_WIDTH, 150),
    Mode("UltraExpanded", False, 2, 100, 200),
    Mode("UltraExpanded", True, 4, 100, 200),
]

# Whether the Emphasized modes are built. They are not: Bold already makes the
# text heavier, and they would only cover two widths. Without them, the quad
# layout (repeat 4) is not built either. The random seeds are set by the
# layout, so the other fonts are the same either way.
BUILD_EMPHASIZED = False


# The weight (wght) of the regular and bold styles. The elements are 1.10 of a
# row, bigger than the pins of the printer (0.8 of a row), as the ink of the
# ribbon spreads. Regular then has the ink of the common coding fonts: 0.117 em
# squared per printable ASCII character, as JetBrains Mono (0.115) and DejaVu
# Sans Mono (0.117), between Consolas (0.101) and Cascadia Mono (0.127). The
# dots overlap in rows and columns, so the strokes are continuous, and diagonal
# neighbours all but touch. Bold adds a second strike, not bigger dots.
REGULAR_WEIGHT = 400
BOLD_WEIGHT = 700
ELEMENT_WEIGHT = 440

# The marks that are placed above or below the base letter
ANCHOR_NAMES = ("top", "bottom")

# The gftools builder configuration. Autohinting and flattening components
# would move the outlines off the pixel grid.
GFTOOLS_CONFIG = """sources:
  - {designspace}
outputDir: ../../fonts
autohintTTF: false
flattenComponents: false
buildVariable: false
"""


@dataclass(frozen=True)
class Layout:
    """How the dots of the fonts that share a .bdf font are laid out.

    Attributes:
        proportional: Whether the fonts are proportional (Sans) or monospace
            (Mono).
        repeat: The number of times each dot is repeated: 1, 2 or 4.
    """

    proportional: bool
    repeat: int

    @property
    def key(self):
        """The name of the .bdf font, without the style."""
        return f"DotMatrix{self.group}-x{self.repeat}"

    @property
    def name(self):
        return f"DotMatrix {self.group} x{self.repeat}"

    @property
    def group(self):
        """Sans for the proportional fonts, Mono for the monospace fonts."""
        return "Sans" if self.proportional else "Mono"

    @property
    def index(self):
        """The index of the layout, which sets the random seed: the fonts of a
        layout share the jitter of their dots."""
        return {1: 0, 2: 1, 4: 2}[self.repeat] + (3 if self.proportional else 0)

    @property
    def scale_x(self):
        """The horizontal scale of the .bdf font: Quad has two columns per dot."""
        return 2 if self.repeat == 4 else 1

    @property
    def monospace(self):
        """The advance, in pixels, of a monospace font, or 0."""
        return 0 if self.proportional else CELL_WIDTH * self.scale_x

    @property
    def units_per_element_x(self):
        """The width of an element: the repeated dots are twice as wide as Pica."""
        advance = PICA_ADVANCE * (1 if self.repeat == 1 else 2)
        return advance / (CELL_WIDTH * self.scale_x)

    @property
    def glyph_offset_x(self):
        """The dots of the double repeat are not centered in their pixel."""
        return 0 if self.repeat == 2 else 0.5


@dataclass(frozen=True)
class Style:
    """A DotMatrix style: Bold is the double-strike version of Regular."""

    key: str
    name: str
    italic: bool
    double_strike: bool

    @property
    def base(self):
        """The name of the style of the .bdf font that the style is made from."""
        return "Italic" if self.italic else "Regular"

    @property
    def weight(self):
        return BOLD_WEIGHT if self.double_strike else REGULAR_WEIGHT


LAYOUTS = [Layout(p, r) for p, r in itertools.product([False, True], [1, 2, 4])]

STYLES = [
    Style("Regular", "Regular", italic=False, double_strike=False),
    Style("Bold", "Bold", italic=False, double_strike=True),
    Style("Italic", "Italic", italic=True, double_strike=False),
    Style("BoldItalic", "Bold Italic", italic=True, double_strike=True),
]


# .bdf fonts


def derive_glyph(glyph, layout):
    """Derive a glyph of a layout from a glyph of the base font.

    Args:
        glyph: The glyph of the base font.
        layout: The layout.

    Returns:
        The bitmap rows, x offset, width and advance of the derived glyph.
    """
    if layout.proportional:
        offset_x = 0
        width = glyph.bbW + 3 if glyph.bbW != 0 else CELL_WIDTH
    else:
        offset_x = layout.scale_x * glyph.bbX
        width = CELL_WIDTH

    width *= layout.scale_x
    advance = width

    # Combining marks have no advance, so they stack on the preceding glyph:
    # they are drawn to the left of the origin
    if glyph.advance == 0:
        advance = 0
        if layout.proportional:
            offset_x = -width

    rows = []
    for y in range(glyph.bbH):
        row = 0
        for x in range(glyph.bbW):
            if glyph.data[y] & (1 << (glyph.bbW - 1 - x)):
                for i in range(layout.repeat):
                    # A repeated dot in the last column of the cell (the ends of
                    # the diagonals) is struck once: its repeats would fall in the
                    # next cell
                    shift = width - 1 - (layout.scale_x * x + i)
                    if shift >= 0:
                        row |= 1 << shift
        rows.append(row)

    return rows, offset_x, width, advance


def build_bdf(base, layout, base_style, path):
    """Write the .bdf font of a layout.

    Args:
        base: The base font, a bdflib font.
        layout: The layout.
        base_style: The style of the font: "Regular" or "Italic".
        path: The .bdf file to write.
    """
    font = bdflib.model.Font(path.stem.encode(), 10, 72, 72)

    for glyph in base.glyphs:
        rows, offset_x, width, advance = derive_glyph(glyph, layout)

        font.new_glyph_from_data(
            glyph.name,
            rows,
            offset_x,
            glyph.bbY,
            width,
            glyph.bbH,
            advance,
            glyph.codepoint,
        )

    # The version, copyright, foundry and vertical metrics are set in the .kbitx font
    for key in (b"FONT_VERSION", b"COPYRIGHT", b"FOUNDRY"):
        font.properties[key] = base.properties[key]

    font.properties[b"FAMILY_NAME"] = layout.name.encode()
    font.properties[b"STYLE_NAME"] = base_style.encode()
    font.properties[b"WEIGHT_NAME"] = b"Regular"
    font.properties[b"SLANT"] = b"I" if base_style == "Italic" else b""
    font.properties[b"FONT_ASCENT"] = base.properties[b"FONT_ASCENT"]
    font.properties[b"FONT_DESCENT"] = base.properties[b"FONT_DESCENT"]
    font.properties[b"CAP_HEIGHT"] = base.properties[b"CAP_HEIGHT"]
    font.properties[b"X_HEIGHT"] = base.properties[b"X_HEIGHT"]

    with open(path, "wb") as handle:
        bdflib.writer.write_bdf(font, handle)


# Mark anchors
#
# bdf2ufo places the anchors of a mark itself from the accented letters that
# are exactly a base letter plus the mark. In DotMatrix the accented capitals
# are redrawn (the body of the letter is squeezed to make room for the accent),
# so none of them is, and bdf2ufo is left with no anchors. The accent is found
# in the drawn letter instead: the mark bitmap is searched in the pixels at the
# top (or the bottom) of the letter.


def find_accent(glyph, mark, anchor_name):
    """Find where the accent of an accented letter is drawn.

    Args:
        glyph: The accented letter.
        mark: The combining mark.
        anchor_name: "top" or "bottom".

    Returns:
        The (x, y) position of the mark bitmap in the bitmap of the accented
        letter, or None if the accent is not found. The accent is the topmost
        (or the lowest) place of the letter where all pixels of the mark are
        set, at most one row off the top (or bottom) of the letter. It is not
        required to be above the base letter, as the accented capitals are
        drawn within the height of the capitals.
    """
    bitmap = glyph["bitmap"].astype(bool)
    mark_bitmap = mark["bitmap"].astype(bool)
    height, width = bitmap.shape
    mark_height, mark_width = mark_bitmap.shape

    best = None
    for y in range(height - mark_height + 1):
        if anchor_name == "top" and y + mark_height < height - 1:
            continue
        if anchor_name == "bottom" and y > 1:
            continue

        for x in range(width - mark_width + 1):
            if (mark_bitmap & ~bitmap[y : y + mark_height, x : x + mark_width]).any():
                continue

            # The topmost (or lowest) accent, the closest to the center
            score = (
                y if anchor_name == "top" else -y,
                -abs(x + mark_width / 2 - width / 2),
            )
            if best is None or score > best[0]:
                best = (score, (x, y))

    return None if best is None else best[1]


def find_accents(font, components):
    """Find the accents of the accented letters of a font.

    Args:
        font: The bdf2ufo font.
        components: The letters bdf2ufo composes itself.

    Returns:
        A list of (anchor name, mark character, base character, offset of the
        mark in the accented letter, position of the base anchor of the letter).
    """
    accents = []

    for glyph_name, glyph in font.glyphs.items():
        character = glyph["character"]

        if character is None or glyph_name in components:
            continue

        decomposition = unicodedata.decomposition(character).split()
        if len(decomposition) != 2 or decomposition[0].startswith("<"):
            continue

        base_character, mark_character = (chr(int(c, 16)) for c in decomposition)

        if (
            mark_character not in MARKS
            or MARKS[mark_character][0] not in ANCHOR_NAMES
            or base_character in MARKS
            or base_character not in font.names
            or mark_character not in font.names
        ):
            continue

        anchor_name = MARKS[mark_character][0]
        base = font.glyphs[font.names[base_character]]
        mark = font.glyphs[font.names[mark_character]]

        position = find_accent(glyph, mark, anchor_name)
        if position is None:
            continue

        # The offset of the mark within the accented letter
        offset = (
            glyph["offset"].x - mark["offset"].x + position[0],
            glyph["offset"].y - mark["offset"].y + position[1],
        )

        # The anchor of the base letter, which the anchor of the mark is placed
        # on: the center of the letter, and its top or bottom
        base_anchor = (
            base["offset"].x + base["bitmap"].shape[1] // 2,
            base["offset"].y + (base["bitmap"].shape[0] if anchor_name == "top" else 0),
        )

        accents.append(
            (anchor_name, mark_character, base_character, offset, base_anchor)
        )

    return accents


def most_common(values):
    return collections.Counter(values).most_common(1)[0][0]


def derive_mark_anchors(path):
    """Derive the bdf2ufo custom anchors of a .bdf font.

    A mark gets a "_top" or "_bottom" anchor, and each base letter a "top" or
    "bottom" anchor, so that the mark sits on the base letter like in the
    accented letters of the font. The accents of the font are not all drawn at
    the same place (the grave is one pixel to the right of the acute), so a mark
    takes the position it has most often, and a base letter the position that
    its marks have most often.

    Args:
        path: The .bdf file.

    Returns:
        A dictionary of custom anchors, keyed by character.
    """
    font = BDFFont()
    font.load(str(path), {})

    # The letters bdf2ufo composes itself get their anchors from their bitmap
    accents = find_accents(font, build_decomposition(font))

    # The anchor of each mark: where the mark sits on the center of its base
    # letters
    mark_positions = collections.defaultdict(list)
    for anchor_name, mark, _, (x, y), (base_x, base_y) in accents:
        mark_positions[anchor_name, mark].append((base_x - x, base_y - y))
    mark_anchors = {key: most_common(values) for key, values in mark_positions.items()}

    # The anchor of each base letter: where its marks sit
    base_positions = collections.defaultdict(list)
    for anchor_name, mark, base, (x, y), _ in accents:
        mark_x, mark_y = mark_anchors[anchor_name, mark]
        base_positions[anchor_name, base].append((mark_x + x, mark_y + y))
    base_anchors = {key: most_common(values) for key, values in base_positions.items()}

    custom_anchors = {}
    for prefix, anchors in (("_", mark_anchors), ("", base_anchors)):
        for (anchor_name, character), (x, y) in sorted(anchors.items()):
            custom_anchors.setdefault(character, {})[prefix + anchor_name] = [
                int(x),
                int(y),
            ]

    return custom_anchors


# bdf2ufo and gftools builder configurations


def font_key(family_name, style):
    """The name of a font, without spaces: DotMatrixMonoEmphasized-BoldItalic."""
    return f"{family_name.replace(' ', '')}-{style.key}"


def build_config(common, layout, mode, proportional, style, custom_anchors):
    """Build the bdf2ufo configuration of a font.

    Args:
        common: The configuration shared by all fonts.
        layout: The layout of its dots.
        mode: The print mode.
        proportional: Whether the font is proportional.
        style: The style.
        custom_anchors: The custom anchors of the .bdf font.

    Returns:
        The configuration, a dictionary.
    """
    config = copy.deepcopy(common)

    config["family_name"] = mode.family_name(proportional)
    config["style_name"] = style.name
    config["double_strike"] = style.double_strike
    config["random_seed"] = 2 * layout.index + (1 if style.italic else 0)
    config["units_per_element"] = [layout.units_per_element_x, UNITS_PER_ELEMENT_Y]
    config["glyph_offset"] = [layout.glyph_offset_x, 0]
    config["monospace"] = layout.monospace
    config["custom_anchors"] = custom_anchors

    # There are no variable axes. The weight (400 or 700) and the width (relative
    # to Pica) are what the font reports. They are mapped to the size of the
    # elements and to the width of the dots they are repeated from.
    config["default_axis_values"].update(wght=style.weight, wdth=mode.wdth)
    config["axis_maps"] = {
        "wght": {style.weight: ELEMENT_WEIGHT},
        "wdth": {mode.wdth: mode.scale},
    }

    # The only instance is the font itself
    config["variable_instances"] = {style.name: {}}

    return config


def build_designspace(config, bdf_path, output_dir):
    """Build the masters and the designspace of a font with bdf2ufo."""
    font = BDFFont()
    font.load(str(bdf_path), config)

    designspace = DesignSpace()
    designspace.setup(font, config)
    designspace.build(output_dir)


def main():
    # The accented letters that bdf2ufo cannot compose are expected: it stores
    # them as drawn
    logging.getLogger("bdf2ufo.decomposition").setLevel(logging.ERROR)

    with open(COMMON_CONFIG, "r", encoding="utf-8") as handle:
        common = yaml.safe_load(handle)

    base_fonts = {}
    for base_style in ("Regular", "Italic"):
        with open(BASE_DIR / f"DotMatrix-{base_style}.bdf", "rb") as handle:
            base_fonts[base_style] = bdflib.reader.read_bdf(handle)

    # Remove the fonts of earlier builds
    for font_dir in BUILD_DIR.glob("DotMatrix*"):
        if font_dir.is_dir():
            shutil.rmtree(font_dir)

    for layout in LAYOUTS:
        modes = [
            mode
            for mode in MODES
            if mode.repeat == layout.repeat and (BUILD_EMPHASIZED or not mode.emphasized)
        ]
        if not modes:
            continue

        anchors = {}

        for base_style, base in base_fonts.items():
            path = BUILD_DIR / f"{layout.key}-{base_style}.bdf"

            build_bdf(base, layout, base_style, path)
            anchors[base_style] = derive_mark_anchors(path)

        for mode, style in itertools.product(modes, STYLES):
            family_name = mode.family_name(layout.proportional)
            key = font_key(family_name, style)
            font_dir = BUILD_DIR / key

            config = build_config(
                common, layout, mode, layout.proportional, style, anchors[style.base]
            )
            build_designspace(
                config, BUILD_DIR / f"{layout.key}-{style.base}.bdf", font_dir
            )

            # bdf2ufo names the designspace after the family
            with open(font_dir / "config.yaml", "w", encoding="utf-8") as handle:
                handle.write(
                    GFTOOLS_CONFIG.format(
                        designspace=f"{family_name.replace(' ', '')}.designspace"
                    )
                )

            print(key)


if __name__ == "__main__":
    main()
