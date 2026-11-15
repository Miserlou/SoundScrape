param([string]$Python = ".\.venv\Scripts\python.exe")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    & $Python -c "import tkinter; t=tkinter.Tcl(); print('Tcl/Tk:', t.eval('info patchlevel'))"
    if ($LASTEXITCODE -ne 0) { throw "A working Tcl/Tk installation is required; do not ship a GUI-less EXE." }
    $nodePath = (Get-Command node.exe -ErrorAction Stop).Source
    $nodeVersion = & $nodePath --version
    if ($LASTEXITCODE -ne 0 -or $nodeVersion -ne 'v24.22.0') { throw "Node.js 24.22.0 is required to match the bundled runtime license." }
    $nodeLicense = Join-Path $PSScriptRoot 'assets\node-LICENSE.txt'
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name SoundScrape --icon assets/soundscrape.ico --add-data "assets/soundscrape.ico;assets" --add-binary "$nodePath;runtime" --add-data "$nodeLicense;runtime" --collect-all yt_dlp --collect-all yt_dlp_ejs --collect-all curl_cffi --collect-all imageio_ffmpeg --collect-all certifi desktop.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
    $hash = (Get-FileHash -LiteralPath "dist\SoundScrape.exe" -Algorithm SHA256).Hash.ToLower()
    "$hash  SoundScrape.exe" | Set-Content -LiteralPath "dist\SoundScrape.exe.sha256" -Encoding ascii
} finally {
    Pop-Location
}
