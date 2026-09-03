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

# UNE LIGNE SUR STDERR NE DOIT PAS TUER LA COMPILATION. Avec $ErrorActionPreference = "Stop",
# Windows PowerShell 5.1 transforme chaque ligne de stderr d'un executable natif en
# NativeCommandError terminant, MEME quand l'executable rend 0. MiKTeX ecrit desormais un
# rappel de mise a jour sur stderr ("you have not checked for MiKTeX updates"), ce qui suffisait
# a interrompre le script des la premiere passe alors que le PDF etait correct. On neutralise
# la preference le temps de l'appel et on juge sur le CODE DE SORTIE, seule information fiable.
function Invoke-Natif($exe, $arguments) {
    $ancien = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try   { & $exe @arguments 2>&1 | Out-Null; return $LASTEXITCODE }
    finally { $ErrorActionPreference = $ancien }
}

function Invoke-Pass($n) {
    Write-Host "--- pdflatex passe $n ---"
    if ((Invoke-Natif $pdflatex $flags) -ne 0) {
        Write-Host "ECHEC pdflatex (passe $n). Erreurs :"
        Select-String -Path memoire.log -Pattern '^(.*:\d+:|!)' | Select-Object -First 25
        exit 1
    }
}

Invoke-Pass 1
if (-not $Quick) {
    # biber echoue tant qu'aucune citation n'existe : sans gravite, on ne teste pas son code.
    Invoke-Natif $biber @("memoire") | Out-Null
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

# Les encadres MATIERE sont l'echafaudage de redaction (cf. memoire/PLAN.md) : ils portent la
# liste des items du corpus qui reviennent a chaque section. Tant qu'il en reste, le compte de
# pages ci-dessus mesure l'echafaudage et non la prose -- ne pas le lire comme un budget tenu.
$mat = (Select-String -Path memoire.log -Pattern '^MATIERE : ' | Measure-Object).Count
Write-Host "Encadres MATIERE restants   : $mat"
if ($mat -gt 0) {
    Write-Host "  (le compte de pages ci-dessus inclut l'echafaudage, pas la prose finale)"
}

# Marqueurs d'attente des reponses des encadrants (memoire/encadrants.md). Ils sont VISIBLES
# tant que \attentesvisiblestrue : ce ne sont pas des trous, ce sont des phrases qu'une reponse
# enrichira. Les masquer avant depot si les reponses ne sont pas arrivees.
$att = (Select-String -Path memoire.log -Pattern '^ATTENTE : ' | Measure-Object).Count
Write-Host "Marqueurs d'attente encadrants : $att"

# Le sommaire donne la page de depart de chaque chapitre : c'est le controle du budget par
# chapitre defini dans PLAN.md section 4.
if (Test-Path memoire.toc) {
    Write-Host ""
    Write-Host "Depart de chaque chapitre (page) :"
    Select-String -Path memoire.toc -Pattern '\\contentsline \{chapter\}\{(?:\\numberline \{[^}]*\})?([^}]*)\}\{(\d+)\}' |
        ForEach-Object {
            $m = $_.Matches[0]
            "{0,-42} p. {1}" -f $m.Groups[1].Value, $m.Groups[2].Value
        }
}

$over = Select-String -Path memoire.log -Pattern 'Overfull \\hbox \((\d+\.\d+)pt'
$bad  = @($over | Where-Object { [double]$_.Matches[0].Groups[1].Value -gt 5 })
Write-Host "Overfull hbox > 5 pt : $($bad.Count)"

$undef = (Select-String -Path memoire.log -Pattern 'undefined' | Measure-Object).Count
Write-Host "References/citations non resolues : $undef"
