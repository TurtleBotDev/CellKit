# Render exported character cells to PNG using Windows' built-in System.Drawing.
# These are labelled UI previews, not captures of an interactive terminal window.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$projectDirectory = Split-Path -Parent $PSScriptRoot
$frameFile = Join-Path $projectDirectory '.test-results\previews\frames.json'
$outputDirectory = Join-Path $projectDirectory 'docs\screenshots'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$frames = Get-Content -LiteralPath $frameFile -Raw -Encoding UTF8 | ConvertFrom-Json
$regularFont = New-Object System.Drawing.Font('Consolas', 16, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$boldFont = New-Object System.Drawing.Font('Consolas', 16, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$titleFont = New-Object System.Drawing.Font('Segoe UI', 13, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$format = [System.Drawing.StringFormat]::GenericTypographic.Clone()
$format.FormatFlags = $format.FormatFlags -bor [System.Drawing.StringFormatFlags]::NoClip
$styleCache = @{}

function Get-CellStyle([string]$style) {
    if ($styleCache.ContainsKey($style)) { return $styleCache[$style] }
    $codes = @($style.Split(';') | ForEach-Object { [int]$_ })
    $foreground = [System.Drawing.Color]::FromArgb(205, 215, 230)
    $background = [System.Drawing.Color]::FromArgb(16, 22, 34)
    $bold = $false
    $reverse = $false
    for ($index = 0; $index -lt $codes.Count; $index++) {
        if ($codes[$index] -eq 1) { $bold = $true }
        if ($codes[$index] -eq 7) { $reverse = $true }
        if (($codes[$index] -eq 38 -or $codes[$index] -eq 48) -and $codes[$index + 1] -eq 2) {
            $colour = [System.Drawing.Color]::FromArgb($codes[$index + 2], $codes[$index + 3], $codes[$index + 4])
            if ($codes[$index] -eq 38) { $foreground = $colour } else { $background = $colour }
            $index += 4
        }
    }
    if ($reverse) { $temporary = $foreground; $foreground = $background; $background = $temporary }
    $result = @{
        Foreground = New-Object System.Drawing.SolidBrush($foreground)
        Background = New-Object System.Drawing.SolidBrush($background)
        Font = $(if ($bold) { $boldFont } else { $regularFont })
        Underline = ($codes -contains 4)
    }
    $styleCache[$style] = $result
    return $result
}

try {
    foreach ($frame in $frames) {
        $cellWidth, $cellHeight, $margin, $top = 9, 20, 18, 50
        $bitmap = New-Object System.Drawing.Bitmap(($frame.rows[0].Count * $cellWidth + $margin * 2), ($frame.rows.Count * $cellHeight + $top + $margin))
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([System.Drawing.Color]::FromArgb(12, 16, 25))
            $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
            $graphics.DrawString(('CellKit  /  ' + $frame.title), $titleFont, [System.Drawing.Brushes]::LightGray, 18, 14)
            $graphics.DrawString('RENDERED PREVIEW', $titleFont, [System.Drawing.Brushes]::SlateGray, ($bitmap.Width - 155), 14)
            # Paint all backgrounds first so a following space cannot clip a glyph.
            for ($row = 0; $row -lt $frame.rows.Count; $row++) {
                for ($column = 0; $column -lt $frame.rows[$row].Count; $column++) {
                    $style = Get-CellStyle $frame.rows[$row][$column][1]
                    $graphics.FillRectangle($style.Background, ($margin + $column * $cellWidth), ($top + $row * $cellHeight), $cellWidth, $cellHeight)
                }
            }
            for ($row = 0; $row -lt $frame.rows.Count; $row++) {
                for ($column = 0; $column -lt $frame.rows[$row].Count; $column++) {
                    $cell = $frame.rows[$row][$column]
                    $style = Get-CellStyle $cell[1]
                    $left, $y = ($margin + $column * $cellWidth), ($top + $row * $cellHeight)
                    if ($cell[0] -ne ' ') {
                        $graphics.DrawString([string]$cell[0], $style.Font, $style.Foreground, [single]$left, [single]$y, $format)
                    }
                    if ($style.Underline) { $graphics.FillRectangle($style.Foreground, $left, ($y + $cellHeight - 2), $cellWidth, 1) }
                }
            }
            $destination = Join-Path $outputDirectory ($frame.name + '.png')
            $bitmap.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
            Write-Output $destination
        } finally {
            $graphics.Dispose()
            $bitmap.Dispose()
        }
    }
} finally {
    foreach ($style in $styleCache.Values) { $style.Foreground.Dispose(); $style.Background.Dispose() }
    $regularFont.Dispose(); $boldFont.Dispose(); $titleFont.Dispose(); $format.Dispose()
}
