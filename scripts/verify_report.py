#!/usr/bin/env python3
"""
lgpd-scan document verifier.

Checks that a generated document keeps the promise it makes on its first page: that
every claim points at a real line of real code.

The whole proposition of this skill is that its output is checkable. A citation
pointing at a file that does not exist, or at line 340 of a 120-line file, breaks
that proposition more thoroughly than a missed finding would -- a developer who
catches the tool inventing evidence once will never trust it again, and will be
right not to. This script is the cheap mechanical check that stops that from
reaching them.

It verifies four kinds of document, because generating a ROPA nobody checked is
the same failure as writing a report nobody checked:

    relatorio   RELATORIO-LGPD.md   the audit report
    ropa        ROPA.md             registro das operacoes, art. 37
    ripd        RIPD.md             relatorio de impacto, art. 38
    dpa         DPA-MINUTA*.md      minuta de clausulas com operador, art. 39

The kind is detected from the filename and the title; --kind forces it.

    python3 scripts/verify_report.py RELATORIO-LGPD.md --repo .
    python3 scripts/verify_report.py ROPA.md --repo . --kind ropa

Run it after writing the document, before handing it over.

Python 3.8+, standard library only.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402
import report_data  # noqa: E402

# Extensions a citation may plausibly point at. Anything else that looks like
# `word.word:123` is prose -- "Art. 18:" and "https://x.y:8080" must not be treated
# as broken citations.
CITABLE_EXTS = {
    "ts", "tsx", "js", "jsx", "mjs", "cjs", "java", "kt", "kts", "py", "rb", "php",
    "go", "rs", "cs", "scala", "groovy", "sql", "prisma", "graphql", "gql", "json",
    "yml", "yaml", "xml", "properties", "toml", "ini", "conf", "env", "sh", "tf",
    "gradle", "html", "vue", "svelte", "md", "txt", "lock",
}

CITATION = re.compile(
    r"(?<![\w/])"
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_\-./\\]*\.(?P<ext>[A-Za-z0-9]{1,10}))"
    r":(?P<line>\d+)(?:-(?P<end>\d+))?"
)

INLINE_CODE = re.compile(r"`([^`]{2,120})`")
# Three characters, not four: a citation like `@Get('me')` carries only the token
# "Get", and dropping it means the wrong-line check silently never runs on exactly
# the short decorator snippets these reports quote most.
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")

REQUIREMENT_HEADING = re.compile(
    r"^#{2,4}\s*(?P<id>R\d{2})\s*[—\-–]\s*(?P<title>[^·|\n]+?)\s*(?:·|\|)\s*"
    r"(?P<status>[^·|\n]+?)\s*(?:(?:·|\|).*)?$"
)

NEEDS_EVIDENCE = {"nao atendido", "parcial"}

# Uma lacuna se sustenta de dois jeitos: apontando o codigo que falha, ou dizendo o
# que foi procurado e nao existe. Exigir citacao das duas empurra para o pior
# resultado possivel -- o relatorio cita uma linha qualquer so para satisfazer o
# verificador, e ai a citacao deixa de significar o que ela promete. Encontrado
# escrevendo o fixture do report.json: "nenhuma coluna de consentimento em lugar
# nenhum" e o achado, e nao ha o que citar.
ABSENCE_CLAIM = re.compile(
    r"(?i)(nenhum|nao (ha|existe|encontr|retorn|aparec)|"
    r"ausen(te|cia)|inexistente|nada (foi )?(encontrad|retorn)|"
    r"busca por .{0,60} (nao|sem)|em lugar nenhum)")

# A report that reproduces a live credential turns the report itself into the leak.
LEAKED_SECRET = [
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("credencial de nuvem", re.compile(
        r"(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{20,}|sk-[A-Za-z0-9]{20,}|"
        r"ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})")),
]

# A risk block in a RIPD asserts something about the data subject; the rule is the
# same as a finding's -- assert it and cite it, or do not assert it.
RISK_HEADING = re.compile(r"^#{2,4}\s*(?P<id>RISCO\s*\d+)\b(?P<title>.*)$")

# Template holes. A document shipped with `[INSERIR NOME]` or `{nome do projeto}` in
# it is the R15 failure the tool itself reports -- the policy sending the data subject
# to a channel that was never filled in. Catching it in our own output is the least we
# can do before reporting it in someone else's.
PLACEHOLDERS = [
    ("marcador de modelo", re.compile(
        r"(?i)(\[\s*e-?mail\s*\]|\[\s*inserir[^\]]{0,40}\]|"
        r"\[\s*preencher[^\]]{0,40}\]|\[\s*nome[^\]]{0,30}\]|"
        r"\[\s*cnpj[^\]]{0,20}\]|\[\s*razao social[^\]]{0,20}\]|"
        r"<\s*inserir[^>]{0,40}>|<\s*preencher[^>]{0,40}>|"
        r"\{\{\s*(?:inserir|preencher|informar|nome|e-?mail|empresa|razao|cnpj|cpf|dpo|"
        r"encarregado|endereco|telefone|definir|xxx|todo)[^}]{0,40}\}\})")),
    # Caixa alta obrigatoria em TODO e FIXME: "todo" e palavra comum em portugues, e
    # a primeira rodada real deste verificador acusou "desloga todo mundo" de ser
    # marcador de modelo.
    ("texto de exemplo",
     re.compile(r"(?i)(lorem ipsum|[:=]\s*a\s+definir"
                r"|(?-i:\bTODO\b|\bFIXME\b|\bXXXX+\b))")),
    # A brace hole from the template body: `{nome do projeto}`, `{DD/MM/AAAA}`. Only
    # outside code spans, which is why the scan strips those first -- `if (x) {` and
    # `${user.id}` are code, not an unfilled field. And a SINGLE pair: `{nome do projeto}`. Excluding the doubled form
    # keeps a report that quotes an Angular or Handlebars template in prose --
    # `{{ versao }}` -- from being accused of shipping an unfilled field.
    ("campo do modelo nao preenchido", re.compile(
        r"(?<![${\w])\{\s*[A-Za-zÀ-ÿ][^{}`|]{2,60}\}(?!\})")),
]

# A table row either cites evidence or says out loud that there is none. This is the
# rule that makes a generated ROPA worth more than a form: a row asserting a
# processing activity with neither a citation nor a declared gap is a row somebody
# wrote from memory, and in a document the controller signs that is the whole risk.
NO_EVIDENCE_CLAIM = re.compile(
    r"(?i)(⚠|a preencher|nao verificavel|a avaliar|ausente|nenhum|inexistente|"
    r"nao localizad|nao encontrad|nao se aplica|\bn/?a\b|pendente|^\s*[-—–]\s*$)")

TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")

FENCE = re.compile(r"^\s*(```|~~~)")


def _strip_code(line):
    """Drop inline code spans, so a placeholder scan never reads code as prose."""
    return INLINE_CODE.sub(" ", line)


# --------------------------------------------------------------------------
# Document profiles
# --------------------------------------------------------------------------
# Four documents, four sets of promises. The report promises that every finding is
# located; the ROPA promises that every processing activity was found in the code;
# the RIPD promises that every risk has a trace; the DPA promises that its annexes
# were levantados and not copied. One verifier, because the failure mode is identical
# in all four and a document nobody checked is what this skill exists to avoid.

DOC_PROFILES = {
    "relatorio": {
        "label": "relatório de conformidade",
        "filename": re.compile(r"(?i)relatorio.*lgpd|lgpd.*relatorio"),
        "title": re.compile(r"(?i)relat[oó]rio de conformidade"),
        "required_sections": [
            ("Limitações desta análise", ("limitacoes",)),
            ("Não verificável a partir do código", ("nao verificavel",)),
        ],
        "evidence_heading": REQUIREMENT_HEADING,
        "needs_evidence": lambda m: (
            deaccent(m.group("status")).strip().lower() in NEEDS_EVIDENCE),
        "break_heading": re.compile(r"^## "),
        "evidence_tables": [],
        "min_citations": 1,
    },
    "ropa": {
        "label": "ROPA (art. 37)",
        "filename": re.compile(r"(?i)\bropa\b|registro.*operac"),
        "title": re.compile(r"(?i)registro das opera|\bropa\b"),
        "required_sections": [
            ("O que este registro não apura", ("nao apura", "limitac")),
            ("Medidas de segurança", ("medidas de seguranca",)),
            ("Retenção e eliminação", ("retenc",)),
        ],
        "evidence_heading": None,
        "needs_evidence": None,
        "break_heading": re.compile(r"^#{2,} "),
        # A ROPA's operations table is the document. Its other tables describe it.
        "evidence_tables": [
            (re.compile(r"(?i)^#{2,}.*(opera[cç]|tratamento)"), "operações de tratamento"),
            (re.compile(r"(?i)^#{2,}.*dados pessoais por"), "dados pessoais por entidade"),
        ],
        # A ROPA with no citation at all was not levantado do código, whatever the
        # header says. There is no honest version of this document with zero traces.
        "min_citations": 3,
    },
    "ripd": {
        "label": "RIPD (art. 38)",
        "filename": re.compile(r"(?i)\bripd\b|impacto"),
        "title": re.compile(r"(?i)relat[oó]rio de impacto|\bripd\b"),
        "required_sections": [
            ("Limitações", ("limitac",)),
            ("Riscos identificados", ("risco",)),
            ("Medidas de segurança e salvaguardas", ("medidas de seguranca", "salvaguard")),
        ],
        "evidence_heading": RISK_HEADING,
        "needs_evidence": lambda m: True,
        "break_heading": re.compile(r"^#{2,} "),
        "evidence_tables": [
            (re.compile(r"(?i)^#{2,}.*(medidas de seguran|tipos de dado|"
                        r"metodologia de coleta|direitos dos titulares)"),
             "tabela de apuração"),
        ],
        "min_citations": 2,
    },
    "politica": {
        "label": "politica de privacidade gerada",
        "filename": re.compile(r"(?i)politica|privacidade|privacy"),
        "title": re.compile(r"(?i)politica de privacidade|aviso de privacidade"),
        "required_sections": [
            ("Direitos do titular", ("seus direitos", "direitos do titular")),
            ("Dados tratados", ("quais dados", "dados que trat", "dados coletad")),
            ("Contato do encarregado", ("encarregado", "dpo")),
        ],
        "evidence_heading": None,
        "needs_evidence": None,
        "break_heading": re.compile(r"^#{2,} "),
        # Documento publico, lido por titular: citacao de arquivo:linha aqui seria
        # absurda, e expoe a estrutura interna sem necessidade. A evidencia vai no
        # anexo separado, que passa pelo verificador como qualquer outro documento.
        "evidence_tables": [],
        "min_citations": 0,
        "promises": True,
    },
    "dpa": {
        "label": "minuta de cláusulas com operador",
        "filename": re.compile(r"(?i)\bdpa\b|operador|clausul"),
        "title": re.compile(r"(?i)minuta de clausul|clausulas de tratamento|\bdpa\b"),
        "required_sections": [
            ("Aviso de minuta para revisão jurídica", ("revisao juridica",)),
            ("Anexo I — atividades de tratamento", ("anexo i",)),
            ("Anexo II — medidas técnicas", ("anexo ii",)),
        ],
        "evidence_heading": None,
        "needs_evidence": None,
        "break_heading": re.compile(r"^#{2,} "),
        # The annexes are the only part of a DPA this tool can claim to have found.
        # If they carry no evidence, what was generated is a boilerplate contract with
        # a tool's name on it, which is worse than nothing.
        "evidence_tables": [
            (re.compile(r"(?i)^#{2,}\s*anexo\s+(i|ii)\b"), "anexo levantado do código"),
        ],
        "min_citations": 2,
    },
}


def detect_kind(path, lines):
    """Which of the four documents is this? Filename first, then the title.

    Getting this wrong matters in one direction only: a ROPA verified as a report
    skips the row-evidence check and passes clean, which is exactly the outcome the
    check exists to prevent. So an ambiguous name loses to an explicit title, and
    --kind overrides both.
    """
    base = os.path.basename(path)
    title = next((l for l in lines[:40] if l.startswith("# ")), "")
    title = deaccent(title)
    for kind in ("ropa", "ripd", "dpa", "politica", "relatorio"):
        if DOC_PROFILES[kind]["title"].search(title):
            return kind
    for kind in ("ropa", "ripd", "dpa", "politica", "relatorio"):
        if DOC_PROFILES[kind]["filename"].search(deaccent(base)):
            return kind
    return "relatorio"

SNIPPET_WINDOW = 6

# A line made only of punctuation can never be evidence of anything. Citing one is
# always a mistake, and an existence check alone waves it through.
TRIVIAL_LINE = re.compile(r"^[\s{}()\[\];,.<>*/+-]*$")


def deaccent(text):
    table = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
                          "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")
    return text.translate(table)


def read_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().splitlines()
    except OSError:
        return None


def resolve(repo, cited):
    """Map a cited path onto disk. Deliberately strict -- no fuzzy basename search."""
    cited = cited.replace("\\", "/").lstrip("./")
    for candidate in (os.path.join(repo, *cited.split("/")), cited):
        if os.path.isfile(candidate):
            return candidate
    return None


def _span_with_backticks(line, match):
    """A citation's extent including the backticks that usually wrap it.

    Cutting the scope in the middle of a backtick pair desynchronises the inline-code
    parser downstream: every following snippet gets paired with the wrong delimiter
    and vanishes. The boundary has to fall outside the pair.
    """
    start, end = match.start(), match.end()
    if start > 0 and line[start - 1] == "`":
        start -= 1
    if end < len(line) and line[end] == "`":
        end += 1
    return start, end


def citation_scope(report_line, match):
    """The part of the line whose quoted snippets belong to THIS citation.

    A line often carries more than one citation -- a table row, or a sentence citing
    two files. Pairing every snippet on the line with every citation produced a
    stream of false alarms, so a citation only owns the text between its neighbours,
    clipped to its own cell when the line is a table row.
    """
    start, end = 0, len(report_line)
    for other in CITATION.finditer(report_line):
        if other.start() == match.start():
            continue
        o_start, o_end = _span_with_backticks(report_line, other)
        if o_end <= match.start():
            start = max(start, o_end)
        elif o_start >= match.end():
            end = min(end, o_start)

    if report_line.lstrip().startswith("|"):
        cell_start = report_line.rfind("|", 0, match.start())
        cell_end = report_line.find("|", match.end())
        if cell_start != -1:
            start = max(start, cell_start + 1)
        if cell_end != -1:
            end = min(end, cell_end)
        # A table row's other cells describe the row, not the cited line -- but when
        # the citation sits alone in its cell there is nothing to check against, so
        # fall back to the whole row rather than reporting it as unquoted.
        own = [sp for sp in INLINE_CODE.findall(report_line[start:end])
               if not CITATION.search(sp)]
        if not own:
            start, end = 0, len(report_line)
        return report_line[start:end]

    # Markdown wraps prose at arbitrary columns, so a line routinely ends one
    # sentence and begins another. A snippet from the next sentence describes a
    # different citation entirely -- clip to the sentence this one lives in.
    before = report_line.rfind(". ", start, match.start())
    if before != -1:
        start = before + 2
    after = report_line.find(". ", match.end(), end)
    if after != -1:
        end = after

    return report_line[start:end]


def _span_matches(tokens, context):
    """Does this quoted span really describe the cited line?

    Any-token matching was too weak in one specific and dangerous way: a claim like
    `argon2.hash(dto.senha)` against a line that reads `bcrypt.hash(dto.senha, 10)`
    passed, because three of its four tokens were there. The one word that carried
    the claim -- and that was wrong -- was the one that did not match.

    So the span's longest token has to be present. That is where the meaning sits
    (`rejectUnauthorized`, `politica_aceita_em`, `argon2`), while the short ones are
    the language's furniture. When several tokens tie for longest, any of them
    counts: a tie means no single word carries the claim.

    Measured before adopting: on the pilot report and a real generated ROPA this
    produced exactly the same warnings as any-token matching, and caught a
    substituted-keyword mutation that any-token waved through.
    """
    distinct = set(tokens)
    if not distinct:
        return False
    longest = max(len(t) for t in distinct)
    return any(t in context for t in distinct if len(t) == longest)


def check_snippet(report_line, match, source_lines, line_no):
    """Did the report quote something that is actually near the cited line?

    Returns ("ok"|"sem_trecho"|"divergente", detail). One corroborating snippet is
    enough: a report legitimately quotes a table name or a neighbouring identifier
    alongside the one that sits on the cited line, and demanding that all of them
    match turns ordinary prose into noise.
    """
    lo = max(0, line_no - 1 - SNIPPET_WINDOW)
    hi = min(len(source_lines), line_no + SNIPPET_WINDOW)
    context = deaccent(" ".join(source_lines[lo:hi])).lower()

    spans = [sp for sp in INLINE_CODE.findall(citation_scope(report_line, match))
             if not CITATION.search(sp)]
    checkable = []
    for span in spans:
        tokens = [t.lower() for t in TOKEN.findall(deaccent(span))]
        if tokens:
            checkable.append((span, tokens))

    if not checkable:
        return "sem_trecho", None
    if any(_span_matches(tokens, context) for _, tokens in checkable):
        return "ok", None
    quoted = checkable[0][0][:60]
    return "divergente", f"trecho `{quoted}` nao aparece perto da linha {line_no}"


def scan_placeholders(lines):
    """Template holes left in the finished document.

    Only outside fenced blocks and inline code: a report legitimately quotes
    `${user.id}` from the code it is auditing, and a document that describes the
    marker vocabulary would otherwise accuse itself.
    """
    found, in_fence = [], False
    for idx, line in enumerate(lines, start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        clean = _strip_code(line)
        for label, pattern in PLACEHOLDERS:
            hit = pattern.search(clean)
            if hit:
                found.append(f"documento:{idx}  {label}: {hit.group(0)[:48].strip()}")
                break
    return found


def scan_table_rows(lines, profile):
    """Rows that assert something with no evidence and no declared gap.

    A generated ROPA is only worth more than a filled-in form if its rows came from
    somewhere. This walks the tables the profile cares about and reports the rows
    that state a fact -- an operation, a field, a security measure -- while citing
    nothing and admitting nothing.
    """
    if not profile["evidence_tables"]:
        return []

    problems, active, label, in_fence = [], False, None, False
    for idx, line in enumerate(lines, start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if line.startswith("#"):
            active, label = False, None
            for pattern, name in profile["evidence_tables"]:
                if pattern.search(deaccent(line)):
                    active, label = True, name
                    break
            continue

        stripped = line.strip()
        if not stripped.startswith("|") or not active:
            continue
        if TABLE_SEPARATOR.match(stripped):
            continue
        # A header row is the one followed by the dashed separator. Recognising it
        # structurally rather than by position matters: an earlier version tracked
        # "have I passed the separator yet" and a blank line inside the section reset
        # it, so a detached row -- exactly what a hand-edited document produces --
        # was read as a new table's header and skipped without being checked.
        nxt = lines[idx].strip() if idx < len(lines) else ""
        if TABLE_SEPARATOR.match(nxt):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not any(cells):
            continue
        # A row whose only content is the template's own ellipsis or a filler row.
        if all(c in ("", "...", "…", "-", "—", "–") for c in cells):
            continue
        if CITATION.search(stripped):
            continue
        if NO_EVIDENCE_CLAIM.search(deaccent(stripped)):
            continue
        problems.append(f"documento:{idx}  [{label}] {cells[0][:44] or stripped[:44]}")
    return problems


def verify(report_path, repo, profile):
    report_lines = read_lines(report_path)
    if report_lines is None:
        sys.stderr.write(f"erro: nao consegui ler {report_path}\n")
        return None

    cache = {}
    errors, warnings, unquoted, ok_count = [], [], [], 0
    cited_files = set()

    for r_idx, r_line in enumerate(report_lines, start=1):
        for match in CITATION.finditer(r_line):
            if match.group("ext").lower() not in CITABLE_EXTS:
                continue
            before = r_line[:match.start()]
            if before.endswith(("://", "//")) or "http" in before[-8:].lower():
                continue

            cited = match.group("path")
            line_no = int(match.group("line"))
            where = f"documento:{r_idx}"

            if cited not in cache:
                resolved = resolve(repo, cited)
                cache[cited] = (resolved, read_lines(resolved) if resolved else None)
            resolved, source_lines = cache[cited]

            if resolved is None:
                errors.append(f"{where}  arquivo inexistente: {cited}")
                continue
            if source_lines is None:
                warnings.append(f"{where}  nao consegui abrir: {cited}")
                continue

            cited_files.add(cited)
            end = int(match.group("end") or line_no)
            if line_no < 1 or end > len(source_lines):
                errors.append(
                    f"{where}  {cited}:{line_no} fora do arquivo "
                    f"(tem {len(source_lines)} linhas)")
                continue

            if TRIVIAL_LINE.match(source_lines[line_no - 1]):
                errors.append(
                    f"{where}  {cited}:{line_no} aponta para linha vazia ou so "
                    f"com pontuacao — nao e evidencia de nada")
                continue

            verdict, detail = check_snippet(r_line, match, source_lines, line_no)
            if verdict == "divergente":
                warnings.append(f"{where}  {cited}:{line_no} — {detail}")
            elif verdict == "sem_trecho":
                unquoted.append(f"{where}  {cited}:{line_no}")
            ok_count += 1

    # Sections that assert a gap or a risk but cite nothing at all.
    uncited = []
    heading_rule = profile["evidence_heading"]
    if heading_rule is not None:
        current = None
        saw_citation = False
        for r_line in report_lines + ["## fim"]:
            heading = heading_rule.match(r_line.strip())
            if heading or profile["break_heading"].match(r_line):
                if current and not saw_citation:
                    uncited.append(current)
                current = None
                saw_citation = False
                if heading and profile["needs_evidence"](heading):
                    extra = (heading.groupdict().get("status") or "").strip()
                    current = (f"{heading.group('id')} ({extra})" if extra
                               else heading.group("id"))
                continue
            if current and (CITATION.search(r_line)
                            or ABSENCE_CLAIM.search(deaccent(r_line))):
                saw_citation = True

    body = deaccent("\n".join(report_lines)).lower()
    missing_sections = [
        label for label, keys in profile["required_sections"]
        if not any(k in body for k in keys)
    ]

    leaks = []
    for r_idx, r_line in enumerate(report_lines, start=1):
        for label, pattern in LEAKED_SECRET:
            if pattern.search(r_line):
                leaks.append(f"documento:{r_idx}  {label} reproduzida no texto")

    promises = []
    if profile.get("promises"):
        promises = check_promises(report_lines, repo)

    unsupported = []
    if ok_count < profile["min_citations"]:
        unsupported.append(
            f"o documento tem {ok_count} citacao(oes) de codigo e o minimo para um "
            f"{profile['label']} e {profile['min_citations']} — sem evidencia nenhuma, "
            f"isto foi escrito de memoria, nao levantado do repositorio")

    return {
        "kind": profile["label"],
        "ok": ok_count,
        "errors": errors,
        "warnings": warnings,
        "unquoted": unquoted,
        "uncited": uncited,
        "missing_sections": missing_sections,
        "leaks": leaks,
        "placeholders": scan_placeholders(report_lines),
        "rows": scan_table_rows(report_lines, profile),
        "unsupported": unsupported,
        "promises": promises,
        "files": len(cited_files),
        "data": None,
    }



# --------------------------------------------------------------------------
# Promessa x implementacao, na politica de privacidade
# --------------------------------------------------------------------------
# A skill inteira existe para nao creditar promessa como implementacao. Quando ela
# passa a GERAR a politica, a mesma regra vira uma restricao sobre a propria saida:
# a politica so promete o que o codigo entrega. Uma politica que promete um botao
# que nao existe nao e um texto ruim -- e a nao conformidade, documentada e
# publicada pelo controlador, e e exatamente o achado que o R15 levanta depois.

PROMISES = [
    ("exclusao da conta pelo titular",
     re.compile(r"(?i)(exclu|elimin|apag|delet|encerr|cancel)\w*\s+"
                r"(a\s+)?(sua\s+|seu\s+)?(conta|cadastro|perfil|dados)"),
     ("delete_route", "delete_route_alt")),
    ("exportacao ou portabilidade",
     re.compile(r"(?i)(export\w*|portabilidade|baix\w*\s+(os\s+)?seus\s+dados|"
                r"download\s+dos\s+dados)"),
     ("export_route",)),
    ("correcao pelo titular",
     re.compile(r"(?i)(corrig\w*|retific\w*|atualiz\w*)\s+"
                r"(os\s+|seus\s+|as\s+)?(dados|informacoes|cadastro)"),
     ("update_route",)),
    ("criptografia dos dados",
     re.compile(r"(?i)(criptograf\w*|cifrad\w*|encriptad\w*)"),
     ("encryption_at_rest", "password_hash_strong")),
    ("anonimizacao",
     re.compile(r"(?i)anonimiz\w*"),
     ("anonymization",)),
    ("verificacao de idade",
     re.compile(r"(?i)verific\w*\s+(a\s+)?idade|verificacao de idade"),
     ("age_verification_provider",)),
]

# "Voce pode solicitar a exclusao pelo canal do encarregado" e verdadeiro sem rota
# nenhuma: a lei garante o direito, nao o botao, e atendimento manual e legitimo. So
# a promessa de automacao precisa de lastro no codigo.
MEDIATED = re.compile(
    r"(?i)(solicit\w*|pedid\w*|requer\w*|mediante|entre em contato|fale conosco|"
    r"pelo canal|por e-?mail|atraves do encarregado|junto ao encarregado|"
    r"nos escrev\w*|abrir\w* (um )?chamado)")

SENTENCE = re.compile(r"(?<=[.;:!?])\s+|\n")


def check_promises(report_lines, repo):
    """O que a politica promete e o codigo nao entrega."""
    problems = []
    try:
        result = collect.scan(repo, max_hits=60)
    except Exception as exc:  # pragma: no cover - ambiente sem permissao de leitura
        return [f"nao consegui rodar o coletor para conferir as promessas: {exc}"]

    presentes = {name for name, hits in result["signals"].items() if hits}

    corpo, in_fence = [], False
    for line in report_lines:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            corpo.append(line)
    texto = deaccent("\n".join(corpo))

    for frase in SENTENCE.split(texto):
        frase = frase.strip()
        if len(frase) < 12:
            continue
        if MEDIATED.search(frase):
            continue
        for rotulo, padrao, sinais in PROMISES:
            if not padrao.search(frase):
                continue
            if any(sinal in presentes for sinal in sinais):
                continue
            problems.append(
                f"promete {rotulo} e nenhum sinal sustenta "
                f"({' ou '.join(sinais)}): \"{frase[:80]}\"")
    return problems


def check_evidence_item(item, repo, cache):
    """Uma evidencia do report.json conferida contra o arquivo real.

    Mesmas tres perguntas que se faz a uma citacao do markdown: o arquivo existe, a
    linha esta dentro dele, e o trecho citado aparece por ali. Se o JSON e o registro
    de maquina da auditoria, ele nao pode ter um padrao de prova mais baixo que o
    documento que as pessoas leem.
    """
    cited = str(item.get("file", ""))
    line_no = item.get("line")
    if cited not in cache:
        resolved = resolve(repo, cited)
        cache[cited] = (resolved, read_lines(resolved) if resolved else None)
    resolved, source_lines = cache[cited]

    if resolved is None:
        return f"arquivo inexistente: {cited}"
    if source_lines is None:
        return f"nao consegui abrir: {cited}"
    if not isinstance(line_no, int) or line_no < 1 or line_no > len(source_lines):
        return (f"{cited}:{line_no} fora do arquivo "
                f"(tem {len(source_lines)} linhas)")
    if TRIVIAL_LINE.match(source_lines[line_no - 1]):
        return (f"{cited}:{line_no} aponta para linha vazia ou so com pontuacao "
                f"— nao e evidencia de nada")

    snippet = (item.get("snippet") or "").strip()
    if not snippet:
        return f"{cited}:{line_no} sem trecho — a citacao fica inconferivel"

    lo = max(0, line_no - 1 - SNIPPET_WINDOW)
    hi = min(len(source_lines), line_no + SNIPPET_WINDOW)
    context = deaccent(" ".join(source_lines[lo:hi])).lower()
    tokens = [t.lower() for t in TOKEN.findall(deaccent(snippet))]
    if tokens and not _span_matches(tokens, context):
        return (f"{cited}:{line_no} — trecho `{snippet[:50]}` nao aparece perto "
                f"da linha")
    return None


def markdown_statuses(report_lines):
    """Os status que o relatorio em markdown declara, por requisito.

    Este parser existe para CONFERIR o JSON, nunca para substitui-lo. A diferenca
    importa: quando ele nao acha a secao de um requisito, isso e um achado sobre o
    relatorio, e nao um dado que se perdeu.
    """
    found = {}
    for line in report_lines:
        heading = REQUIREMENT_HEADING.match(line.strip())
        if heading:
            status = report_data.canonical_status(heading.group("status"))
            found.setdefault(heading.group("id"), status or
                             heading.group("status").strip())
    return found


def verify_data(data_path, repo, report_lines):
    """O report.json: valido, com evidencia real, e de acordo com o markdown."""
    result = {"path": data_path, "invalid": [], "citations": [], "divergence": [],
              "summary": None, "checked": 0}
    try:
        with open(data_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        result["invalid"].append(f"nao consegui ler o JSON: {exc}")
        return result

    result["invalid"] = report_data.validate(data)
    result["summary"] = report_data.summarise(data)

    # O registro de maquina vaza igual ao documento. Um `snippet` de segredo com o
    # valor literal transforma o report.json no vazamento, e ele costuma ser
    # commitado sem ninguem reler. A regra para o R09 e mascarar o valor e manter o
    # identificador: `DB_PASS=***` continua conferivel e nao carrega nada.
    for entry in data.get("requirements") or []:
        for item in entry.get("evidence") or []:
            if not isinstance(item, dict):
                continue
            texto = str(item.get("snippet") or "")
            for label, pattern in LEAKED_SECRET:
                if pattern.search(texto):
                    result["invalid"].append(
                        f"{entry.get('id')}: {label} reproduzida no snippet de "
                        f"{item.get('file')}:{item.get('line')} — mascare o valor "
                        f"e mantenha o identificador")

    cache = {}
    for entry in data.get("requirements") or []:
        rid = entry.get("id")
        for item in entry.get("evidence") or []:
            if not isinstance(item, dict):
                continue
            result["checked"] += 1
            problem = check_evidence_item(item, repo, cache)
            if problem:
                result["citations"].append(f"{rid}  {problem}")

    # O relatorio e o JSON sao dois registros da mesma auditoria. Se discordam, um
    # dos dois esta errado e nao da para saber qual -- entao os dois param.
    if report_lines is not None:
        no_markdown = markdown_statuses(report_lines)
        for entry in data.get("requirements") or []:
            rid = entry.get("id")
            json_status = report_data.canonical_status(entry.get("status"))
            if json_status == "Nao se aplica" and rid not in no_markdown:
                continue  # grupo inteiro fora de escopo pode sair em uma linha so
            if rid not in no_markdown:
                result["divergence"].append(
                    f"{rid}: esta no JSON como {json_status} e nao tem secao no "
                    f"relatorio")
            elif no_markdown[rid] != json_status:
                result["divergence"].append(
                    f"{rid}: JSON diz {json_status}, relatorio diz "
                    f"{no_markdown[rid]}")
    return result


# The categories that block delivery. Warnings and unquoted citations do not: the
# first is often a legitimate paraphrase, the second is a gap in what could be
# checked rather than a proven defect -- --strict promotes both.
BLOCKING = ("errors", "uncited", "missing_sections", "leaks", "placeholders",
            "rows", "unsupported", "promises")

# O report.json tem as proprias categorias bloqueantes. Separadas de BLOCKING porque
# ele e opcional: um relatorio sem registro de maquina ainda e um relatorio valido.
DATA_BLOCKING = ("invalid", "citations", "divergence")


def is_clean(result):
    if any(result[key] for key in BLOCKING):
        return False
    data = result.get("data")
    if data and any(data[key] for key in DATA_BLOCKING):
        return False
    return True


def report(result, quiet=False):
    out = sys.stdout.write
    if not quiet:
        out(f"\n=== lgpd-scan: verificacao ({result['kind']}) ===\n")
        out(f"citacoes validas   {result['ok']} em {result['files']} arquivos\n")
        data = result.get("data")
        if data:
            resumo = data["summary"] or {}
            out(f"report.json        {data['checked']} evidencia(s) conferida(s)"
                f", indice de pendencia "
                f"{resumo.get('indice_de_pendencia', '?')}\n")

    if result["leaks"]:
        out("\n!! SEGREDO REPRODUZIDO NO DOCUMENTO !!\n")
        for item in result["leaks"]:
            out(f"  {item}\n")
        out("  Cite arquivo:linha e o tipo da credencial, nunca o valor.\n")

    if result["errors"]:
        out(f"\nERROS ({len(result['errors'])}) — evidencia que nao existe:\n")
        for item in result["errors"]:
            out(f"  {item}\n")

    if result["unsupported"]:
        out("\nDOCUMENTO SEM LASTRO NO CODIGO:\n")
        for item in result["unsupported"]:
            out(f"  {item}\n")

    if result["placeholders"]:
        out(f"\nMARCADOR NAO PREENCHIDO ({len(result['placeholders'])}):\n")
        for item in result["placeholders"]:
            out(f"  {item}\n")
        out("  E a mesma falha que a ferramenta reporta como R15: um documento que\n"
            "  manda o leitor procurar um campo que ninguem preencheu. Para o que\n"
            "  depende do controlador, use a marca de pendencia visivel\n"
            "  (\u26a0 A PREENCHER PELO CONTROLADOR) em vez do marcador do modelo.\n")

    if result.get("promises"):
        out(f"\nPROMESSA SEM IMPLEMENTACAO ({len(result['promises'])}):\n")
        for item in result["promises"]:
            out(f"  {item}\n")
        out("  A politica so promete o que o codigo entrega. Ou implemente, ou\n"
            "  reescreva como pedido ao encarregado — que e legitimo, verdadeiro, e\n"
            "  e o que o sistema faz hoje.\n")

    if result["rows"]:
        out(f"\nLINHAS DE TABELA SEM EVIDENCIA ({len(result['rows'])}):\n")
        for item in result["rows"]:
            out(f"  {item}\n")
        out("  Cada linha afirma um fato. Cite arquivo:linha com o trecho, ou declare\n"
            "  a lacuna (ausente, nao verificavel, a preencher) — uma das duas.\n")

    data = result.get("data")
    if data:
        if data["invalid"]:
            out(f"\nREPORT.JSON FORA DO SCHEMA ({len(data['invalid'])}):\n")
            for item in data["invalid"]:
                out(f"  {item}\n")
        if data["citations"]:
            out(f"\nEVIDENCIA DO REPORT.JSON QUE NAO FECHA "
                f"({len(data['citations'])}):\n")
            for item in data["citations"]:
                out(f"  {item}\n")
        if data["divergence"]:
            out(f"\nJSON E RELATORIO DISCORDAM ({len(data['divergence'])}):\n")
            for item in data["divergence"]:
                out(f"  {item}\n")
            out("  Sao dois registros da mesma auditoria. Discordando, nao da para\n"
                "  saber qual esta certo — corrija os dois para o mesmo status.\n")

    if result["uncited"]:
        out(f"\nACHADOS SEM EVIDENCIA ({len(result['uncited'])}):\n")
        for item in result["uncited"]:
            out(f"  {item} afirma algo sem citar nenhum arquivo:linha\n")
        out("  Cite a linha que falha, ou diga o que foi procurado e nao existe —\n"
            "  uma das duas. O que nao vale e afirmar a lacuna e nao sustentar.\n")

    if result["missing_sections"]:
        out(f"\nSECOES OBRIGATORIAS AUSENTES ({len(result['missing_sections'])}):\n")
        for item in result["missing_sections"]:
            out(f"  {item}\n")

    if result["warnings"]:
        out(f"\nAVISOS ({len(result['warnings'])}) — trecho citado nao bate com a linha:\n")
        for item in result["warnings"]:
            out(f"  {item}\n")

    if result["unquoted"]:
        out(f"\nCITACOES SEM TRECHO ({len(result['unquoted'])}) — nao da para conferir "
            f"automaticamente:\n")
        limit = len(result["unquoted"]) if not quiet else 10
        for item in result["unquoted"][:limit]:
            out(f"  {item}\n")
        if quiet and len(result["unquoted"]) > limit:
            out(f"  ... e mais {len(result['unquoted']) - limit}\n")
        out("  Cite um trecho entre crases junto da linha para que a checagem alcance\n"
            "  estas. Sem isso, a unica coisa verificada e que a linha existe — e uma\n"
            "  linha existente pode dizer algo completamente diferente do afirmado.\n")

    clean = is_clean(result)
    if clean:
        out("\nTudo certo: toda afirmacao aponta para codigo que existe.\n\n")
    else:
        out("\nCorrija os itens acima antes de entregar o documento.\n\n")
    return clean


def main():
    parser = argparse.ArgumentParser(
        description="Verify that every claim in an lgpd-scan document points at real code."
    )
    parser.add_argument("report", nargs="?", default="RELATORIO-LGPD.md")
    parser.add_argument("--repo", default=None,
                        help="repository root (default: the document's directory)")
    parser.add_argument("--kind", default="auto",
                        choices=["auto"] + sorted(DOC_PROFILES),
                        help="document kind (default: detected from name and title)")
    parser.add_argument("--data", default=None,
                        help="report.json a conferir junto (padrao: "
                             "<repo>/.lgpd-scan/report.json, quando existir)")
    parser.add_argument("--no-data", action="store_true",
                        help="nao procurar o report.json")
    parser.add_argument("--quiet", action="store_true",
                        help="show only problems")
    parser.add_argument("--strict", action="store_true",
                        help="fail on warnings and on citations without a snippet")
    args = parser.parse_args()

    if not os.path.isfile(args.report):
        sys.stderr.write(f"erro: documento nao encontrado: {args.report}\n")
        return 2

    lines = read_lines(args.report) or []
    kind = args.kind if args.kind != "auto" else detect_kind(args.report, lines)
    profile = DOC_PROFILES[kind]

    repo = args.repo or os.path.dirname(os.path.abspath(args.report)) or "."
    result = verify(args.report, repo, profile)
    if result is None:
        return 2

    data_path = args.data
    if not data_path and not args.no_data and kind == "relatorio":
        guess = os.path.join(repo, ".lgpd-scan", "report.json")
        data_path = guess if os.path.isfile(guess) else None
    if data_path:
        if not os.path.isfile(data_path):
            sys.stderr.write(f"erro: nao encontrei {data_path}\n")
            return 2
        result["data"] = verify_data(data_path, repo, lines)

    clean = report(result, quiet=args.quiet)
    if not clean:
        return 1
    if args.strict and (result["warnings"] or result["unquoted"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
