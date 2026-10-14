# GurOS - tek satirlik kurulum (Windows PowerShell 5.1+ ve PowerShell 7)
#
#   irm https://raw.githubusercontent.com/guraygur0/guros-ikinci-beyin/main/kur.ps1 | iex
#
# Ne yapar: Python 3.9+ bulur (yoksa kurmayi teklif eder), GurOS'u ~\guros-ikinci-beyin klasorune indirir ya da
# gunceller, sonra soru soran kurulumu (kur.py) baslatir. Sen onaylamadan vault'una hicbir sey yazilmaz.
#
# Bu dosya bilerek yalniz ASCII: PowerShell 5.1 BOM'suz .ps1 dosyalarini ANSI okur, BOM ise "irm | iex"i bozar.
# Turkce harfler bu yuzden {015F} gibi Unicode kodlariyla yazildi ve ekrana basilirken cozuluyor.
#
# Ortam degiskenleri (test ve ileri kullanim):
#   GUROS_KAYNAK  indirme yapma, bu klasordeki kur.py'yi calistir
#   GUROS_HEDEF   indirilecek klasor (varsayilan: ~\guros-ikinci-beyin)

function ConvertFrom-GurOSKod([string]$Metin) {
    [regex]::Replace($Metin, '\{([0-9A-F]{4})\}', { param($m) [string][char][Convert]::ToInt32($m.Groups[1].Value, 16) })
}

function Write-GurOS([string]$Mesaj, [string]$Renk = 'Gray') {
    Write-Host (ConvertFrom-GurOSKod $Mesaj) -ForegroundColor $Renk
}

function Find-GurOSPython {
    foreach ($aday in @(@('py', '-3'), @('python'), @('python3'))) {
        if (-not (Get-Command $aday[0] -ErrorAction SilentlyContinue)) { continue }
        $ek = @($aday | Select-Object -Skip 1)
        try {
            # the Microsoft Store stub prints an advert and exits 9009; a real Python 3.9+ exits 0
            & $aday[0] @ek -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return ,$aday }
        } catch { }
    }
    return $null
}

function Initialize-GurOS {
    $depo = 'https://github.com/guraygur0/guros-ikinci-beyin'
    Write-Host ''
    Write-GurOS '  GurOS kurulumu ba{015F}l{0131}yor' 'Magenta'

    $py = Find-GurOSPython
    if (-not $py) {
        Write-GurOS '  Python 3.9 veya {00FC}st{00FC} bulunamad{0131}.' 'Yellow'
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            $cevap = Read-Host (ConvertFrom-GurOSKod '  winget ile Python 3.12 kurulsun mu? [E/h]')
            if ($cevap -notmatch '^\s*(h|hay.r|n|no)\s*$') {
                winget install -e --id Python.Python.3.12 --scope user | Out-Host
                $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' +
                            [Environment]::GetEnvironmentVariable('Path', 'Machine')
                $py = Find-GurOSPython
            }
        }
        if (-not $py) {
            Write-GurOS '  Python''u https://www.python.org/downloads/ adresinden kur ("Add python.exe to PATH" kutusunu i{015F}aretle),' 'Yellow'
            Write-GurOS '  sonra yeni bir PowerShell penceresinde bu komutu yeniden {00E7}al{0131}{015F}t{0131}r.' 'Yellow'
            return $null
        }
    }

    if ($env:GUROS_KAYNAK) { return @{ Python = $py; Kur = (Join-Path $env:GUROS_KAYNAK 'kur.py') } }

    $hedef = if ($env:GUROS_HEDEF) { $env:GUROS_HEDEF } else { Join-Path $HOME 'guros-ikinci-beyin' }
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ((Test-Path (Join-Path $hedef '.git')) -and $git) {
        Write-GurOS '  GurOS g{00FC}ncelleniyor...'
        git -C $hedef pull --ff-only -q 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) { Write-GurOS '  (g{00FC}ncellenemedi; eldeki s{00FC}r{00FC}mle devam)' 'Yellow' }
    } elseif ($git -and -not (Test-Path $hedef)) {
        Write-GurOS '  GurOS indiriliyor...'
        git clone -q --depth 1 "$depo.git" $hedef 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) { Write-GurOS '  {0130}ndirme ba{015F}ar{0131}s{0131}z oldu.' 'Red'; return $null }
    } else {
        if ((Test-Path $hedef) -and -not (Test-Path (Join-Path $hedef 'kur.py'))) {
            Write-Host "  $hedef" -ForegroundColor Red          # paths are printed as they are, never decoded
            Write-GurOS '  zaten var ve bir GurOS klas\u00f6r\u00fc de\u011fil; ta\u015f\u0131 ya da sil, sonra yeniden dene.' 'Red'
            return $null
        }
        Write-GurOS '  GurOS indiriliyor...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        $gecici = Join-Path ([IO.Path]::GetTempPath()) ('guros-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $gecici | Out-Null
        $zip = Join-Path $gecici 'guros.zip'
        $eskiIlerleme = $ProgressPreference
        $ProgressPreference = 'SilentlyContinue'          # the progress bar makes Invoke-WebRequest many times slower on 5.1
        try {
            Invoke-WebRequest "$depo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
            Expand-Archive $zip -DestinationPath $gecici -Force
        } catch {
            Write-GurOS '  {0130}ndirme ba{015F}ar{0131}s{0131}z oldu:' 'Red'
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
            return $null
        } finally {
            $ProgressPreference = $eskiIlerleme
        }
        if (Test-Path $hedef) { Remove-Item $hedef -Recurse -Force }
        Move-Item (Join-Path $gecici 'guros-ikinci-beyin-main') $hedef
        Remove-Item $gecici -Recurse -Force -ErrorAction SilentlyContinue
    }
    return @{ Python = $py; Kur = (Join-Path $hedef 'kur.py') }
}

function Invoke-GurOS([hashtable]$Hazir, [string[]]$Argumanlar) {
    # Start-Process -NoNewWindow keeps Python on this console, so the wizard can ask questions and show colours;
    # calling it inside a function with & would capture its output and hide the prompts.
    $tirnak = { param($s) '"' + ($s -replace '"', '\"') + '"' }
    $liste = @($Hazir.Python | Select-Object -Skip 1) + @(& $tirnak $Hazir.Kur) + @($Argumanlar | ForEach-Object { & $tirnak $_ })
    $surec = Start-Process -FilePath $Hazir.Python[0] -ArgumentList ($liste -join ' ') -NoNewWindow -PassThru
    $null = $surec.Handle                                # without this, ExitCode can stay empty on Windows PowerShell
    $surec.WaitForExit()
    return $surec.ExitCode
}

$__gurosHazir = Initialize-GurOS
if ($__gurosHazir) {
    $__gurosKod = Invoke-GurOS $__gurosHazir @($args)
} else {
    $__gurosKod = 1
}
if ($MyInvocation.MyCommand.Path) { exit $__gurosKod }    # run as a file (CI); under "irm | iex" never close the window
