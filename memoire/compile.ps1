# Compilation du memoire.
#
# On n'utilise PAS latexmk : c'est un script Perl, et MiKTeX basic n'embarque pas
# d'interpreteur Perl ("script engine not found"). Enchainer pdflatex et biber a la
# main evite d'installer Strawberry Perl pour rien.
#
#   .\compile.ps1            compilation complete (4 passes + biber)
#   .\compile.ps1 -Quick     une seule passe, pour verifier qu'une edition compile
#
# En fin de course le script affiche le NOMBRE DE PAGES DU COEUR, qui est la
# contrainte dure du PFE (30 pages, figures comprises, hors annexes).

param([switch]$Quick)

$ErrorActionPreference = "Stop"
$mik = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
$pdflatex = Join-Path $mik "pdflatex.exe"
$biber    = Join-Path $mik "biber.exe"

Set-Location $PSScriptRoot

# -interaction=nonstopmode : ne jamais attendre au clavier (le harnais n'a pas de stdin).
$flags = @("-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "memoire.tex")

function Invoke-Pass($n) {
    Write-Host "--- pdflatex passe $n ---"
    & $pdflatex @flags | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ECHEC pdflatex (passe $n). Erreurs :"
        Select-String -Path memoire.log -Pattern '^(.*:\d+:|!)' | Select-Object -First 25
        exit 1
    }
}

Invoke-Pass 1
if (-not $Quick) {
    & $biber memoire | Out-Null      # biber echoue tant qu'aucune citation n'existe : sans gravite
    Invoke-Pass 2
    Invoke-Pass 3
}

# --- Rapports de fin -------------------------------------------------------
# Le compte de pages se lit dans le .aux et non dans le .log : \typeout n'expanse
# pas \pageref, il l'ecrit litteralement. Le .aux porte la valeur resolue.
# \newlabel{fin-coeur}{{5.5}{8}{...}} -- le second groupe est la page.
$core = Select-String -Path memoire.aux -Pattern '\\newlabel\{fin-coeur\}\{\{[^}]*\}\{(\d+)\}' |
        Select-Object -Last 1
if ($core) {
    $n = [int]$core.Matches[0].Groups[1].Value
    $verdict = if ($n -le 30) { "OK" } else { "DEPASSEMENT de $($n - 30) page(s)" }
    Write-Host ""
    Write-Host "PAGES DU COEUR : $n / 30  --> $verdict"
}

$todo = (Select-String -Path memoire.log -Pattern '^A REDIGER : ' | Measure-Object).Count
Write-Host "Sections a rediger restantes : $todo"

$over = Select-String -Path memoire.log -Pattern 'Overfull \\hbox \((\d+\.\d+)pt'
$bad  = @($over | Where-Object { [double]$_.Matches[0].Groups[1].Value -gt 5 })
Write-Host "Overfull hbox > 5 pt : $($bad.Count)"

$undef = (Select-String -Path memoire.log -Pattern 'undefined' | Measure-Object).Count
Write-Host "References/citations non resolues : $undef"
