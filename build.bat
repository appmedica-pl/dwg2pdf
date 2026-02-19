@echo off
echo === Building dwg2pdf.exe ===
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install PyInstaller if not present
pip install pyinstaller >nul 2>&1

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building single-file executable...
echo This may take a few minutes.
echo.

pyinstaller dwg2pdf.spec --noconfirm
echo.

echo ========================================
echo  Build result:
echo ========================================

if exist dist\dwg2pdf.exe (
    for %%A in (dist\dwg2pdf.exe) do echo  OK  dwg2pdf.exe  (%%~zA bytes)
) else (
    echo  FAIL  dwg2pdf.exe
)

echo.
echo  Usage:
echo    dwg2pdf.exe input.dwg output.pdf
echo    dwg2pdf.exe input.dxf output.pdf
echo    dwg2pdf.exe input.dwg output.pdf --margin 10
echo    dwg2pdf.exe --help
echo.
echo  NOTE: dwg2pdf.exe requires these files alongside it
echo  (only needed for DWG input, not for DXF):
echo    dwg2dxf.exe, libredwg-0.dll
echo.
pause
