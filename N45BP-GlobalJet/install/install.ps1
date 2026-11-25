# N45BP livery installer for the iniBuilds Global Jet (Microsoft Flight Simulator 2024)
#
# Run it with INSTALL-N45BP.bat. It:
#   1. finds your MSFS 2024 Community folder,
#   2. looks for any Global Jet livery you already have (iniManager / flightsim.to / Marketplace layout)
#      to learn the aircraft's real folder name, texture file names and livery.cfg settings,
#   3. builds the N45BP livery package with those names and puts it in Community,
#   4. writes N45BP-install-report.txt next to this script (also copied to the clipboard).
# It only creates/deletes packages whose folder name starts with "n45bp". Nothing else is changed.

$ErrorActionPreference = 'Stop'
$Here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$Files   = Join-Path $Here 'files'
$PkgName = 'n45bp-livery-globaljet'
$Title   = 'N45BP (camo)'
$Utf8    = New-Object System.Text.UTF8Encoding($false)
$Report  = New-Object System.Collections.Generic.List[string]
function Say([string]$s) { Write-Host $s; [void]$Report.Add($s) }

$Keys = @('EXT_1001','EXT_1002','EXT_1003','EXT_1004','EXT_1005','EXT_1006','EXT_1007',
          'ENG_L','ENG_R','WING_L_1001','WING_L_1002','WING_R_1001','WING_R_1002','Registration_ALBD')
$GJ = '(?i)glex|global|bd-?700|g6000|gl6t'
$NotGJ = '(?i)a3[0-9][0-9]|a2[0-9][0-9]|7[0-9]7|crj|e1[79]5|atr|dash|q400|citation|longitude|g[0-9]{3}|gulfstream|falcon|pc-?12|tbm|cessna|piper'

# ---------------------------------------------------------------- texture name -> our texture
function Get-Key([string]$fileName) {
    $n = $fileName.ToUpperInvariant()
    $n = $n -replace '\.JSON$', '' -replace '\.KTX2$', '' -replace '\.(PNG|TIF|TIFF|TGA|DDS)$', ''
    if ($n -match 'COMP|NORM|NRM|_ORM|RMA|METAL|ROUGH|_AO|EMIS|_LIT|GLASS|DIRT|WINDOW|COCKPIT|CABIN|INTERIOR|DETAIL|MASK|_OCC|LOGO|DECAL|PLACARD') { return $null }
    if ($n -match 'REGISTRATION|(^|[_\-\.])REG([_\-\.]|$)') { return 'Registration_ALBD' }
    $udim = 0
    if ($n -match '(10[0-9][0-9])') { $udim = [int]$Matches[1] }
    $side = ''
    if ($n -match '(^|[_\-\.])(L|LH|LEFT)([_\-\.]|$)') { $side = 'L' }
    elseif ($n -match '(^|[_\-\.])(R|RH|RIGHT)([_\-\.]|$)') { $side = 'R' }
    if ($n -match 'ENG|NAC|COWL') {
        if ($side -eq '' -and $n -match '(^|[_\-\.])1([_\-\.]|$)') { $side = 'L' }
        if ($side -eq '' -and $n -match '(^|[_\-\.])2([_\-\.]|$)') { $side = 'R' }
        if ($side -eq '' -and $udim -eq 1001) { $side = 'L' }
        if ($side -eq '' -and $udim -eq 1002) { $side = 'R' }
        if ($side -ne '') { return "ENG_$side" }
        return $null
    }
    if ($n -match 'WING') {
        if ($side -eq '') { return $null }
        if ($udim -eq 0) { $udim = 1001 }
        if ($udim -eq 1001 -or $udim -eq 1002) { return "WING_${side}_$udim" }
        return $null
    }
    if ($udim -ge 1001 -and $udim -le 1007) { return "EXT_$udim" }
    return $null
}

# Names tried when nothing on this PC tells us the real ones.
function Get-GuessNames([string]$key) {
    if ($key -match '^EXT_(\d+)$') { $k = $Matches[1]
        return @("GLEX_EXT_ALBD--$k", "GLEX_EXT_${k}_ALBD", "GLEX_EXT_ALBD.$k", "GLEX_EXT_ALBD_$k", "EXT_${k}_ALBD", "EXT_ALBD--$k", "LIVERY_ALBD--$k") }
    if ($key -match '^ENG_([LR])$') { $s = $Matches[1]
        return @("GLEX_ENG_${s}_ALBD", "GLEX_ENG_${s}_ALBD--1001", "GLEX_ENG_${s}_1001_ALBD", "ENG_${s}_ALBD", "LIVERY_ENG_${s}_ALBD") }
    if ($key -match '^WING_([LR])_(\d+)$') { $s = $Matches[1]; $k = $Matches[2]
        return @("GLEX_WING_${s}_ALBD--$k", "GLEX_WING_${s}_${k}_ALBD", "GLEX_WING_${s}_ALBD.$k", "WING_${s}_${k}_ALBD", "WING_${s}_ALBD--$k", "LIVERY_WING_${s}_ALBD--$k") }
    return @('REGISTRATION_ALBD')
}

# Put our texture for $key into $dir under $name (".PNG.KTX2" added if missing), with its .json.
function Put-Texture([string]$key, [string]$dir, [string]$name, [string]$linkFrom) {
    if ($name -notmatch '(?i)\.KTX2$') { $name = "$name.PNG.KTX2" }
    $dst = Join-Path $dir $name
    foreach ($ext in @('', '.json')) {
        $d = "$dst$ext"
        if (Test-Path -LiteralPath $d) { Remove-Item -LiteralPath $d -Force }
        $done = $false
        if ($linkFrom -and (Test-Path -LiteralPath "$linkFrom$ext")) {
            try { New-Item -ItemType HardLink -Path $d -Value "$linkFrom$ext" | Out-Null; $done = $true } catch { $done = $false }
        }
        if (-not $done) { Copy-Item -LiteralPath (Join-Path $Files "$key.PNG.KTX2$ext") -Destination $d -Force }
    }
    return $dst
}

function Write-Text([string]$path, [string]$text) { [System.IO.File]::WriteAllText($path, $text, $Utf8) }
function Esc([string]$s) { return $s.Replace('\', '\\').Replace('"', '\"') }

try {
    Say "N45BP livery installer  $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    if (-not (Test-Path -LiteralPath (Join-Path $Files 'EXT_1001.PNG.KTX2'))) { throw "The 'files' folder next to this script is missing or incomplete. Extract the whole ZIP first." }

    # ------------------------------------------------------------ 1. MSFS 2024 folders
    $roots = New-Object System.Collections.Generic.List[string]
    $cfgs = @((Join-Path $env:APPDATA 'Microsoft Flight Simulator 2024\UserCfg.opt'),
              (Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\UserCfg.opt'),
              (Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.FlightSimulator2024_8wekyb3d8bbwe\LocalCache\UserCfg.opt'))
    foreach ($c in $cfgs) {
        if (Test-Path -LiteralPath $c) {
            $m = Select-String -LiteralPath $c -Pattern '^\s*InstalledPackagesPath\s+"([^"]+)"' | Select-Object -First 1
            if ($m) { $p = $m.Matches[0].Groups[1].Value
                if ((Test-Path -LiteralPath $p) -and -not $roots.Contains($p)) { $roots.Add($p); Say "Found MSFS 2024 packages folder: $p" } }
        }
    }
    foreach ($d in @((Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\Packages'),
                     (Join-Path $env:APPDATA 'Microsoft Flight Simulator 2024\Packages'))) {
        if ((Test-Path -LiteralPath $d) -and -not $roots.Contains($d)) { $roots.Add($d); Say "Found MSFS 2024 packages folder: $d" }
    }
    $communities = @()
    foreach ($r in $roots) { $c = Join-Path $r 'Community'; if (Test-Path -LiteralPath $c) { $communities += $c } }
    if ($communities.Count -eq 0) {
        Write-Host ''
        $c = Read-Host 'Could not find your Community folder. Paste its full path here and press Enter'
        $c = $c.Trim('"', ' ')
        if (-not (Test-Path -LiteralPath $c)) { throw "Folder not found: $c" }
        $communities = @($c); $roots.Add((Split-Path -Parent $c))
    }
    foreach ($c in $communities) { Say "Community folder: $c" }

    # ------------------------------------------------------------ 2. what does this PC know about the Global Jet?
    $pkgDirs = @()
    foreach ($r in $roots) {
        foreach ($sub in @('Community', 'Community2024', 'Official2024\OneStore', 'Official2024\Steam', 'Official\OneStore', 'Official\Steam')) {
            $p = Join-Path $r $sub
            if (Test-Path -LiteralPath $p) { $pkgDirs += @(Get-ChildItem -LiteralPath $p -Directory -ErrorAction SilentlyContinue) }
        }
    }
    foreach ($c in $communities) { if (-not ($roots | Where-Object { $c.StartsWith($_) })) { $pkgDirs += @(Get-ChildItem -LiteralPath $c -Directory -ErrorAction SilentlyContinue) } }
    $pkgDirs = @($pkgDirs | Where-Object { $_.Name -notlike 'n45bp*' })
    Say "Packages scanned: $($pkgDirs.Count)"

    # 2a. installed Global Jet liveries (best source: real folder, real texture names, real livery.cfg)
    $templates = @()
    foreach ($pk in $pkgDirs) {
        $air = Join-Path $pk.FullName 'SimObjects\Airplanes'
        if (-not (Test-Path -LiteralPath $air)) { continue }
        foreach ($ac in @(Get-ChildItem -LiteralPath $air -Directory -ErrorAction SilentlyContinue)) {
            $acHit = ($ac.Name -match $GJ) -and ($ac.Name -notmatch $NotGJ)
            $pkHit = ($pk.Name -match $GJ) -and ($ac.Name -notmatch $NotGJ)
            if (-not ($acHit -or $pkHit)) { continue }
            $liv = Join-Path $ac.FullName 'liveries'
            if (-not (Test-Path -LiteralPath $liv)) { continue }
            foreach ($cfg in @(Get-ChildItem -LiteralPath $liv -Filter 'livery.cfg' -Recurse -Depth 3 -File -ErrorAction SilentlyContinue)) {
                $tex = @(Get-ChildItem -LiteralPath $cfg.DirectoryName -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '(?i)\.KTX2$' })
                $score = [Math]::Min($tex.Count, 40)
                if ($ac.Name -match '(?i)glex') { $score += 200 } elseif ($acHit) { $score += 100 }
                if ($pk.Name -match '(?i)inibuilds|glex') { $score += 50 }
                $templates += [pscustomobject]@{ Pkg = $pk.FullName; Aircraft = $ac.Name; Dir = $cfg.DirectoryName; LivRoot = $liv; Ktx = $tex.Count; Score = $score }
                Say "  Global Jet livery found: $($pk.Name)  ->  SimObjects\Airplanes\$($ac.Name)\...\$(Split-Path -Leaf $cfg.DirectoryName)  ($($tex.Count) KTX2 textures)"
            }
        }
    }

    # 2b. layout.json of Global Jet packages (lists every file even when the package itself is encrypted)
    $layoutAircraft = @{}
    $layoutNames = New-Object System.Collections.Generic.List[string]
    $gjPkgs = @($pkgDirs | Where-Object { $_.Name -match '(?i)inibuilds.*(glex|global)|glex' })
    if ($gjPkgs.Count -eq 0) { $gjPkgs = @($pkgDirs | Where-Object { $_.Name -match $GJ -and $_.Name -notmatch $NotGJ }) }
    foreach ($pk in $gjPkgs) {
        $lj = Join-Path $pk.FullName 'layout.json'
        if (-not (Test-Path -LiteralPath $lj)) { continue }
        try { $j = [System.IO.File]::ReadAllText($lj) | ConvertFrom-Json } catch { continue }
        foreach ($e in @($j.content)) {
            $p = [string]$e.path
            if ($p -match '^(?i)SimObjects/Airplanes/([^/]+)/(.+)$') {
                $a = $Matches[1]; $rest = $Matches[2]
                if ($a -match $NotGJ) { continue }
                if ($layoutAircraft.ContainsKey($a)) { $layoutAircraft[$a] += 1 } else { $layoutAircraft[$a] = 1 }
                if ($rest -match '(?i)\.KTX2$') { $leaf = ($rest -split '/')[-1]; if (-not $layoutNames.Contains($leaf)) { $layoutNames.Add($leaf) } }
            }
        }
        Say "  Read file list of package: $($pk.Name)"
    }
    foreach ($a in $layoutAircraft.Keys) { Say "  Aircraft folder seen in package file lists: $a ($($layoutAircraft[$a]) files)" }

    # 2c. folders MSFS created when you flew the jet (user settings)
    $userAircraft = @()
    foreach ($d in @((Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\SimObjects\Airplanes'),
                     (Join-Path $env:APPDATA 'Microsoft Flight Simulator 2024\SimObjects\Airplanes'))) {
        if (Test-Path -LiteralPath $d) {
            foreach ($a in @(Get-ChildItem -LiteralPath $d -Directory -ErrorAction SilentlyContinue)) {
                if ($a.Name -match $GJ -and $a.Name -notmatch $NotGJ) { $userAircraft += $a.Name; Say "  Aircraft folder from your sim settings: $($a.Name)" }
            }
        }
    }

    # ------------------------------------------------------------ 3. decide
    $template = $templates | Sort-Object -Property Score -Descending | Select-Object -First 1
    $aircraftList = @()
    if ($template) {
        $aircraftList = @($template.Aircraft)
        Say "Using livery as template: $($template.Dir)"
    } elseif ($layoutAircraft.Count -gt 0) {
        $aircraftList = @($layoutAircraft.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 1 | ForEach-Object { $_.Key })
    } elseif ($userAircraft.Count -gt 0) {
        $aircraftList = @($userAircraft | Select-Object -Unique)
    } else {
        $aircraftList = @('inibuilds_glex', 'GLEX', 'Global', 'GlobalJet', 'Global_Jet', 'inibuilds-glex', 'inibuilds-aircraft-glex', 'Global6000', 'Global_6000')
        Say 'WARNING: nothing on this PC names the Global Jet folder. Installing under several guessed folder names.'
    }
    Say "Aircraft folder(s) used: $($aircraftList -join ', ')"

    # ------------------------------------------------------------ 4. build + install
    foreach ($community in $communities) {
        foreach ($old in @('n45bp-livery-inibuilds-global-jet', $PkgName)) {
            $o = Join-Path $community $old
            if (Test-Path -LiteralPath $o) { Remove-Item -LiteralPath $o -Recurse -Force; Say "Removed old package: $o" }
        }
        $pkgRoot = Join-Path $community $PkgName
        $first = $true; $mappedKeys = @{}; $templateNames = @(); $firstCopy = @{}
        foreach ($aircraft in $aircraftList) {
            $livRel = 'N45BP\N45BP'
            if ($template) {
                $parts = @($template.Dir.Substring($template.LivRoot.Length).Trim('\').Split('\'))
                $parts[$parts.Count - 1] = 'N45BP'
                $livRel = $parts -join '\'
            }
            $liv = Join-Path $pkgRoot "SimObjects\Airplanes\$aircraft\liveries\$livRel"
            New-Item -ItemType Directory -Path $liv -Force | Out-Null
            $mk = @{}
            if ($template) {
                Get-ChildItem -LiteralPath $template.Dir -Force | Copy-Item -Destination $liv -Recurse -Force
                $ktx = @(Get-ChildItem -LiteralPath $liv -Recurse -File | Where-Object { $_.Name -match '(?i)\.KTX2$' })
                $templateNames = @($ktx | ForEach-Object { $_.Name })
                foreach ($f in $ktx) {
                    $k = Get-Key $f.Name
                    if ($k) { Put-Texture $k $f.DirectoryName $f.Name $null | Out-Null; $mk[$k] = $f.Name }
                }
                $texDir = ($ktx | Group-Object -Property DirectoryName | Sort-Object -Property Count -Descending | Select-Object -First 1).Name
                if (-not $texDir) { $texDir = Join-Path $liv 'texture'; New-Item -ItemType Directory -Path $texDir -Force | Out-Null }
            } else {
                $texDir = Join-Path $liv 'texture'
                New-Item -ItemType Directory -Path $texDir -Force | Out-Null
                Write-Text (Join-Path $liv 'livery.cfg') ("[Version]`r`nmajor = 1`r`nminor = 0`r`n`r`n[General]`r`nname = `"$Title`"`r`natc_id = `"N45BP`"")
            }
            # names learned from package file lists
            foreach ($nm in $layoutNames) {
                $k = Get-Key $nm
                if ($k -and -not $mk.ContainsKey($k)) { Put-Texture $k $texDir $nm $firstCopy[$k] | Out-Null; $mk[$k] = $nm }
            }
            # anything still unknown: guessed names (hard links, no extra disk space)
            foreach ($k in $Keys) {
                if ($mk.ContainsKey($k)) { continue }
                foreach ($nm in (Get-GuessNames $k)) {
                    $p = Put-Texture $k $texDir $nm $firstCopy[$k]
                    if (-not $firstCopy.ContainsKey($k)) { $firstCopy[$k] = $p }
                }
            }
            # livery.cfg from a template: rename it, keep everything else (required_tags etc.)
            $cfgPath = Join-Path $liv 'livery.cfg'
            if ($template -and (Test-Path -LiteralPath $cfgPath)) {
                $t = [System.IO.File]::ReadAllText($cfgPath)
                if ($t -match '(?im)^[ \t]*name[ \t]*=') { $t = [regex]::Replace($t, '(?im)^([ \t]*name[ \t]*=[ \t]*)[^\r\n]*', ('${1}"' + $Title + '"')) }
                else { $t = [regex]::Replace($t, '(?im)^(\[general\])[ \t]*(\r?)$', ('$1$2' + "`nname = `"$Title`"" + '$2')) }
                $t = [regex]::Replace($t, '(?im)^([ \t]*atc_id[ \t]*=[ \t]*)[^\r\n]*', '${1}"N45BP"')
                $t = [regex]::Replace($t, '(?im)^([ \t]*atc_airline[ \t]*=[ \t]*)[^\r\n]*', '${1}""')
                $t = [regex]::Replace($t, '(?im)^([ \t]*icao_airline[ \t]*=[ \t]*)[^\r\n]*', '${1}""')
                Write-Text $cfgPath $t
            }
            # thumbnails: ours at every size the template uses
            $thumbDir = Join-Path $liv 'thumbnail'
            New-Item -ItemType Directory -Path $thumbDir -Force | Out-Null
            foreach ($tn in @('thumbnail.png', 'thumbnail_small.png', 'thumbnail_side.png', 'thumbnail_button.png', 'thumbnail_popup.png')) {
                Copy-Item -LiteralPath (Join-Path $Files $tn) -Destination (Join-Path $thumbDir $tn) -Force
            }
            try {
                Add-Type -AssemblyName System.Drawing
                foreach ($tf in @(Get-ChildItem -LiteralPath $thumbDir -File | Where-Object { $_.Extension -match '(?i)\.(png|jpg|jpeg)$' })) {
                    if (@('thumbnail.png', 'thumbnail_small.png', 'thumbnail_side.png', 'thumbnail_button.png', 'thumbnail_popup.png') -contains $tf.Name.ToLowerInvariant()) { continue }
                    $old = [System.Drawing.Image]::FromFile($tf.FullName); $w = $old.Width; $h = $old.Height; $old.Dispose()
                    $srcName = 'thumb_master.png'; if ($tf.Name -match '(?i)side|button') { $srcName = 'thumb_side_master.png' }
                    $src = [System.Drawing.Image]::FromFile((Join-Path $Files $srcName))
                    $bmp = New-Object System.Drawing.Bitmap($w, $h)
                    $g = [System.Drawing.Graphics]::FromImage($bmp)
                    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                    $s = [Math]::Min($w / $src.Width, $h / $src.Height)
                    $dw = [int]($src.Width * $s); $dh = [int]($src.Height * $s)
                    $g.DrawImage($src, [int](($w - $dw) / 2), [int](($h - $dh) / 2), $dw, $dh)
                    $g.Dispose(); $src.Dispose()
                    $fmt = [System.Drawing.Imaging.ImageFormat]::Png; if ($tf.Extension -match '(?i)jpe?g') { $fmt = [System.Drawing.Imaging.ImageFormat]::Jpeg }
                    $bmp.Save($tf.FullName, $fmt); $bmp.Dispose()
                }
            } catch { Say "  (thumbnail resize skipped: $($_.Exception.Message))" }
            if ($first) {
                $mappedKeys = $mk
                Say "Livery folder: $liv"
                Say "Textures matched to this aircraft's real file names: $($mappedKeys.Count) of $($Keys.Count)"
                foreach ($k in $Keys) { if ($mappedKeys.ContainsKey($k)) { Say "    $k -> $($mappedKeys[$k])" } }
                $first = $false
            }
        }

        # manifest.json + layout.json
        $tm = $null
        if ($template -and (Test-Path -LiteralPath (Join-Path $template.Pkg 'manifest.json'))) {
            try { $tm = [System.IO.File]::ReadAllText((Join-Path $template.Pkg 'manifest.json')) | ConvertFrom-Json } catch { $tm = $null }
        }
        $ctype = 'AIRCRAFT'; $mingame = '1.0.0'; $hint = ''; $compat = ''
        if ($tm) {
            if ($tm.content_type) { $ctype = [string]$tm.content_type }
            if ($tm.minimum_game_version) { $mingame = [string]$tm.minimum_game_version }
            if ($tm.package_order_hint) { $hint = [string]$tm.package_order_hint }
            if ($tm.minimum_compatibility_version) { $compat = [string]$tm.minimum_compatibility_version }
        }
        $all = @(Get-ChildItem -LiteralPath $pkgRoot -Recurse -File | Where-Object { -not ($_.DirectoryName -eq $pkgRoot -and ($_.Name -eq 'layout.json' -or $_.Name -eq 'manifest.json')) })
        $entries = foreach ($f in $all) {
            $rel = $f.FullName.Substring($pkgRoot.Length + 1).Replace('\', '/')
            [pscustomobject]@{ Rel = $rel; Key = $rel.ToLowerInvariant(); Size = $f.Length; Date = $f.LastWriteTimeUtc.ToFileTimeUtc() }
        }
        $entries = @($entries | Sort-Object -Property Key)
        $sb = New-Object System.Text.StringBuilder
        [void]$sb.Append("{`n  `"content`": [`n")
        for ($i = 0; $i -lt $entries.Count; $i++) {
            $e = $entries[$i]
            [void]$sb.Append("    {`n      `"path`": `"$(Esc $e.Rel)`",`n      `"size`": $($e.Size),`n      `"date`": $($e.Date)`n    }")
            if ($i -lt $entries.Count - 1) { [void]$sb.Append(",`n") } else { [void]$sb.Append("`n") }
        }
        [void]$sb.Append("  ]`n}")
        Write-Text (Join-Path $pkgRoot 'layout.json') $sb.ToString()
        $total = ($entries | Measure-Object -Property Size -Sum).Sum + (Get-Item -LiteralPath (Join-Path $pkgRoot 'layout.json')).Length
        function Manifest([long]$size) {
            $lines = @('{', '  "dependencies": [],', "  `"content_type`": `"$ctype`",", '  "title": "N45BP camo - iniBuilds Global Jet",',
                       '  "manufacturer": "Bombardier",', '  "creator": "N45BP livery",', '  "package_version": "1.0.0",',
                       "  `"minimum_game_version`": `"$mingame`",")
            if ($compat) { $lines += "  `"minimum_compatibility_version`": `"$compat`"," }
            if ($hint) { $lines += "  `"package_order_hint`": `"$hint`"," }
            $lines += @('  "release_notes": {', '    "neutral": {', '      "LastUpdate": "",', '      "OlderHistory": ""', '    }', '  },',
                        '  "builder": "Microsoft Flight Simulator 2024",', "  `"total_package_size`": `"$($size.ToString('D20'))`"", '}')
            return ($lines -join "`r`n")
        }
        $mpath = Join-Path $pkgRoot 'manifest.json'
        Write-Text $mpath (Manifest 0)
        Write-Text $mpath (Manifest ($total + (Get-Item -LiteralPath $mpath).Length))
        $mb = [Math]::Round((($entries | Measure-Object -Property Size -Sum).Sum) / 1MB)
        Say "Installed: $pkgRoot  ($($entries.Count) files, $mb MB)"
    }

    # ------------------------------------------------------------ 5. report
    if ($templates.Count -gt 0) {
        Say ''; Say 'Texture files in the template livery:'
        foreach ($n in ($templateNames | Sort-Object)) { Say "    $n" }
    }
    if ($layoutNames.Count -gt 0) {
        Say ''; Say "Texture files listed by Global Jet packages: $($layoutNames.Count)"
        foreach ($n in ($layoutNames | Sort-Object | Select-Object -First 120)) { Say "    $n" }
    }
    Say ''
    if ($template -and $mappedKeys.Count -ge 9) {
        Say 'RESULT: installed using the real names from your PC.'
    } elseif ($template -or $layoutAircraft.Count -gt 0 -or $userAircraft.Count -gt 0) {
        Say 'RESULT: installed in the real aircraft folder, but some texture names are still guesses.'
    } else {
        Say 'RESULT: installed with guessed names only. Installing any free Global Jet livery from iniManager and running this again will fix that.'
    }
    $ok = $true
} catch {
    Say ''; Say "ERROR: $($_.Exception.Message)"
    $ok = $false
}

$rep = Join-Path $Here 'N45BP-install-report.txt'
try { [System.IO.File]::WriteAllLines($rep, $Report.ToArray(), $Utf8) } catch { }
try { Set-Clipboard -Value ($Report -join "`r`n") } catch { }
Write-Host ''
Write-Host '------------------------------------------------------------------'
Write-Host 'Next: start MSFS 2024 -> pick the Global Jet -> Configure -> livery "N45BP (camo)".'
Write-Host 'If it is missing or the plane is not camo, the report above has been copied:'
Write-Host 'paste it to Claude (Ctrl+V). It is also saved as N45BP-install-report.txt'
Write-Host '------------------------------------------------------------------'
