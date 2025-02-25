![Presentation](documentation/DotMatrix-Presentation.png)

# DotMatrix

**DotMatrix** is a font inspired by the dot matrix printers of the 1980s, capturing the essence of the printing technologies from that era. It's perfect for evoking a retro or nostalgic feel, rendering ASCII/ANSI art, or use within code editors. For true scale, use **10 point text**.

## Features

* **Character Set**: Includes 537 characters featuring the full set from the Epson FX-80 printer, DOS code page 437, Google Fonts Latin Core, Greek Core, Cyrillic Core, and Hebrew. Note, the italic subset is limited to 191 characters due to historical constraints.

* **Dot Jitter**: Simulates the inaccuracy of the printing head for an authentic look.

* **Epson FX-80 Modes**: Mapped to different DotMatrix font families:
  
  |Epson FX-80 Mode|DotMatrix Font Family|
  |------------|---|
  |Pica|DotMatrix|
  |Elite|DotMatrix Expanded|
  |Compressed|DotMatrix Condensed|
  |Expanded Pica|DotMatrix Duo|
  |Expanded Elite|DotMatrix Duo Expanded|
  |Expanded Compressed|DotMatrix Duo Condensed|
  |Emphasized Pica| DotMatrix Duo UltraCondensed|
  |Emphasized Expanded Pica|DotMatrix Quad|

  * **"Double-strike"** is represented by the **Bold** style.
  * **"Italic"** corresponds to the **Italic** style.
  * **"Proportional mode"** is mapped to the respective **Var** font families.

* **Variable Font Axes**:
  * **Element Size**: Adjusts the dot strength.
  * **Horizontal Element Spacing**: Modifies the font width.

## Samples

![Sample 1](documentation/DotMatrix-Sample1.png)

![Sample 2](documentation/DotMatrix-Sample2.png)

![Sample 3](documentation/DotMatrix-Sample3.png)

![Sample 4](documentation/DotMatrix-Sample4.png)

# Releases

## 1.000

* First release.

## Build

Ensure you have Python 3.10 or newer, pip, and virtualenv installed. Then, execute:

    ./build.sh

## Designer profile

Stefan Schmidt is an electrical engineer with graduate studies in signal processing, combined artistic languages and sociology. Fascinated by the interplay between the virtual and the real, his work probes the boundaries between perception and technology.

Learn more at [http://www.stefanschmidtart.com](http://www.stefanschmidtart.com).

## License

This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://scripts.sil.org/OFL
