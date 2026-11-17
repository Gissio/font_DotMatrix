.DEFAULT_GOAL := help

# The .bdf fonts converted from the .kbitx sources, which the .bdf fonts of the
# families are built from
build/base/%.bdf: venv sources/%.kbitx
	mkdir -p build/base
	. venv/bin/activate; python3 scripts/kbitx2bdf.py "sources/$*.kbitx" "build/base/$*.bdf"

# The .bdf fonts of the dot layouts (single, double, quad, Prop...), and the masters and the
# gftools builder configuration of each font, made from the base .bdf fonts
build/sources.stamp: venv build/base/DotMatrix-Regular.bdf build/base/DotMatrix-Italic.bdf sources/DotMatrix-build-config.yaml scripts/build-dotmatrix-sources.py
	. venv/bin/activate; python3 scripts/build-dotmatrix-sources.py
	touch build/sources.stamp

# The glyph table of the glyph viewer (the GitHub Pages site)
index.html: venv build.stamp scripts/update-index.py
	. venv/bin/activate; python3 scripts/update-index.py index.html --family "DotMatrix" "fonts/webfonts/DotMatrix-Regular.woff2"

help:
	@echo "###"
	@echo "# Build targets for DotMatrix"
	@echo "###"
	@echo
	@echo "  make build:  Builds the fonts and places them in the fonts/ directory, and updates index.html"
	@echo "  make test:   Tests the fonts with fontspector"
	@echo "  make images: Builds the specimen images in the documentation/ directory"
	@echo "  make clean:  Removes the venv and the generated files"
	@echo

build: build.stamp index.html

images: venv build.stamp
	. venv/bin/activate; python3 documentation/build-specimen.py

venv: venv/touchfile

build.stamp: venv build/sources.stamp
	rm -rf fonts
	(for config in build/*/config.yaml; do . venv/bin/activate; env -u MAKEFLAGS gftools builder $$config || exit 1; done) && touch build.stamp

venv/touchfile: requirements.txt
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

test: build.stamp
	which fontspector || (echo "fontspector not found. Please install it with 'cargo install fontspector'." && exit 1)
	mkdir -p out/ out/fontspector; fontspector --profile googlefonts -l warn --full-lists --succinct --html out/fontspector/fontspector-report.html --ghmarkdown out/fontspector/fontspector-report.md --badges out/badges fonts/ttf/*.ttf  || echo '::warning file=sources/DotMatrix-build-config.yaml,title=fontspector failures::The fontspector QA check reported errors in your font. Please check the generated report.'

clean:
	rm -rf venv
	rm -rf build
	rm -rf build.stamp
	rm -rf fonts
	find . -name "*.pyc" -delete

.PHONY: help build images test clean
