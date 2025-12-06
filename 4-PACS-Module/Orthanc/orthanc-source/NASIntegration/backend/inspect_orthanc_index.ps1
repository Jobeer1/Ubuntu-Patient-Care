$folder = 'C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index'
if (-not (Test-Path $folder)) { Write-Output "Folder not found: $folder"; exit 1 }
Write-Output "Inspecting folder: $folder"
# read up to 5 MB from each file for inspection
$maxRead = 5 * 1024 * 1024
Get-ChildItem -Path $folder -File | ForEach-Object {
    $f = $_
    $p = $f.FullName
    Write-Output ("\nFILE: {0}  Size: {1} bytes" -f $f.Name, $f.Length)
    try {
        $read = [Math]::Min($f.Length, $maxRead)
        $fs = [System.IO.File]::Open($p, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try {
            $bytes = New-Object byte[] $read
            $fs.Read($bytes, 0, $read) | Out-Null
        } finally { $fs.Close() }
        $headLen = [Math]::Min(128, $bytes.Length)
        $head = $bytes[0..($headLen-1)]
        $asciiHead = -join ($head | ForEach-Object { if ($_ -ge 32 -and $_ -le 126) { [char]$_ } else { '.' } })
        $hexHead = ($head | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
        Write-Output "  Head ASCII: $asciiHead"
        Write-Output "  Head HEX: $hexHead"
        if ($asciiHead -match 'SQLite format 3') {
            Write-Output "  => Detected SQLite main DB file"
            # build a mostly-ASCII string for pattern search
            $asciiAll = -join ($bytes | ForEach-Object { if ($_ -ge 32 -and $_ -le 126) { [char]$_ } else { ' ' } })
            $patterns = @('CREATE TABLE','CREATE INDEX','PRAGMA','BEGIN','COMMIT','INSERT INTO','PatientName','PatientID','PatientBirthDate','StudyInstanceUID','StudyDate','AccessionNumber','Modality','InstitutionName','StudyDescription','SeriesDescription','BodyPartExamined','PatientSex')
            foreach ($pat in $patterns) {
                Write-Output "\n  -- Searching for pattern: $pat"
                $regex = [regex]::Matches($asciiAll, ".{0,80}" + [regex]::Escape($pat) + ".{0,200}") | ForEach-Object { $_.Value.Trim() }
                $uniq = $regex | Select-Object -Unique
                if ($uniq.Count -eq 0) { Write-Output ("    No matches for {0}" -f $pat) } else {
                    $i = 0
                    foreach ($m in $uniq) { $i++; if ($i -le 50) { Write-Output ("    Match {0}: {1}" -f $i, $m) } }
                }
            }
        } elseif ($f.Name -match '-wal$') { Write-Output "  => Detected SQLite WAL file" }
        elseif ($f.Name -match '-shm$') { Write-Output "  => Detected SQLite SHM file" }
        else { Write-Output "  => Unknown binary file (not SQLite main/WAL/SHM)" }
    } catch {
        Write-Output "  ERROR inspecting file: $($_.Exception.Message)"
    }
}

Write-Output "\nFinished inspection."
