#!/usr/bin/env sh
#
# lgpd-scan installer -- macOS, Linux, WSL, Git Bash.
#
#   ./install.sh                      # instala para todos os agentes detectados, no projeto atual
#   ./install.sh --agent claude       # so o Claude Code
#   ./install.sh --scope user         # instala para o usuario (~), nao para o projeto
#   ./install.sh --dest ../outro-repo # instala em outro projeto
#   ./install.sh --dry-run            # mostra o que faria, sem escrever nada
#   ./install.sh --uninstall          # remove o que este script instalou
#
# Uma honestidade que vale dizer aqui em cima, porque muda a expectativa: so o Claude
# Code tem mecanismo nativo de skill. Para os outros quatro agentes, o que este script
# instala e a pasta da skill mais um ponteiro no arquivo de contexto que aquele agente
# ja le (AGENTS.md, GEMINI.md, .cursor/rules). Funciona -- o agente le o SKILL.md e
# segue -- mas nao e a mesma coisa que uma skill registrada, e um instalador que
# finge o contrario so consegue decepcionar na primeira vez que o usuario olha.
#
# POSIX sh de proposito: bash 3 do macOS, dash do Debian e o sh do Git Bash.

set -eu

VERSION="0.6.0"
MARK_BEGIN="<!-- lgpd-scan:begin -->"
MARK_END="<!-- lgpd-scan:end -->"

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$(pwd)"
SCOPE="project"
AGENTS=""
DRY=0
FORCE=0
UNINSTALL=0

log()  { printf '%s\n' "$*"; }
warn() { printf 'aviso: %s\n' "$*" >&2; }
die()  { printf 'erro: %s\n' "$*" >&2; exit 1; }
run()  { if [ "$DRY" -eq 1 ]; then log "  [dry-run] $*"; else "$@"; fi; }

usage() {
  sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --agent|-a)   AGENTS="${AGENTS} $2"; shift 2 ;;
    --agent=*)    AGENTS="${AGENTS} ${1#*=}"; shift ;;
    --scope|-s)   SCOPE="$2"; shift 2 ;;
    --scope=*)    SCOPE="${1#*=}"; shift ;;
    --dest|-d)    DEST="$2"; shift 2 ;;
    --dest=*)     DEST="${1#*=}"; shift ;;
    --from)       SRC="$2"; shift 2 ;;
    --dry-run|-n) DRY=1; shift ;;
    --force|-f)   FORCE=1; shift ;;
    --uninstall)  UNINSTALL=1; shift ;;
    --version)    log "lgpd-scan ${VERSION}"; exit 0 ;;
    -h|--help)    usage ;;
    *)            die "opcao desconhecida: $1 (use --help)" ;;
  esac
done

[ -f "${SRC}/SKILL.md" ] || die "nao achei SKILL.md em ${SRC} — rode de dentro da pasta da skill ou use --from"

case "$SCOPE" in
  project) ROOT="$(cd "$DEST" 2>/dev/null && pwd)" || die "pasta de destino nao existe: $DEST" ;;
  user)    ROOT="${HOME}" ;;
  *)       die "escopo invalido: $SCOPE (use project ou user)" ;;
esac

# --------------------------------------------------------------------------
# Deteccao
# --------------------------------------------------------------------------
# Um agente conta como presente quando ha rastro dele no destino ou o binario esta no
# PATH. Sem rastro nenhum, o padrao e instalar so para o Claude Code: escrever
# AGENTS.md e .cursor/rules num repositorio que nunca usou aquelas ferramentas e
# poluicao, nao conveniencia.

has_cmd() { command -v "$1" >/dev/null 2>&1; }

# if explicito em vez de `[ a ] || [ b ] || cmd && found=...`: naquela forma, quando
# as tres condicoes falham o status da linha inteira e 1, e com `set -e` isso mata o
# script num caminho que nao tem nada de errado -- o agente simplesmente nao esta ali.
detect() {
  found=""
  if [ -d "${ROOT}/.claude" ] || [ -d "${HOME}/.claude" ] || has_cmd claude; then
    found="${found} claude"
  fi
  if [ -f "${ROOT}/AGENTS.md" ] || [ -d "${ROOT}/.codex" ] || has_cmd codex; then
    found="${found} codex"
  fi
  if [ -f "${ROOT}/GEMINI.md" ] || [ -d "${ROOT}/.gemini" ] || has_cmd gemini; then
    found="${found} gemini"
  fi
  if [ -d "${ROOT}/.cursor" ] || has_cmd cursor; then
    found="${found} cursor"
  fi
  if [ -d "${ROOT}/.opencode" ] || has_cmd opencode; then
    found="${found} opencode"
  fi
  if [ -z "$found" ]; then found=" claude"; fi
  printf '%s' "$found"
}

if [ -z "${AGENTS# }" ]; then
  AGENTS="$(detect)"
  log "agentes detectados:${AGENTS}"
fi
case " ${AGENTS} " in *" all "*) AGENTS="claude codex gemini cursor opencode" ;; esac

# --------------------------------------------------------------------------
# Copia da skill
# --------------------------------------------------------------------------
# Uma copia, varios ponteiros. Cinco copias da mesma pasta divergem na primeira
# atualizacao e ai nenhuma delas e a atual.

if [ "$SCOPE" = "user" ]; then
  SKILL_DIR="${HOME}/.claude/skills/lgpd-scan"
else
  SKILL_DIR="${ROOT}/.claude/skills/lgpd-scan"
fi

copy_skill() {
  if [ -d "$SKILL_DIR" ] && [ "$FORCE" -eq 0 ] && [ "$DRY" -eq 0 ]; then
    log "  ja existe, atualizando: ${SKILL_DIR}"
  fi
  run mkdir -p "$SKILL_DIR"
  for item in SKILL.md README.md COMO-USAR.md CHANGELOG.md LICENSE scripts references; do
    [ -e "${SRC}/${item}" ] || continue
    if [ -d "${SRC}/${item}" ]; then
      run rm -rf "${SKILL_DIR}/${item}"
      run cp -R "${SRC}/${item}" "${SKILL_DIR}/${item}"
    else
      run cp "${SRC}/${item}" "${SKILL_DIR}/${item}"
    fi
  done
  # O harness de teste e a suite pertencem ao repositorio da skill, nao a instalacao:
  # sem tests/ ao lado ele nao roda, e um script que so sabe falhar na pasta do usuario
  # e pior que a ausencia dele. __pycache__ e da maquina de quem empacotou.
  run rm -f "${SKILL_DIR}/scripts/run_tests.py"
  run rm -rf "${SKILL_DIR}/scripts/__pycache__"
}

# Caminho que o ponteiro mostra. Relativo quando a skill esta dentro do projeto,
# porque o arquivo de contexto e versionado e um caminho absoluto de outra maquina
# nao ajuda ninguem.
pointer_path() {
  case "$SKILL_DIR" in
    "${ROOT}"/*) printf '%s' "${SKILL_DIR#${ROOT}/}" ;;
    *)           printf '%s' "$SKILL_DIR" ;;
  esac
}

block() {
  cat <<BLOCK
${MARK_BEGIN}
## lgpd-scan — conformidade LGPD a partir do codigo

Quando a conversa mencionar LGPD, adequacao a LGPD, protecao de dados, dados
pessoais, privacidade, DPO, encarregado, ANPD, RIPD, ROPA, DPIA, ECA Digital,
verificacao de idade, ou pedir revisao de schema, migration, rota ou fluxo de
autenticacao em busca de problema de privacidade -- inclusive "este projeto esta
em conformidade?" sem dizer LGPD -- leia \`$(pointer_path)/SKILL.md\` e siga o que
esta la, do passo 1 ao 7.

Nao responda de memoria sobre a conformidade deste repositorio: a skill existe
porque a resposta tem de vir do codigo, com \`arquivo:linha\` e o trecho citado.

lgpd-scan ${VERSION} · instalado por install.sh · nao edite dentro dos marcadores
${MARK_END}
BLOCK
}

# Idempotente por marcador: reinstalar troca o bloco em vez de empilhar outro.
write_pointer() {
  target="$1"
  if [ "$DRY" -eq 1 ]; then
    log "  [dry-run] escreveria o bloco em ${target}"
    return 0
  fi
  mkdir -p "$(dirname "$target")"
  if [ -f "$target" ] && grep -qF "$MARK_BEGIN" "$target" 2>/dev/null; then
    tmp="${target}.lgpd-scan.tmp"
    awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
      index($0,b) { skip=1 }
      !skip { print }
      index($0,e) { skip=0 }
    ' "$target" > "$tmp"
    printf '\n' >> "$tmp"
    block >> "$tmp"
    mv "$tmp" "$target"
    log "  bloco atualizado em ${target}"
  else
    if [ -f "$target" ]; then printf '\n' >> "$target"; fi
    block >> "$target"
    log "  bloco escrito em ${target}"
  fi
}

remove_pointer() {
  target="$1"
  [ -f "$target" ] || return 0
  grep -qF "$MARK_BEGIN" "$target" 2>/dev/null || return 0
  if [ "$DRY" -eq 1 ]; then log "  [dry-run] removeria o bloco de ${target}"; return 0; fi
  tmp="${target}.lgpd-scan.tmp"
  awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
    index($0,b) { skip=1 }
    !skip { print }
    index($0,e) { skip=0 }
  ' "$target" > "$tmp"
  mv "$tmp" "$target"
  # Se o que sobrou e so espaco em branco, o arquivo era nosso: foi este script que o
  # criou, e deixar um GEMINI.md vazio para tras e o tipo de sujeira que faz o usuario
  # desconfiar do resto da desinstalacao.
  if [ -z "$(tr -d '[:space:]' < "$target")" ]; then
    rm -f "$target"
    log "  ${target} removido (estava vazio depois da remocao do bloco)"
  else
    log "  bloco removido de ${target}"
  fi
}

prune_dir() {
  [ -d "$1" ] || return 0
  if [ "$DRY" -eq 1 ]; then return 0; fi
  rmdir "$1" 2>/dev/null || true
}

cursor_rule() {
  if [ "$DRY" -eq 1 ]; then log "  [dry-run] escreveria ${ROOT}/.cursor/rules/lgpd-scan.mdc"; return 0; fi
  mkdir -p "${ROOT}/.cursor/rules"
  cat > "${ROOT}/.cursor/rules/lgpd-scan.mdc" <<MDC
---
description: Auditoria de conformidade LGPD, ANPD e ECA Digital a partir do codigo-fonte, com evidencia em arquivo:linha
alwaysApply: false
---

$(block)
MDC
  log "  regra escrita em ${ROOT}/.cursor/rules/lgpd-scan.mdc"
}

# --------------------------------------------------------------------------
# Execucao
# --------------------------------------------------------------------------

if [ "$UNINSTALL" -eq 1 ]; then
  log "desinstalando lgpd-scan (escopo ${SCOPE})"
  remove_pointer "${ROOT}/AGENTS.md"
  remove_pointer "${ROOT}/GEMINI.md"
  if [ -f "${ROOT}/.cursor/rules/lgpd-scan.mdc" ]; then
    run rm -f "${ROOT}/.cursor/rules/lgpd-scan.mdc"
  fi
  if [ -d "$SKILL_DIR" ]; then
    run rm -rf "$SKILL_DIR"
  fi
  prune_dir "${ROOT}/.cursor/rules"
  prune_dir "${ROOT}/.cursor"
  prune_dir "$(dirname "$SKILL_DIR")"
  prune_dir "$(dirname "$(dirname "$SKILL_DIR")")"
  log ""
  log "pronto. O que a skill gerou no projeto (RELATORIO-LGPD.md, ROPA.md, .lgpd-scan/)"
  log "continua no lugar de proposito — sao seus documentos, nao arquivos do instalador."
  exit 0
fi

log "instalando lgpd-scan ${VERSION}"
log "  de:   ${SRC}"
log "  para: ${ROOT} (escopo ${SCOPE})"
log ""
copy_skill
log "  skill em ${SKILL_DIR}"

# Codex e OpenCode leem o mesmo AGENTS.md; escrever duas vezes daria no mesmo por
# causa do marcador, mas o log ficaria dizendo que fez duas coisas quando fez uma.
DID_AGENTS_MD=0

for agent in $AGENTS; do
  case "$agent" in
    claude)
      log "claude code: a pasta de skill ja e o mecanismo nativo, nada mais a fazer" ;;
    codex|opencode)
      log "${agent}: usa AGENTS.md"
      if [ "$DID_AGENTS_MD" -eq 0 ]; then
        write_pointer "${ROOT}/AGENTS.md"
        DID_AGENTS_MD=1
      else
        log "  (mesmo AGENTS.md, ja escrito acima)"
      fi ;;
    gemini)   log "gemini cli:"; write_pointer "${ROOT}/GEMINI.md" ;;
    cursor)   log "cursor:";   cursor_rule ;;
    ""|" ")   ;;
    *)        warn "agente desconhecido, ignorado: ${agent}" ;;
  esac
done

if has_cmd python3; then
  PYOK="$(python3 -c 'import sys; print("ok" if sys.version_info >= (3,8) else sys.version.split()[0])' 2>/dev/null || echo ausente)"
  if [ "$PYOK" != "ok" ]; then
    warn "o coletor pede python3 >= 3.8 e aqui respondeu: ${PYOK}"
  fi
else
  warn "python3 nao encontrado no PATH — o coletor (scripts/collect.py) nao vai rodar sem ele"
fi

log ""
log "pronto. Para usar, peca ao agente: \"audita este projeto para a LGPD\"."
log "Direto, sem agente:  python3 ${SKILL_DIR}/scripts/collect.py ."
