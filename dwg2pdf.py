# dwg2pdf - DWG/DXF to PDF converter
# Copyright (C) 2026 Invest It Sp. z o.o.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
dwg2pdf - DWG/DXF to PDF converter.

Converts DWG or DXF files to PDF:
  - DWG input: dwg2dxf.exe (LibreDWG) -> ezdxf + PyMuPDF -> PDF
  - DXF input: ezdxf + PyMuPDF -> PDF (skips DWG conversion)

External tools (dwg2dxf.exe, libredwg-0.dll) are part of GNU LibreDWG,
licensed under GPL-3.0-or-later. Source code is available at:
  https://www.gnu.org/software/libredwg/
  https://github.com/LibreDWG/libredwg
These files must reside in the same directory as this executable.
Only required for DWG input.

Usage:
    dwg2pdf input.dwg output.pdf
    dwg2pdf input.dxf output.pdf
    dwg2pdf input.dwg output.pdf --margin 5
    dwg2pdf input.dwg output.pdf --color black
"""

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

__version__ = "3.0.0"

EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 1
EXIT_TOOL_MISSING = 2
EXIT_DWG2DXF_ERROR = 3
EXIT_DXF2PDF_ERROR = 4

SUPPORTED_EXTENSIONS = {".dwg", ".dxf"}


def get_exe_dir() -> Path:
    """Return the directory where this executable (or script) lives.

    Handles: plain Python, PyInstaller (--onefile), Nuitka (--onefile).
    In Nuitka onefile, only sys.argv[0] points to the real exe location.
    """
    exe_from_argv = Path(sys.argv[0]).resolve()
    if exe_from_argv.suffix.lower() == ".exe":
        return exe_from_argv.parent
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def find_tool(name: str, exe_dir: Path) -> Path:
    """Find an external tool in the exe directory."""
    tool = exe_dir / name
    if not tool.exists():
        raise FileNotFoundError(
            f"Required tool not found: {tool}\n"
            f"Place {name} in the same directory as dwg2pdf."
        )
    return tool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dwg2pdf",
        description="Convert DWG/DXF files to PDF format.",
        epilog="Example: dwg2pdf drawing.dwg output.pdf --margin 10",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the input file (.dwg or .dxf).",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Path for the output PDF file.",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=5.0,
        metavar="MM",
        help="Page margin in millimeters (default: 5).",
    )
    parser.add_argument(
        "--color",
        choices=["source", "black"],
        default="black",
        help='Color policy: "source" preserves original colors, '
        '"black" renders all entities in black (default: black).',
    )
    parser.add_argument(
        "--background",
        choices=["white", "none"],
        default="white",
        help='Background: "white" adds a white background, '
        '"none" for transparent (default: white).',
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(argv)


def _repair_truncated_dxf(dxf_path: Path) -> bool:
    """Attempt to repair a truncated DXF by adding ENDSEC + EOF.

    Returns True if the file was repaired.
    """
    with open(dxf_path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="surrogateescape")
    if text.rstrip().endswith("EOF"):
        return False

    lines = text.split("\n")
    ENTITY_TYPES = frozenset((
        "LINE", "ARC", "CIRCLE", "LWPOLYLINE", "POLYLINE", "INSERT",
        "MTEXT", "TEXT", "DIMENSION", "HATCH", "SPLINE", "ELLIPSE",
        "SOLID", "POINT", "ATTRIB", "ATTDEF", "BLOCK", "ENDBLK",
        "VIEWPORT", "LEADER", "MLINE", "3DFACE", "TRACE", "SEQEND",
    ))
    cut_at = -1
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].strip() == "0" and i + 1 < len(lines):
            if lines[i + 1].strip() in ENTITY_TYPES:
                cut_at = i
                break
    if cut_at < 0:
        return False

    repaired = "\n".join(lines[:cut_at])
    repaired += "\n  0\nENDSEC\n  0\nEOF\n"
    with open(dxf_path, "wb") as f:
        f.write(repaired.encode("utf-8", errors="surrogateescape"))
    return True


def step_dwg_to_dxf(
    dwg_path: Path, dxf_path: Path, dwg2dxf_exe: Path
) -> None:
    """Convert DWG to DXF using LibreDWG's dwg2dxf."""
    result = subprocess.run(
        [str(dwg2dxf_exe), str(dwg_path), "-o", str(dxf_path), "-y"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        if dxf_path.exists() and dxf_path.stat().st_size > 0:
            if _repair_truncated_dxf(dxf_path):
                print("CRASHED (partial DXF recovered)", end=" ", flush=True)
                return
        stderr = result.stderr.strip() if result.stderr else "unknown error"
        raise RuntimeError(f"dwg2dxf failed (exit {result.returncode}): {stderr}")
    if not dxf_path.exists() or dxf_path.stat().st_size == 0:
        raise RuntimeError("dwg2dxf produced no output.")


def _patch_ezdxf_unicode_decoder() -> None:
    """Patch ezdxf to handle broken \\U+XXXX sequences from LibreDWG.

    LibreDWG's dwg2dxf sometimes splits Unicode escape sequences across
    DXF group boundaries (e.g. '\\U+\\n  3\\n0142' instead of '\\U+0142').
    The stock ezdxf decoder crashes with 'invalid literal for int()'.
    This patch makes it return the raw text instead of crashing.
    """
    from ezdxf.lldxf import encoding

    original_decode = encoding._decode

    def _safe_decode(s: str) -> str:
        try:
            return original_decode(s)
        except (ValueError, IndexError):
            return s

    encoding._decode = _safe_decode


def step_dxf_to_pdf(
    dxf_path: Path,
    pdf_path: Path,
    margin_mm: float,
    color_policy: str,
    background: str,
) -> None:
    """Convert DXF to PDF using ezdxf + PyMuPDF backend."""
    _patch_ezdxf_unicode_decoder()
    from ezdxf import recover
    from ezdxf.addons.drawing import Frontend, RenderContext, layout
    from ezdxf.addons.drawing.config import (
        BackgroundPolicy,
        ColorPolicy,
        Configuration,
    )
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
    from ezdxf.bbox import Cache as BBoxCache

    doc, auditor = recover.readfile(str(dxf_path))
    msp = doc.modelspace()

    if len(msp) == 0:
        raise ValueError("DXF file contains no entities in modelspace.")

    cfg = Configuration(
        background_policy=(
            BackgroundPolicy.WHITE
            if background == "white"
            else BackgroundPolicy.OFF
        ),
        color_policy=(
            ColorPolicy.BLACK if color_policy == "black" else ColorPolicy.COLOR
        ),
    )

    backend = PyMuPdfBackend()
    bbox_cache = BBoxCache()
    Frontend(
        RenderContext(doc), backend, config=cfg, bbox_cache=bbox_cache
    ).draw_layout(msp)

    page = layout.Page(0, 0, layout.Units.mm, layout.Margins.all(margin_mm))
    pdf_bytes = backend.get_pdf_bytes(page)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(pdf_bytes)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    input_path: Path = args.input.resolve()
    output_path: Path = args.output.resolve()

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    input_ext = input_path.suffix.lower()
    if input_ext not in SUPPORTED_EXTENSIONS:
        print(
            f"Error: Unsupported format '{input_ext}'. Expected .dwg or .dxf",
            file=sys.stderr,
        )
        return EXIT_INPUT_ERROR

    is_dwg = input_ext == ".dwg"
    total_steps = 2 if is_dwg else 1
    t_total = time.perf_counter()

    if is_dwg:
        # Locate dwg2dxf tool (only needed for DWG input)
        exe_dir = get_exe_dir()
        try:
            dwg2dxf_exe = find_tool("dwg2dxf.exe", exe_dir)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return EXIT_TOOL_MISSING

        with tempfile.TemporaryDirectory(prefix="dwg2pdf_") as tmp:
            dxf_path = Path(tmp) / f"{input_path.stem}.dxf"

            # Step 1: DWG -> DXF
            print(f"[1/{total_steps}] DWG -> DXF ...", end=" ", flush=True)
            t0 = time.perf_counter()
            try:
                step_dwg_to_dxf(input_path, dxf_path, dwg2dxf_exe)
            except Exception as e:
                print("FAILED", file=sys.stderr)
                print(f"Error: {e}", file=sys.stderr)
                return EXIT_DWG2DXF_ERROR
            print(f"OK ({time.perf_counter() - t0:.2f}s)")

            # Step 2: DXF -> PDF
            print(f"[2/{total_steps}] DXF -> PDF ...", end=" ", flush=True)
            t0 = time.perf_counter()
            try:
                step_dxf_to_pdf(
                    dxf_path, output_path,
                    margin_mm=args.margin,
                    color_policy=args.color,
                    background=args.background,
                )
            except Exception as e:
                print("FAILED", file=sys.stderr)
                print(f"Error: {e}", file=sys.stderr)
                return EXIT_DXF2PDF_ERROR
            print(f"OK ({time.perf_counter() - t0:.2f}s)")
    else:
        # DXF input - skip conversion, go straight to PDF
        print(f"[1/{total_steps}] DXF -> PDF ...", end=" ", flush=True)
        t0 = time.perf_counter()
        try:
            step_dxf_to_pdf(
                input_path, output_path,
                margin_mm=args.margin,
                color_policy=args.color,
                background=args.background,
            )
        except Exception as e:
            print("FAILED", file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
            return EXIT_DXF2PDF_ERROR
        print(f"OK ({time.perf_counter() - t0:.2f}s)")

    elapsed = time.perf_counter() - t_total
    size_kb = output_path.stat().st_size / 1024
    print(
        f"\nDone: {input_path.name} -> {output_path.name} "
        f"({size_kb:.0f} KB, {elapsed:.2f}s total)"
    )
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
