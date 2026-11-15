# Recreate the editable vector design as a multi-resolution Windows icon.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$output = Join-Path $PSScriptRoot 'soundscrape.ico'
$frames = @()
foreach ($size in @(16, 24, 32, 48, 64, 128, 256)) {
    $bitmap = New-Object System.Drawing.Bitmap($size, $size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.ScaleTransform(($size / 256.0), ($size / 256.0))
    $background = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml('#101C30'))
    $foreground = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml('#39E5C5'), 18)
    $foreground.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $foreground.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $shape = New-Object System.Drawing.Drawing2D.GraphicsPath
    $shape.AddArc(8, 8, 80, 80, 180, 90)
    $shape.AddArc(168, 8, 80, 80, 270, 90)
    $shape.AddArc(168, 168, 80, 80, 0, 90)
    $shape.AddArc(8, 168, 80, 80, 90, 90)
    $shape.CloseFigure()
    $graphics.FillPath($background, $shape)
    foreach ($bar in @(@(56, 104, 152), @(92, 76, 180), @(128, 52, 204), @(164, 88, 168), @(200, 110, 146))) {
        $graphics.DrawLine($foreground, $bar[0], $bar[1], $bar[0], $bar[2])
    }
    $buffer = New-Object System.IO.MemoryStream
    $bitmap.Save($buffer, [System.Drawing.Imaging.ImageFormat]::Png)
    $frames += ,@{ Size = $size; Data = $buffer.ToArray() }
    $buffer.Dispose()
    $shape.Dispose()
    $background.Dispose()
    $foreground.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}
$stream = [System.IO.File]::Create($output)
$writer = New-Object System.IO.BinaryWriter($stream)
try {
    $writer.Write([uint16]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]$frames.Count)
    $offset = 6 + 16 * $frames.Count
    foreach ($frame in $frames) {
        $dimension = if ($frame.Size -eq 256) { 0 } else { $frame.Size }
        $writer.Write([byte]$dimension)
        $writer.Write([byte]$dimension)
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([uint16]1)
        $writer.Write([uint16]32)
        $writer.Write([uint32]$frame.Data.Length)
        $writer.Write([uint32]$offset)
        $offset += $frame.Data.Length
    }
    foreach ($frame in $frames) { $writer.Write([byte[]]$frame.Data) }
} finally {
    $writer.Dispose()
    $stream.Dispose()
}
Write-Output "Created $output"
