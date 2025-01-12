#!/bin/bash
if [ ! -d env ] ; then
  python -m venv env
  source env/bin/activate
  pip install -r requirements.txt
else
  source env/bin/activate
fi

# Build derived .bdf files
[ -d build ] || mkdir build
python scripts/bdfbuilder.py

# Variables
COMMON=('-v' '--designer' 'Stefan Schmidt' '--designer-url' 'https://github.com/Gissio/font_DotMatrix' '--manufacturer' 'Stefan Schmidt Art' '--manufacturer-url' 'https://www.stefanschmidtart.com/' '--license' 'This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org' '--license-url' 'https://openfontlicense.org' '--strikeout-position' '3' '--strikeout-thickness' '1' '--underline-position' '-1' '--underline-thickness' '1' '--superscript-scale-x' '1' '--superscript-scale-y' '0.5' '--superscript-offset-x' '0' '--superscript-offset-y' '4' '--subscript-scale-x' '1' '--subscript-scale-y' '0.5' '--subscript-offset-x' '0' '--subscript-offset-y' '0' '--notdef-codepoint' '0x0' '--axes-limits' 'XESP=0.5-1.2' '--variable-axes' 'ESIZ,XESP' '--static-axes' 'ROND=1,EJIT=0.05')

# Monospace single
COMMON_VAR=("${COMMON[@]}" '--family-name' 'DotMatrix' '--glyph-scale-x' '0.5' '--glyph-offset-x' '0.5' '--variable-instance' ',ESIZ=0.8,XESP=1' '--variable-instance' 'Expanded,ESIZ=0.8,XESP=1.2' '--variable-instance' 'Condensed,ESIZ=0.8,XESP=0.58275')

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Regular" --random-seed 0 build/DotMatrix-Regular.bdf build
gftools builder build/DotMatrix-Regular-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold" --random-seed 0 --double-strike build/DotMatrix-Regular.bdf build
gftools builder build/DotMatrix-Bold-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Italic" --random-seed 1 build/DotMatrix-Italic.bdf build
gftools builder build/DotMatrix-Italic-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold Italic" --random-seed 1 --double-strike build/DotMatrix-Italic.bdf build
gftools builder build/DotMatrix-BoldItalic-config.yaml

# Monospace duo
COMMON_VAR=("${COMMON[@]}" '--family-name' 'DotMatrix Duo' '--glyph-scale-x' '1' '--glyph-offset-x' '0' '--variable-instance' ',ESIZ=0.8,XESP=1' '--variable-instance' 'Expanded,ESIZ=0.8,XESP=1.2' '--variable-instance' 'Condensed,ESIZ=0.8,XESP=0.58275' '--variable-instance' 'UltraCondensed,ESIZ=0.8,XESP=0.5')

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Regular" --random-seed 2 build/DotMatrixDuo-Regular.bdf build
gftools builder build/DotMatrixDuo-Regular-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold" --random-seed 2 --double-strike build/DotMatrixDuo-Regular.bdf build
gftools builder build/DotMatrixDuo-Bold-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Italic" --random-seed 3 build/DotMatrixDuo-Italic.bdf build
gftools builder build/DotMatrixDuo-Italic-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold Italic" --random-seed 3 --double-strike build/DotMatrixDuo-Italic.bdf build
gftools builder build/DotMatrixDuo-BoldItalic-config.yaml

# Monospace quad
COMMON_VAR=("${COMMON[@]}" '--family-name' 'DotMatrix Quad' '--glyph-scale-x' '0.5' '--glyph-offset-x' '0.5' '--variable-instance' ',ESIZ=0.8,XESP=1')

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Regular" --random-seed 4 build/DotMatrixQuad-Regular.bdf build
gftools builder build/DotMatrixQuad-Regular-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold" --random-seed 4 --double-strike build/DotMatrixQuad-Regular.bdf build
gftools builder build/DotMatrixQuad-Bold-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Italic" --random-seed 5 build/DotMatrixQuad-Italic.bdf build
gftools builder build/DotMatrixQuad-Italic-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold Italic" --random-seed 5 --double-strike build/DotMatrixQuad-Italic.bdf build
gftools builder build/DotMatrixQuad-BoldItalic-config.yaml

# Var single
COMMON_VAR=("${COMMON[@]}" '--family-name' 'DotMatrix Var' '--glyph-scale-x' '0.5' '--glyph-offset-x' '0.5' '--variable-instance' ',ESIZ=0.8,XESP=1' '--variable-instance' 'Expanded,ESIZ=0.8,XESP=1.2' '--variable-instance' 'Condensed,ESIZ=0.8,XESP=0.58275')

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Regular" --random-seed 6 build/DotMatrixVar-Regular.bdf build
gftools builder build/DotMatrixVar-Regular-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold" --random-seed 6 --double-strike build/DotMatrixVar-Regular.bdf build
gftools builder build/DotMatrixVar-Bold-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Italic" --random-seed 7 build/DotMatrixVar-Italic.bdf build
gftools builder build/DotMatrixVar-Italic-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold Italic" --random-seed 7 --double-strike build/DotMatrixVar-Italic.bdf build
gftools builder build/DotMatrixVar-BoldItalic-config.yaml

# Var duo
COMMON_VAR=("${COMMON[@]}" '--family-name' 'DotMatrix VarDuo' '--glyph-scale-x' '1' '--glyph-offset-x' '0' '--variable-instance' ',ESIZ=0.8,XESP=1' '--variable-instance' 'Expanded,ESIZ=0.8,XESP=1.2' '--variable-instance' 'Condensed,ESIZ=0.8,XESP=0.58275' '--variable-instance' 'UltraCondensed,ESIZ=0.8,XESP=0.5')

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Regular" --random-seed 8 build/DotMatrixVarDuo-Regular.bdf build
gftools builder build/DotMatrixVarDuo-Regular-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold" --random-seed 8 --double-strike build/DotMatrixVarDuo-Regular.bdf build
gftools builder build/DotMatrixVarDuo-Bold-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Italic" --random-seed 9 build/DotMatrixVarDuo-Italic.bdf build
gftools builder build/DotMatrixVarDuo-Italic-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold Italic" --random-seed 9 --double-strike build/DotMatrixVarDuo-Italic.bdf build
gftools builder build/DotMatrixVarDuo-BoldItalic-config.yaml

# Var quad
COMMON_VAR=("${COMMON[@]}" '--family-name' 'DotMatrix VarQuad' '--glyph-scale-x' '0.5' '--glyph-offset-x' '0.5' '--variable-instance' ',ESIZ=0.8,XESP=1')

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Regular" --random-seed 10 build/DotMatrixVarQuad-Regular.bdf build
gftools builder build/DotMatrixVarQuad-Regular-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold" --random-seed 10 --double-strike build/DotMatrixVarQuad-Regular.bdf build
gftools builder build/DotMatrixVarQuad-Bold-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Italic" --random-seed 11 build/DotMatrixVarQuad-Italic.bdf build
gftools builder build/DotMatrixVarQuad-Italic-config.yaml

python scripts/bdf2ufo.py "${COMMON_VAR[@]}" --style-name "Bold Italic" --random-seed 11 --double-strike build/DotMatrixVarQuad-Italic.bdf build
gftools builder build/DotMatrixVarQuad-BoldItalic-config.yaml
