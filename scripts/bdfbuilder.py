# DotMatrix .bdf builder
#
# (C) 2024-2025 Gissio
#
# License: MIT
#

import bdflib
import bdflib.model
import bdflib.reader
import bdflib.writer
import numpy as np


def build_font(source_path, style_name):
    with open(source_path, 'rb') as handle:
        source_bdf = bdflib.reader.read_bdf(handle)

        for proportional in [False, True]:
            for repeat in [1, 2, 4]:
                family_name = ''

                if proportional:
                    family_name += 'Var'

                if repeat == 1:
                    scale_x = 1
                elif repeat == 2:
                    family_name += 'Duo'
                    scale_x = 1
                elif repeat == 4:
                    family_name += 'Quad'
                    scale_x = 2

                if family_name != '':
                    family_name = ' ' + family_name
                family_name = 'DotMatrix' + family_name

                file_name = (family_name + '-' + style_name).replace(' ', '')

                dest_bdf = bdflib.model.Font(
                    file_name.encode(), 10, 72, 72)

                for source_glyph in source_bdf.glyphs:
                    if not proportional:
                        dest_bbX = scale_x * source_glyph.bbX
                        width = 12

                    else:
                        dest_bbX = 0
                        if source_glyph.bbW != 0:
                            width = source_glyph.bbW + 3
                        else:
                            width = 12

                    dest_data = []
                    dest_bbW = scale_x * width

                    for y in range(source_glyph.bbH):
                        source_row = source_glyph.data[y]
                        dest_row = 0

                        for x in range(source_glyph.bbW):
                            source_index = (source_glyph.bbW - 1) - x
                            if source_row & (1 << source_index):
                                for i in range(repeat):
                                    dest_row |= 1 << ((dest_bbW - 1) - (scale_x * x + i))

                        dest_data.append(dest_row)

                    dest_bdf.new_glyph_from_data(
                        source_glyph.name,
                        dest_data,
                        dest_bbX, source_glyph.bbY,
                        dest_bbW, source_glyph.bbH,
                        dest_bbW,
                        source_glyph.codepoint)

                    dest_bdf.properties[b'FONT_VERSION'] = b'1.000'
                    dest_bdf.properties[b'COPYRIGHT'] =\
                        b'Copyright 2025 The DotMatrix Project Authors (https://github.com/Gissio/font_DotMatrix)'
                    dest_bdf.properties[b'FOUNDRY'] = b'Stefan Schmidt Art'
                    dest_bdf.properties[b'FAMILY_NAME'] = family_name.encode()
                    dest_bdf.properties[b'STYLE_NAME'] = style_name.encode()
                    dest_bdf.properties[b'WEIGHT_NAME'] = b'Regular'
                    dest_bdf.properties[b'SLANT'] = b'I' if style_name == 'Italic' else b''

                    dest_bdf.properties[b'FONT_ASCENT'] = 8
                    dest_bdf.properties[b'FONT_DESCENT'] = 2
                    dest_bdf.properties[b'CAP_HEIGHT'] = 7
                    dest_bdf.properties[b'X_HEIGHT'] = 5

                    with open('build/' + file_name + '.bdf', 'wb') as handle:
                        bdflib.writer.write_bdf(dest_bdf, handle)


build_font('sources/DotMatrix-Regular.bdf', 'Regular')
build_font('sources/DotMatrix-Italic.bdf', 'Italic')
