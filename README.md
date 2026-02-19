# dwg2pdf

Command-line tool to convert DWG and DXF files to PDF.

- **DWG input:** LibreDWG (`dwg2dxf`) → ezdxf + PyMuPDF → PDF
- **DXF input:** ezdxf + PyMuPDF → PDF (skips DWG conversion)

## Usage

```
dwg2pdf input.dwg output.pdf
dwg2pdf input.dxf output.pdf
dwg2pdf input.dwg output.pdf --margin 10
dwg2pdf input.dwg output.pdf --color source
dwg2pdf input.dwg output.pdf --background none
```

### Options

| Flag | Description | Default |
|---|---|---|
| `--margin MM` | Page margin in millimeters | `5` |
| `--color {source,black}` | `source` preserves original colors, `black` renders all in black | `black` |
| `--background {white,none}` | `white` adds white background, `none` for transparent | `white` |

## Building from source

Windows only. Requires Python 3.10+.

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
build.bat
```

The built executable will be in `dist\dwg2pdf.exe`.

For DWG input, place `dwg2dxf.exe` and `libredwg-0.dll` from [GNU LibreDWG](https://www.gnu.org/software/libredwg/) alongside the executable. These are only needed for DWG files — DXF input works without them.

## Third-party components

This project includes binaries from [GNU LibreDWG](https://www.gnu.org/software/libredwg/) (`dwg2dxf.exe`, `libredwg-0.dll`), licensed under GPL-3.0-or-later. Source code: https://github.com/LibreDWG/libredwg

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
