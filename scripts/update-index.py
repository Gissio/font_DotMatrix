#!/usr/bin/env python3
# Updates the glyph table of the GitHub Pages glyph viewer (index.html) from
# the fonts. The table sits between the BEGIN GLYPHS and END GLYPHS markers;
# everything else in the page is edited by hand.
#
# Glyphs are ordered for finding, not by code point: letters by script and
# case, each base letter followed by its variants (accented, final, wide,
# turned, ...), then marks, numbers, symbols and text-mode graphics.
import argparse
import json
import os
import re
import urllib.parse

from fontTools import unicodedata as fontunicodedata
from fontTools.ttLib import TTFont

try:
    import unicodedata2 as unicodedata
except ImportError:
    import unicodedata

# Room around the widest glyph in a box of the page, in em
BOX_AIR = 0.25

SCRIPT_NAMES = {
    "Latn": "Latin",
    "Grek": "Greek",
    "Cyrl": "Cyrillic",
    "Hebr": "Hebrew",
}

# Scripts without case: their letters are one section, and their marks get
# their own section
UNICASE_SCRIPTS = {"Hebr"}

# First letter and last letter of each script's basic alphabet: base letters in
# these ranges come first, in code point order.
CORE_LETTERS = {
    "Latn": [(0x41, 0x5A), (0x61, 0x7A)],
    "Grek": [(0x391, 0x3A9), (0x3B1, 0x3C9)],
    "Cyrl": [(0x410, 0x42F), (0x430, 0x44F)],
    "Hebr": [(0x5D0, 0x5EA)],
}


def get_script_sections(script, script_name):
    if script in UNICASE_SCRIPTS:
        kinds = ("letters", "marks", "other")
    else:
        kinds = ("uppercase", "lowercase", "small capitals", "other")
    return [f"{script_name} {kind}" for kind in kinds]


# Sections in page order. Letter sections are added per script.
SECTIONS = [
    section
    for script, script_name in SCRIPT_NAMES.items()
    for section in get_script_sections(script, script_name)
] + [
    # Marks, from standalone to attached
    "Punctuation",
    "Modifier letters",
    "Combining marks",
    # Numbers and what goes with them
    "Numbers",
    "Math",
    "Currency",
    # Symbols used in text: each shares shapes with the next, and the
    # technical symbols lead into the graphics
    "Arrows",
    "Geometric shapes",
    "Enclosed",
    "Symbols",
    "Technical",
    # Text-mode graphics
    "Box drawing",
    "Block elements",
    "Sextants and octants",
    "Braille",
    "Legacy computing",
    # Nothing to see
    "Spaces and invisibles",
    "Other",
]

BLOCK_SECTIONS = {
    "Superscripts and Subscripts": "Numbers",
    "Number Forms": "Numbers",
    "Variation Selectors": "Spaces and invisibles",
    "Mathematical Operators": "Math",
    "Supplemental Mathematical Operators": "Math",
    "Miscellaneous Mathematical Symbols-A": "Math",
    "Miscellaneous Mathematical Symbols-B": "Math",
    "Mathematical Alphanumeric Symbols": "Math",
    "Arrows": "Arrows",
    "Supplemental Arrows-A": "Arrows",
    "Supplemental Arrows-B": "Arrows",
    "Supplemental Arrows-C": "Arrows",
    "Miscellaneous Technical": "Technical",
    "Control Pictures": "Technical",
    "Optical Character Recognition": "Technical",
    "Box Drawing": "Box drawing",
    "Block Elements": "Block elements",
    "Symbols for Legacy Computing": "Legacy computing",
    "Symbols for Legacy Computing Supplement": "Legacy computing",
    "Geometric Shapes": "Geometric shapes",
    "Geometric Shapes Extended": "Geometric shapes",
    "Miscellaneous Symbols and Arrows": "Geometric shapes",
    "Enclosed Alphanumerics": "Enclosed",
    "Enclosed Alphanumeric Supplement": "Enclosed",
    "Letterlike Symbols": "Symbols",
    "Miscellaneous Symbols": "Symbols",
    "Dingbats": "Symbols",
    "Miscellaneous Symbols and Pictographs": "Symbols",
    "Braille Patterns": "Braille",
}

# Name-derived variants sort after the accented ones
NAMED_VARIANT = 0x110000
DIGRAPH_VARIANT = 0x220000


def get_name(code):
    return unicodedata.name(chr(code), f"U+{code:04X}")


def get_script(char):
    """Returns the script code, with Coptic letters counted as Greek."""
    script = fontunicodedata.script(char)
    return "Grek" if script == "Copt" else script


def get_base(char, script):
    """Returns the base letter and a sort key of the variant: the combining
    marks of the decomposition, or pseudo marks for variants found by name
    (O WITH STROKE, TURNED A, digraph AE, FINAL KAF, WIDE ALEF)."""
    decomposition = unicodedata.normalize("NFD", char)
    if len(decomposition) > 1 and unicodedata.category(decomposition[0])[0] == "L":
        base, key = get_base(decomposition[0], script)
        return base, key + tuple(ord(mark) for mark in decomposition[1:])

    name = unicodedata.name(char, "")
    candidates = []
    match = re.fullmatch(r"HEBREW LETTER (?:FINAL|WIDE|ALTERNATIVE) (.+)", name)
    if match:
        candidates.append(("HEBREW LETTER " + match[1], NAMED_VARIANT))
    match = re.fullmatch(r"(\w+) (CAPITAL|SMALL) LETTER (.+?)(?: WITH .*)?", name)
    if match:
        prefix = f"{match[1]} {match[2]} LETTER "
        letter = match[3]
        candidates.append((prefix + letter, NAMED_VARIANT))
        if script in ("Latn", "Grek"):
            # TURNED A, SCRIPT G, CLOSED OPEN E, FINAL SIGMA
            candidates.append((prefix + letter.split(" ")[-1], NAMED_VARIANT))
        if script == "Latn" and re.fullmatch(r"[A-Z]{2}", letter):
            candidates.append((prefix + letter[0], DIGRAPH_VARIANT))
    for candidate, variant in candidates:
        try:
            base = unicodedata.lookup(candidate)
        except KeyError:
            continue
        if base != char:
            base, key = get_base(base, script)
            return base, key + (variant + ord(char),)
    return char, ()


def get_section(code):
    char = chr(code)
    category = unicodedata.category(char)
    block = fontunicodedata.block(char)
    script = get_script(char)
    name = get_name(code)
    script_name = SCRIPT_NAMES.get(script)

    if category[0] == "Z" or category == "Cf" or block == "Variation Selectors":
        return "Spaces and invisibles"
    if category == "Sc":
        return "Currency"
    if category[0] == "M":
        if script in UNICASE_SCRIPTS:
            return f"{script_name} marks"
        return "Combining marks"
    if code < 0x80:
        if category[0] == "L":
            return f"Latin {'uppercase' if category == 'Lu' else 'lowercase'}"
        if category == "Nd":
            return "Numbers"
        if category == "Sm":
            return "Math"
        return "Punctuation"
    # Not LATIN CAPITAL LETTER SMALL CAPITAL I, the uppercase of ɪ
    if "SMALL CAPITAL" in name and category == "Ll" and script_name:
        return f"{script_name} small capitals"
    # Ↄ ↄ in Number Forms are letters
    if block in BLOCK_SECTIONS and not (
        block == "Number Forms" and category[0] == "L"
    ):
        section = BLOCK_SECTIONS[block]
        if section == "Legacy computing" and re.match(
            r"BLOCK (SEXTANT|OCTANT)", name
        ):
            return "Sextants and octants"
        # Arrows and arrowheads among the shapes and dingbats
        if section in ("Geometric shapes", "Symbols") and re.search(
            r"\bARROW", name
        ):
            return "Arrows"
        # Circled digits among the dingbats, with the other circled numbers
        if block == "Dingbats" and re.search(r"CIRCLED.*\b(DIGIT|NUMBER)\b", name):
            return "Enclosed"
        return section
    if script in ("Cyrl", "Hebr") and category[0] != "L":
        return f"{script_name} other"
    if category in ("Lm", "Sk"):
        return "Modifier letters"
    if category[0] == "L":
        if not script_name:
            # MICRO SIGN
            return "Symbols"
        if script in UNICASE_SCRIPTS:
            return f"{script_name} letters"
        if category in ("Lu", "Lt"):
            return f"{script_name} uppercase"
        if category == "Ll":
            return f"{script_name} lowercase"
        return f"{script_name} other"
    if category[0] == "N":
        return "Numbers"
    if category[0] == "P":
        return "Punctuation"
    if category == "Sm":
        return "Math"
    if category == "So":
        return "Symbols"
    return "Other"


def get_sort_key(code, section):
    """Returns (group, key): a new group starts a run of related glyphs."""
    char = chr(code)
    category = unicodedata.category(char)
    name = get_name(code)
    if section.endswith("small capitals"):
        # Group by the letter: LATIN LETTER SMALL CAPITAL L WITH STROKE -> L
        letter = re.search(r"SMALL CAPITAL (?:LETTER )?(\S+)", name)[1]
        return (letter,), (" WITH " in name, code)
    if section.endswith(("uppercase", "lowercase", "letters")):
        script = get_script(char)
        base, key = get_base(char, script)
        base_code = ord(base)
        core = any(
            first <= base_code <= last
            for first, last in CORE_LETTERS.get(script, [])
        )
        # The base letter first, then its variants, the simpler ones first
        return (not core, base_code), (len(key),) + key + (code,)
    if section == "Hebrew marks":
        # The cantillation marks, then the points
        return ("ACCENT" not in name,), (code,)
    if section == "Sextants and octants":
        return ("OCTANT" in name,), (code,)
    if section == "Numbers":
        if 0x30 <= code <= 0x39:
            return (0,), (code,)
        if "FRACTION" in name or "VULGAR" in name:
            return (2,), (code,)
        if "ROMAN NUMERAL" in name:
            return (3,), (code,)
        return (1,), (code,)
    if section == "Punctuation":
        if "QUOTATION" in name or "APOSTROPHE" in name or category in ("Pi", "Pf"):
            return (3,), (code,)
        if category in ("Ps", "Pe"):
            return (2,), (code,)
        if category == "Pd" or "HYPHEN" in name or "DASH" in name:
            return (1,), (code,)
        return (0,), (code,)
    return (), (code,)


def get_cell_metrics(font):
    """Returns a font's cell metrics in em: the line, the highest and lowest
    ink, and the box width. A box has room for the widest ink, centered on its
    advance."""
    units_per_em = font["head"].unitsPerEm
    ascent = font["hhea"].ascent
    descent = -font["hhea"].descent

    top = ascent
    bottom = descent
    box = 0
    glyf = font["glyf"]
    for code, glyph_name in font.getBestCmap().items():
        advance = font["hmtx"][glyph_name][0]
        overhang = 0
        glyph = glyf[glyph_name]
        if glyph.numberOfContours:
            glyph.recalcBounds(glyf)
            top = max(top, glyph.yMax)
            bottom = max(bottom, -glyph.yMin)
            overhang = max(-glyph.xMin, glyph.xMax - advance, 0)
        # Combining marks are shown on a dotted circle
        if unicodedata.category(chr(code))[0] != "M":
            box = max(box, advance + 2 * overhang)

    return {
        "box": round(box / units_per_em + BOX_AIR, 4),
        "ascent": ascent / units_per_em,
        "descent": descent / units_per_em,
        "top": top / units_per_em,
        "bottom": bottom / units_per_em,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Updates the glyph table of the glyph viewer page."
    )
    parser.add_argument("html", help="the page to update")
    parser.add_argument(
        "--family",
        nargs=2,
        action="append",
        required=True,
        metavar=("NAME", "FONT"),
        help="a family name with its font",
    )
    args = parser.parse_args()

    html_dir = os.path.dirname(os.path.abspath(args.html))

    def get_url(path):
        relative = os.path.relpath(os.path.abspath(path), html_dir)
        return urllib.parse.quote(relative.replace(os.sep, "/"), safe="/,")

    families = []
    cmaps = []
    for name, path in args.family:
        font = TTFont(path)
        cmaps.append(set(font.getBestCmap()))
        families.append(
            {
                "name": name,
                "url": get_url(path),
                **get_cell_metrics(font),
            }
        )

    # Without the C0 and C1 controls
    sections = {section: [] for section in SECTIONS}
    for code in sorted(set().union(*cmaps)):
        if code >= 0x20 and not 0x7F <= code < 0xA0:
            sections[get_section(code)].append(code)

    # A glyph is [code, name], plus whether it starts a group and, when not
    # all families have it, a bit mask of the families that do
    all_families = (1 << len(cmaps)) - 1
    table = []
    for section, codes in sections.items():
        if not codes:
            continue
        glyphs = []
        previous_group = None
        for (group, _), code in sorted(
            (get_sort_key(code, section), code) for code in codes
        ):
            glyph = [code, get_name(code)]
            lead = int(bool(group) and group != previous_group)
            previous_group = group
            mask = sum(1 << i for i, cmap in enumerate(cmaps) if code in cmap)
            if lead or mask != all_families:
                glyph.append(lead)
            if mask != all_families:
                glyph.append(mask)
            glyphs.append(glyph)
        table.append([section, glyphs])

    data = (
        "const FAMILIES = "
        + json.dumps(families, ensure_ascii=False)
        + ";\nconst SECTIONS = [\n"
        + ",\n".join(
            json.dumps(section, ensure_ascii=False, separators=(",", ":"))
            for section in table
        )
        + "\n];\n"
    )

    with open(args.html, encoding="utf-8", newline="") as file:
        html = file.read()
    newline = "\r\n" if "\r\n" in html else "\n"
    begin = html.index("// BEGIN GLYPHS")
    begin = html.index("\n", begin) + 1
    end = html.index("// END GLYPHS")
    end = html.rindex("\n", 0, end) + 1
    html = html[:begin] + data.replace("\n", newline) + html[end:]
    title = " · ".join(family["name"] for family in families)
    html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", html, count=1)
    with open(args.html, "w", encoding="utf-8", newline="") as file:
        file.write(html)

    print(f"{args.html}: {sum(len(g) for _, g in table)} glyphs")


if __name__ == "__main__":
    main()
