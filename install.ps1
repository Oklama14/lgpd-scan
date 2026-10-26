<#
.SYNOPSIS
    Instalador do lgpd-scan para Windows.

.DESCRIPTION
    Copia a skill e escreve o ponteiro no arquivo de contexto de cada agente.

    Uma honestidade que muda a expectativa: so o Claude Code tem mecanismo nativo de
    skill. Para Codex, Gemini CLI, Cursor e OpenCode, o que este script instala e a
    pasta da skill mais um bloco no arquivo que aquele agente ja le (AGENTS.md,
    GEMINI.md, .cursor\rules). Funciona -- o agente le o SKILL.md e segue -- mas nao
    e a mesma coisa que uma skill registrada.

    Escrito para rodar tanto no Windows PowerShell 5.1 (o que vem no Windows) quanto
    no PowerShell 7: sem operador ternario, sem ??, sem Join-Path de tres argumentos.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Agent claude
    .\install.ps1 -Scope user
    .\install.ps1 -Dest ..\outro-repo
    .\install.ps1 -DryRun
    .\install.ps1 -Uninstall
#>

[CmdletBinding()]
param(
    [ValidateSet('claude', 'codex', 'gemini', 'cursor', 'opencode', 'all')]
    [string[]] $Agent,

    [ValidateSet('project', 'user')]
    [string] $Scope = 'project',

    [string] $Dest = '.',
    [string] $From,
    [switch] $DryRun,
    [switch] $Force,
    [switch] $Uninstall
)

$ErrorActionPreference = 'Stop'
$Version    = '0.6.0'
$MarkBegin  = '<!-- lgpd-scan:begin -->'
$MarkEnd    = '<!-- lgpd-scan:end -->'

function Write-Info  { param([string] $Text) Write-Host $Text }
function Write-Note  { param([string] $Text) Write-Host "aviso: $Text" -ForegroundColor Yellow }
function Write-Step  { param([string] $Text) Write-Host "  $Text" }

if ($From) { $src = (Resolve-Path -LiteralPath $From).Path }
else       { $src = $PSScriptRoot }
if (-not $src) { $src = (Get-Location).Path }

if (-not (Test-Path -LiteralPath (Join-Path $src 'SKILL.md'))) {
    throw "nao achei SKILL.md em $src -- rode de dentro da pasta da skill ou use -From"
}

if ($Scope -eq 'user') {
    $root = $HOME
    if (-not $root) { $root = $env:USERPROFILE }
} else {
    if (-not (Test-Path -LiteralPath $Dest)) { throw "pasta de destino nao existe: $Dest" }
    $root = (Resolve-Path -LiteralPath $Dest).Path
}

# Uma copia, varios ponteiros. Cinco copias da mesma pasta divergem na primeira
# atualizacao, e ai nenhuma delas e a atual.
$skillDir = Join-Path (Join-Path (Join-Path $root '.claude') 'skills') 'lgpd-scan'
if ($Scope -eq 'user') {
    $skillDir = Join-Path (Join-Path (Join-Path $root '.claude') 'skills') 'lgpd-scan'
}

function Test-Cmd {
    param([string] $Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-DetectedAgents {
    $found = New-Object System.Collections.Generic.List[string]
    if ((Test-Path -LiteralPath (Join-Path $root '.claude')) -or
        (Test-Path -LiteralPath (Join-Path $HOME '.claude')) -or (Test-Cmd 'claude')) {
        $found.Add('claude')
    }
    if ((Test-Path -LiteralPath (Join-Path $root 'AGENTS.md')) -or
        (Test-Path -LiteralPath (Join-Path $root '.codex')) -or (Test-Cmd 'codex')) {
        $found.Add('codex')
    }
    if ((Test-Path -LiteralPath (Join-Path $root 'GEMINI.md')) -or
        (Test-Path -LiteralPath (Join-Path $root '.gemini')) -or (Test-Cmd 'gemini')) {
        $found.Add('gemini')
    }
    if ((Test-Path -LiteralPath (Join-Path $root '.cursor')) -or (Test-Cmd 'cursor')) {
        $found.Add('cursor')
    }
    if ((Test-Path -LiteralPath (Join-Path $root '.opencode')) -or (Test-Cmd 'opencode')) {
        $found.Add('opencode')
    }
    # Sem rastro nenhum, instala so para o Claude Code: escrever AGENTS.md e
    # .cursor\rules num repositorio que nunca usou aquelas ferramentas e poluicao,
    # nao conveniencia.
    if ($found.Count -eq 0) { $found.Add('claude') }
    return $found
}

$targets = $Agent
if (-not $targets -or $targets.Count -eq 0) {
    $targets = Get-DetectedAgents
    Write-Info ("agentes detectados: " + ($targets -join ' '))
}
if ($targets -contains 'all') {
    $targets = @('claude', 'codex', 'gemini', 'cursor', 'opencode')
}

function Get-PointerPath {
    $prefix = $root
    if (-not $prefix.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $prefix = $prefix + [System.IO.Path]::DirectorySeparatorChar
    }
    if ($skillDir.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $skillDir.Substring($prefix.Length).Replace('\', '/')
    }
    return $skillDir.Replace('\', '/')
}

function Get-Block {
    $path = Get-PointerPath
    return @"
$MarkBegin
## lgpd-scan - conformidade LGPD a partir do codigo

Quando a conversa mencionar LGPD, adequacao a LGPD, protecao de dados, dados
pessoais, privacidade, DPO, encarregado, ANPD, RIPD, ROPA, DPIA, ECA Digital,
verificacao de idade, ou pedir revisao de schema, migration, rota ou fluxo de
autenticacao em busca de problema de privacidade -- inclusive "este projeto esta
em conformidade?" sem dizer LGPD -- leia ``$path/SKILL.md`` e siga o que esta la,
do passo 1 ao 7.

Nao responda de memoria sobre a conformidade deste repositorio: a skill existe
porque a resposta tem de vir do codigo, com ``arquivo:linha`` e o trecho citado.

lgpd-scan $Version - instalado por install.ps1 - nao edite dentro dos marcadores
$MarkEnd
"@
}

# UTF-8 sem BOM: o Set-Content do PowerShell 5.1 escreve BOM por padrao, e um BOM no
# meio de um AGENTS.md que ja existia aparece como lixo na primeira linha do diff.
function Write-TextFile {
    param([string] $Path, [string] $Text)
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}

function Remove-Block {
    param([string] $Text)
    $lines = $Text -split "`r?`n"
    $out = New-Object System.Collections.Generic.List[string]
    $skip = $false
    foreach ($line in $lines) {
        if ($line.Contains($MarkBegin)) { $skip = $true }
        if (-not $skip) { $out.Add($line) }
        if ($line.Contains($MarkEnd))   { $skip = $false }
    }
    return ($out -join "`n")
}

# Idempotente por marcador: reinstalar troca o bloco em vez de empilhar outro.
function Set-Pointer {
    param([string] $Path)
    if ($DryRun) { Write-Step "[dry-run] escreveria o bloco em $Path"; return }
    $existing = ''
    $had = $false
    if (Test-Path -LiteralPath $Path) {
        $existing = Get-Content -LiteralPath $Path -Raw
        if ($null -eq $existing) { $existing = '' }
        if ($existing.Contains($MarkBegin)) {
            $existing = Remove-Block $existing
            $had = $true
        }
    }
    $existing = $existing.TrimEnd()
    if ($existing.Length -gt 0) { $existing = $existing + "`n`n" }
    Write-TextFile -Path $Path -Text ($existing + (Get-Block) + "`n")
    if ($had) { Write-Step "bloco atualizado em $Path" }
    else      { Write-Step "bloco escrito em $Path" }
}

function Clear-Pointer {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $text = Get-Content -LiteralPath $Path -Raw
    if ($null -eq $text -or -not $text.Contains($MarkBegin)) { return }
    if ($DryRun) { Write-Step "[dry-run] removeria o bloco de $Path"; return }
    $rest = (Remove-Block $text)
    if ($rest.Trim().Length -eq 0) {
        Remove-Item -LiteralPath $Path -Force
        Write-Step "$Path removido (estava vazio depois da remocao do bloco)"
    } else {
        Write-TextFile -Path $Path -Text ($rest.TrimEnd() + "`n")
        Write-Step "bloco removido de $Path"
    }
}

function Set-CursorRule {
    $rule = Join-Path (Join-Path (Join-Path $root '.cursor') 'rules') 'lgpd-scan.mdc'
    if ($DryRun) { Write-Step "[dry-run] escreveria $rule"; return }
    $header = @"
---
description: Auditoria de conformidade LGPD, ANPD e ECA Digital a partir do codigo-fonte, com evidencia em arquivo:linha
alwaysApply: false
---

"@
    Write-TextFile -Path $rule -Text ($header + (Get-Block) + "`n")
    Write-Step "regra escrita em $rule"
}

function Copy-Skill {
    if ($DryRun) { Write-Step "[dry-run] copiaria a skill para $skillDir"; return }
    New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
    foreach ($item in @('SKILL.md', 'README.md', 'COMO-USAR.md', 'CHANGELOG.md', 'LICENSE',
                        'scripts', 'references')) {
        $source = Join-Path $src $item
        if (-not (Test-Path -LiteralPath $source)) { continue }
        $target = Join-Path $skillDir $item
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
        Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
    }
    # O harness de teste pertence ao repositorio da skill, nao a instalacao: sem
    # tests\ ao lado ele nao roda. __pycache__ e da maquina de quem empacotou.
    foreach ($junk in @('scripts\run_tests.py', 'scripts\__pycache__')) {
        $path = Join-Path $skillDir $junk
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    }
    Write-Step "skill em $skillDir"
}

function Remove-EmptyDir {
    param([string] $Path)
    if ($DryRun) { return }
    if (-not (Test-Path -LiteralPath $Path)) { return }
    if (@(Get-ChildItem -LiteralPath $Path -Force).Count -eq 0) {
        Remove-Item -LiteralPath $Path -Force
    }
}

if ($Uninstall) {
    Write-Info "desinstalando lgpd-scan (escopo $Scope)"
    Clear-Pointer (Join-Path $root 'AGENTS.md')
    Clear-Pointer (Join-Path $root 'GEMINI.md')
    $rule = Join-Path (Join-Path (Join-Path $root '.cursor') 'rules') 'lgpd-scan.mdc'
    if ((Test-Path -LiteralPath $rule) -and -not $DryRun) { Remove-Item -LiteralPath $rule -Force }
    if ((Test-Path -LiteralPath $skillDir) -and -not $DryRun) {
        Remove-Item -LiteralPath $skillDir -Recurse -Force
    }
    Remove-EmptyDir (Join-Path (Join-Path $root '.cursor') 'rules')
    Remove-EmptyDir (Join-Path $root '.cursor')
    Remove-EmptyDir (Split-Path -Parent $skillDir)
    Remove-EmptyDir (Split-Path -Parent (Split-Path -Parent $skillDir))
    Write-Info ''
    Write-Info 'pronto. O que a skill gerou no projeto (RELATORIO-LGPD.md, ROPA.md, .lgpd-scan\)'
    Write-Info 'continua no lugar de proposito - sao seus documentos, nao arquivos do instalador.'
    return
}

Write-Info "instalando lgpd-scan $Version"
Write-Info "  de:   $src"
Write-Info "  para: $root (escopo $Scope)"
Write-Info ''
Copy-Skill

$didAgentsMd = $false
foreach ($target in $targets) {
    switch ($target) {
        'claude' {
            Write-Info 'claude code: a pasta de skill ja e o mecanismo nativo, nada mais a fazer'
        }
        { $_ -eq 'codex' -or $_ -eq 'opencode' } {
            Write-Info "${target}: usa AGENTS.md"
            if (-not $didAgentsMd) {
                Set-Pointer (Join-Path $root 'AGENTS.md')
                $didAgentsMd = $true
            } else {
                Write-Step '(mesmo AGENTS.md, ja escrito acima)'
            }
        }
        'gemini' { Write-Info 'gemini cli:'; Set-Pointer (Join-Path $root 'GEMINI.md') }
        'cursor' { Write-Info 'cursor:';     Set-CursorRule }
    }
}

# O coletor e o verificador sao Python puro. Sem python3 no PATH nada disso roda, e e
# melhor dizer agora do que na primeira auditoria.
$python = $null
foreach ($candidate in @('python3', 'python', 'py')) {
    if (Test-Cmd $candidate) { $python = $candidate; break }
}
if (-not $python) {
    Write-Note 'python nao encontrado no PATH -- scripts/collect.py nao vai rodar sem ele'
} else {
    $reported = & $python -c "import sys; print('ok' if sys.version_info >= (3,8) else sys.version.split()[0])" 2>$null
    if ($reported -ne 'ok') { Write-Note "o coletor pede python 3.8+ e aqui respondeu: $reported" }
}

Write-Info ''
Write-Info 'pronto. Para usar, peca ao agente: "audita este projeto para a LGPD".'
Write-Info "Direto, sem agente:  python $skillDir\scripts\collect.py ."
