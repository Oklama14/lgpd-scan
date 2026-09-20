#!/usr/bin/env python3
"""
lgpd-scan fixture tests.

Two suites, one command.

Each directory under tests/fixtures/ is a tiny repository plus an expected.json
saying what the collector must and must not find in it. Each directory under
tests/verifier/ is a written document plus an expected.json saying which of the
verifier's categories it must trip -- including the two false-positive guards,
because a verifier that cries wolf about legitimate pendency markers gets turned
off, and then nothing is verified at all.

This harness exists because of a hard rule: no new requirement enters the skill
without a fixture. Going from twelve requirements to twenty-one multiplies the
false-positive surface along with the coverage, and a lexicon is exactly the kind
of artefact that regresses silently -- you widen one pattern to catch a real field
and three unrelated signals start firing somewhere else. The fixtures are what turn
that from a surprise in someone's report into a failing test here.

    python3 scripts/run_tests.py            # run everything
    python3 scripts/run_tests.py eca        # only cases whose name contains "eca"
    python3 scripts/run_tests.py -v         # show every assertion, not just failures

Python 3.8+, standard library only.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ci_check  # noqa: E402
import collect  # noqa: E402
import report_data  # noqa: E402
import verify_report  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
FIXTURES = os.path.join(TESTS, "fixtures")
VERIFIER = os.path.join(TESTS, "verifier")
CI = os.path.join(TESTS, "ci")


def _git_init(work, tracked):
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(["git", "init", "-q", work], check=True, **quiet)
    for key, value in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", work, "config", key, value], check=True, **quiet)
    subprocess.run(["git", "-C", work, "add", *tracked], check=False, **quiet)
    subprocess.run(["git", "-C", work, "commit", "-qm", "fixture"], check=False, **quiet)


def compare(expected, actual):
    """Evaluate one expectation against a count.

    Accepts an int for an exact count, or a string like ">=2", ">0", "<=1" so a
    fixture can say "at least one hit" without pinning a number that legitimate
    lexicon growth would break.
    """
    if isinstance(expected, int):
        return actual == expected, f"= {expected}"
    text = str(expected).strip()
    for op in (">=", "<=", ">", "<", "=="):
        if text.startswith(op):
            target = int(text[len(op):])
            ok = {
                ">=": actual >= target, "<=": actual <= target,
                ">": actual > target, "<": actual < target,
                "==": actual == target,
            }[op]
            return ok, f"{op} {target}"
    return actual == int(text), f"= {text}"


def run_fixture(path, verbose=False):
    name = os.path.basename(path)
    spec_path = os.path.join(path, "expected.json")
    if not os.path.isfile(spec_path):
        return name, ["sem expected.json"], 0

    with open(spec_path, encoding="utf-8") as handle:
        spec = json.load(handle)

    repo = os.path.join(path, "repo")
    if not os.path.isdir(repo):
        return name, ["sem pasta repo/"], 0

    # A fixture that needs git gets a throwaway copy with a real repository in it.
    # Committing a nested .git inside this project would be worse than the test is
    # worth, and the git-dependent behaviour -- .gitignore being honoured, the
    # tracked flag that decides R09's severity -- is exactly what needs covering.
    with tempfile.TemporaryDirectory() as tmp:
        if spec.get("git_outer") is not None:
            # O repositorio git fica ACIMA da pasta varrida, e ignora ela. E o caso
            # que produzia relatorio limpo porque o coletor nao lia nada: skill
            # instalada em .claude/skills/, subprojeto ignorado, pasta de entrega.
            outer = os.path.join(tmp, "outer")
            work = os.path.join(outer, "sub")
            shutil.copytree(repo, work)
            with open(os.path.join(outer, ".gitignore"), "w", encoding="utf-8") as fh:
                fh.write(spec["git_outer"] + "\n")
            _git_init(outer, [".gitignore"])
        elif spec.get("git_init"):
            work = os.path.join(tmp, "repo")
            shutil.copytree(repo, work)
            _git_init(work, spec.get("git_tracked", ["."]))
        else:
            work = repo
        result = collect.scan(
            work,
            include_tests=spec.get("include_tests", False),
            max_hits=spec.get("max_hits", 40),
        )

    signals = {k: len(v) for k, v in result["signals"].items()}
    failures, checks = [], 0

    for signal, expectation in spec.get("expect_signals", {}).items():
        checks += 1
        actual = signals.get(signal, 0)
        ok, rendered = compare(expectation, actual)
        if not ok:
            failures.append(f"{signal}: esperado {rendered}, obtido {actual}")
        elif verbose:
            print(f"      ok  {signal} {rendered} (obtido {actual})")

    for signal in spec.get("expect_absent", []):
        checks += 1
        if signal not in result["absent_signals"]:
            failures.append(
                f"{signal}: esperado em absent_signals, mas teve "
                f"{signals.get(signal, 0)} ocorrencia(s)")
        elif verbose:
            print(f"      ok  {signal} ausente")

    expected_stacks = spec.get("expect_stacks")
    if expected_stacks is not None:
        checks += 1
        if sorted(result["stacks_detected"]) != sorted(expected_stacks):
            failures.append(
                f"stacks: esperado {sorted(expected_stacks)}, "
                f"obtido {sorted(result['stacks_detected'])}")
        elif verbose:
            print(f"      ok  stacks {sorted(expected_stacks)}")

    # Um sinal cujas ocorrencias vem TODAS do texto legal e uma promessa, nao uma
    # implementacao -- a distincao que o relatorio precisa fazer para nao creditar
    # a politica de privacidade como se fosse codigo.
    for signal in spec.get("expect_legal_only", []):
        checks += 1
        hits = result["signals"].get(signal, [])
        if not hits:
            failures.append(f"{signal}: esperava ocorrencias declaratorias, veio vazio")
        elif not all(h.get("declaration_only") for h in hits):
            implementacao = [f"{h['file']}:{h['line']}" for h in hits
                             if not h.get("declaration_only")]
            failures.append(
                f"{signal}: {len(implementacao)} ocorrencia(s) fora do texto legal "
                f"({', '.join(implementacao[:3])})")
        elif verbose:
            print(f"      ok  {signal} so declaratorio ({len(hits)} ocorrencias)")

    for expectation in spec.get("expect_generated", []):
        checks += 1
        hits = [h for h in result["signals"].get(expectation["signal"], [])
                if h["file"].endswith(expectation["file"])]
        if not hits:
            failures.append(
                f"{expectation['signal']}: nenhuma ocorrencia em "
                f"{expectation['file']}")
        elif not all(h.get("generated_by_tool") for h in hits):
            failures.append(
                f"{expectation['signal']} em {expectation['file']}: sem a etiqueta "
                f"generated_by_tool")
        elif verbose:
            print(f"      ok  {expectation['signal']} etiquetado como gerado")

    for expectation in spec.get("expect_suppressed", []):
        checks += 1
        found = [s for s in result.get("suppressed", [])
                 if s["signal"] == expectation["signal"]
                 and s["file"].endswith(expectation["file"])]
        if not found:
            failures.append(
                f"supressao nao registrada: {expectation['signal']} "
                f"em {expectation['file']}")
        elif expectation.get("reason_contains") and not any(
                expectation["reason_contains"].lower() in (s.get("reason") or "").lower()
                for s in found):
            failures.append(
                f"supressao sem o motivo esperado: {expectation['reason_contains']}")
        elif verbose:
            print(f"      ok  suprimido {expectation['signal']}")

    for expectation in spec.get("expect_rejected", []):
        checks += 1
        found = [x for x in result.get("suppression_rejected", [])
                 if x["signal"] == expectation["signal"]
                 and expectation.get("why_contains", "").lower() in x["why"].lower()]
        if not found:
            failures.append(
                f"supressao deveria ser rejeitada: {expectation['signal']} "
                f"({expectation.get('why_contains')})")
        elif verbose:
            print(f"      ok  rejeitado {expectation['signal']}")

    if "expect_listing_source" in spec:
        checks += 1
        actual = (result.get("git") or {}).get("listing_source")
        if actual != spec["expect_listing_source"]:
            failures.append(
                f"listing_source: esperado {spec['expect_listing_source']}, "
                f"obtido {actual}")
        elif verbose:
            print(f"      ok  listing_source {actual}")

    if spec.get("expect_no_listing_note"):
        checks += 1
        note = (result.get("git") or {}).get("listing_note")
        if note:
            failures.append(f"listing_note nao deveria existir: {note}")
        elif verbose:
            print("      ok  sem aviso de listagem")

    if spec.get("expect_listing_note"):
        checks += 1
        note = (result.get("git") or {}).get("listing_note") or ""
        if spec["expect_listing_note"].lower() not in note.lower():
            failures.append(
                f"listing_note nao menciona '{spec['expect_listing_note']}': "
                f"{note or 'sem aviso'}")
        elif verbose:
            print("      ok  listing_note presente")

    if "expect_files_scanned" in spec:
        checks += 1
        actual = result["counts"]["files_scanned"]
        ok, rendered = compare(spec["expect_files_scanned"], actual)
        if not ok:
            failures.append(f"files_scanned: esperado {rendered}, obtido {actual}")
        elif verbose:
            print(f"      ok  files_scanned {rendered}")

    for expectation in spec.get("expect_declared", []):
        checks += 1
        found = [d for d in result.get("declared", [])
                 if d["kind"] == expectation["kind"]
                 and expectation.get("value", d.get("value")) == d.get("value")]
        if not found:
            failures.append(f"anotacao declarada nao lida: {expectation}")
        elif verbose:
            print(f"      ok  declarado {expectation['kind']}")

    return name, failures, checks



def run_ci_case(path, verbose=False):
    """Um portao de CI: estado anterior, estado da PR, e o que deve reprovar.

    Cada caso tem `antes/` e `depois/`. A baseline e construida do primeiro, do
    mesmo jeito que `--update-baseline` faria, e a comparacao roda contra o segundo.
    Construir a baseline em vez de escreve-la a mao e o que faz o teste cobrir
    tambem o formato gravado -- uma baseline escrita a mao passaria a concordar com
    um bug de gravacao.
    """
    name = os.path.basename(path)
    spec_path = os.path.join(path, "expected.json")
    antes_dir = os.path.join(path, "antes")
    depois_dir = os.path.join(path, "depois")
    if not (os.path.isfile(spec_path) and os.path.isdir(antes_dir)
            and os.path.isdir(depois_dir)):
        return name, ["falta expected.json, antes/ ou depois/"], 0

    with open(spec_path, encoding="utf-8") as handle:
        spec = json.load(handle)

    with tempfile.TemporaryDirectory() as tmp:
        work_antes = os.path.join(tmp, "antes")
        work_depois = os.path.join(tmp, "depois")
        shutil.copytree(antes_dir, work_antes)
        shutil.copytree(depois_dir, work_depois)
        if spec.get("git", True):
            _git_init(work_antes, ["."])
            _git_init(work_depois, spec.get("git_tracked", ["."]))
        baseline = ci_check.build_baseline(collect.scan(work_antes, max_hits=200))
        depois = collect.scan(work_depois, max_hits=200)
        achados, informativo = ci_check.compare(baseline, depois)
        sarif = ci_check.to_sarif(achados, work_depois, "teste")

    failures, checks = [], 0
    contagem = {nivel: sum(1 for a in achados if a["severity"] == nivel)
                for nivel in ("alta", "media", "baixa")}

    for nivel, expectation in (spec.get("expect_severidade") or {}).items():
        checks += 1
        ok, rendered = compare(expectation, contagem.get(nivel, 0))
        if not ok:
            failures.append(
                f"achados {nivel}: esperado {rendered}, obtido {contagem.get(nivel, 0)}")
            for a in achados:
                failures.append(f"    -> [{a['severity']}] {a['signal']} "
                                f"{a.get('file') or '(repo)'}: {a['message'][:60]}")
        elif verbose:
            print(f"      ok  achados {nivel} {rendered}")

    for esperado in spec.get("expect_achados", []):
        checks += 1
        encontrados = [a for a in achados
                       if a["signal"] == esperado["signal"]
                       and (not esperado.get("tipo") or a["tipo"] == esperado["tipo"])
                       and (not esperado.get("severity")
                            or a["severity"] == esperado["severity"])]
        quantidade = esperado.get("quantidade", ">=1")
        ok, rendered = compare(quantidade, len(encontrados))
        if not ok:
            failures.append(
                f"{esperado['signal']}: esperado {rendered} achado(s), obtido "
                f"{len(encontrados)}")
        elif verbose:
            print(f"      ok  achado {esperado['signal']} {rendered}")

    for signal in spec.get("expect_sem_achado", []):
        checks += 1
        if any(a["signal"] == signal for a in achados):
            failures.append(f"{signal}: nao deveria gerar achado nenhum")
        elif verbose:
            print(f"      ok  {signal} sem achado")

    if "expect_total" in spec:
        checks += 1
        ok, rendered = compare(spec["expect_total"], len(achados))
        if not ok:
            failures.append(f"total de achados: esperado {rendered}, obtido "
                            f"{len(achados)}")
            for a in achados:
                failures.append(f"    -> [{a['severity']}] {a['signal']} "
                                f"{a.get('file') or '(repo)'}")
        elif verbose:
            print(f"      ok  total {rendered}")

    # SARIF valido o suficiente para o GitHub aceitar: uma run, uma regra por sinal
    # citado, e todo resultado apontando para uma regra que existe.
    checks += 1
    regras = {r["id"] for r in sarif["runs"][0]["tool"]["driver"]["rules"]}
    orfaos = [r["ruleId"] for r in sarif["runs"][0]["results"]
              if r["ruleId"] not in regras]
    if orfaos:
        failures.append(f"SARIF com resultado sem regra: {sorted(set(orfaos))}")
    elif len(sarif["runs"][0]["results"]) != len(achados):
        failures.append("SARIF com numero de resultados diferente dos achados")
    elif verbose:
        print(f"      ok  SARIF ({len(achados)} resultados)")

    return name, failures, checks



def run_verifier_case(path, verbose=False):
    """One written document against the verifier's categories.

    A document case says which categories must fire and which must stay silent. The
    silent ones matter as much: two of these cases exist only to keep the placeholder
    check from flagging the deliberate pendency marker and the code the report quotes.
    """
    name = os.path.basename(path)
    spec_path = os.path.join(path, "expected.json")
    doc = os.path.join(path, "doc.md")
    if not os.path.isfile(spec_path) or not os.path.isfile(doc):
        return name, ["falta expected.json ou doc.md"], 0

    with open(spec_path, encoding="utf-8") as handle:
        spec = json.load(handle)

    repo = os.path.join(TESTS, spec["repo"]) if spec.get("repo") \
        else os.path.join(path, "repo")

    lines = verify_report.read_lines(doc) or []
    detected = verify_report.detect_kind(doc, lines)
    kind = spec.get("kind", detected)
    result = verify_report.verify(doc, repo, verify_report.DOC_PROFILES[kind])
    if result is not None and spec.get("data"):
        result["data"] = verify_report.verify_data(
            os.path.join(path, spec["data"]), repo, lines)

    failures, checks = [], 0

    if spec.get("expect_kind"):
        checks += 1
        if detected != spec["expect_kind"]:
            failures.append(
                f"tipo detectado: esperado {spec['expect_kind']}, obtido {detected}")
        elif verbose:
            print(f"      ok  tipo {detected}")

    if result is None:
        return name, failures + ["verify() devolveu None"], checks

    if "expect_clean" in spec:
        checks += 1
        clean = verify_report.is_clean(result)
        if clean != spec["expect_clean"]:
            tripped = [k for k in verify_report.BLOCKING if result[k]]
            failures.append(
                f"limpo: esperado {spec['expect_clean']}, obtido {clean}"
                + (f" (categorias: {', '.join(tripped)})" if tripped else ""))
        elif verbose:
            print(f"      ok  limpo={clean}")

    for key, expectation in spec.get("expect_data", {}).items():
        checks += 1
        block = result.get("data") or {}
        value = block.get(key)
        actual = value if isinstance(value, int) else len(value or [])
        ok, rendered = compare(expectation, actual)
        if not ok:
            failures.append(f"data.{key}: esperado {rendered}, obtido {actual}")
            for item in (value or [])[:3] if not isinstance(value, int) else []:
                failures.append(f"    -> {item}")
        elif verbose:
            print(f"      ok  data.{key} {rendered} (obtido {actual})")

    for key, expectation in spec.get("expect", {}).items():
        checks += 1
        value = result.get(key)
        actual = value if isinstance(value, int) else len(value or [])
        ok, rendered = compare(expectation, actual)
        if not ok:
            failures.append(f"{key}: esperado {rendered}, obtido {actual}")
            for item in (value or [])[:3] if not isinstance(value, int) else []:
                failures.append(f"    -> {item}")
        elif verbose:
            print(f"      ok  {key} {rendered} (obtido {actual})")

    return name, failures, checks



# --------------------------------------------------------------------------
# Terceira suite: o que nao e caso, e sim coerencia entre as partes
# --------------------------------------------------------------------------
# Nada aqui e um repositorio ou um documento. Sao invariantes entre arquivos que
# divergem em silencio: a tabela de requisitos existe em dois lugares, os sinais sao
# citados pelo nome na documentacao, e a versao aparece em quatro. Cada uma dessas
# duplicacoes ja custou uma correcao -- documentacao que contradiz o codigo e pior
# que documentacao nenhuma, porque alguem confia nela.

def _norm(text):
    text = report_data.deaccent(text or "").lower()
    for old, new in (("º", "o"), ("ª", "a"), ("§", "par."), ("–", "-"), ("—", "-")):
        text = text.replace(old, new)
    return " ".join(text.split())


def check_requirements_table():
    """A tabela dos 21 requisitos em report_data.py e em requirements/index.md."""
    path = os.path.join(ROOT, "references", "requirements", "index.md")
    failures, checks = [], 0
    if not os.path.isfile(path):
        return ["references/requirements/index.md nao existe"], 1

    with open(path, encoding="utf-8") as handle:
        rows = {}
        for line in handle:
            parts = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(parts) == 4 and re.match(r"^R\d{2}$", parts[0]):
                rows[parts[0]] = parts[1:]

    for rid, titulo, legal, grupo in report_data.REQUIREMENTS:
        checks += 1
        if rid not in rows:
            failures.append(f"{rid} esta em report_data.py e nao na tabela do index.md")
            continue
        doc_titulo, doc_legal, doc_grupo = rows[rid]
        if _norm(doc_legal) != _norm(legal):
            failures.append(
                f"{rid}: base legal difere — codigo {legal!r}, doc {doc_legal!r}")
        elif _norm(doc_grupo) != _norm(grupo):
            failures.append(
                f"{rid}: grupo difere — codigo {grupo!r}, doc {doc_grupo!r}")

    checks += 1
    extras = sorted(set(rows) - set(report_data.REQUIREMENT_IDS))
    if extras:
        failures.append(f"index.md tem requisitos que o codigo nao conhece: {extras}")
    return failures, checks


def check_signal_names():
    """Todo sinal citado na documentacao existe no coletor."""
    known = {name for name, _, _ in collect.SIGNAL_RULES}
    failures, checks = [], 0
    for folder in ("requirements", "stacks", "artifacts"):
        directory = os.path.join(ROOT, "references", folder)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".md"):
                continue
            checks += 1
            with open(os.path.join(directory, name), encoding="utf-8") as handle:
                texto = handle.read()
            # So onde a linha declara que aquilo e sinal. A primeira versao pegava
            # todo token com sublinhado entre crases e acusava `deleted_at`,
            # `opiniao_politica`, `responsavel_id` -- nomes de coluna e de padrao,
            # nao de sinal. Um teste que grita em quatro lugares certos para pegar
            # um errado e um teste que alguem desliga.
            fantasmas = set()
            for trecho in re.findall(
                    r"(?:sinais?:|R\d{2}\s*[—-])([^\n|]*)", texto):
                for nome in re.findall(r"`([a-z][a-z0-9_]{3,})`", trecho):
                    if "_" in nome and nome not in known:
                        fantasmas.add(nome)
            fantasmas = sorted(fantasmas)
            if fantasmas:
                failures.append(
                    f"references/{folder}/{name} cita sinal inexistente: "
                    + ", ".join(fantasmas))
    return failures, checks


def check_version_agreement():
    """A versao aparece em quatro arquivos; ja saiu de sincronia uma vez."""
    esperado = collect.TOOL_VERSION
    alvos = [
        ("SKILL.md", re.compile(r'version:\s*"([\d.]+)"')),
        ("install.sh", re.compile(r'VERSION="([\d.]+)"')),
        ("install.ps1", re.compile(r"\$Version\s*=\s*'([\d.]+)'")),
        ("CHANGELOG.md", re.compile(r"^## ([\d.]+)", re.M)),
    ]
    failures, checks = [], 0
    for nome, padrao in alvos:
        checks += 1
        path = os.path.join(ROOT, nome)
        if not os.path.isfile(path):
            failures.append(f"{nome} nao existe")
            continue
        with open(path, encoding="utf-8") as handle:
            achado = padrao.search(handle.read())
        if not achado:
            failures.append(f"{nome}: nao achei a versao")
        elif achado.group(1) != esperado:
            failures.append(
                f"{nome}: versao {achado.group(1)}, coletor diz {esperado}")
    return failures, checks


def check_skill_frontmatter():
    """Chave fora do spec estrito do agentskills.io e erro no empacotamento."""
    permitidas = {"allowed-tools", "compatibility", "description", "license",
                  "metadata", "name"}
    path = os.path.join(ROOT, "SKILL.md")
    with open(path, encoding="utf-8") as handle:
        texto = handle.read()
    partes = texto.split("---")
    if len(partes) < 3:
        return ["SKILL.md sem frontmatter"], 1
    chaves = set(re.findall(r"(?m)^([a-z][a-z-]*):", partes[1]))
    fora = sorted(chaves - permitidas)
    return ([f"SKILL.md: chave fora do spec agentskills.io: {', '.join(fora)}"]
            if fora else []), 1


CONSISTENCY = [
    ("tabela de requisitos: codigo x documentacao", check_requirements_table),
    ("nomes de sinais citados na documentacao", check_signal_names),
    ("versao coerente entre os arquivos", check_version_agreement),
    ("frontmatter do SKILL.md", check_skill_frontmatter),
]


def run_consistency(name_and_fn, verbose=False):
    nome, funcao = name_and_fn
    failures, checks = funcao()
    if verbose and not failures:
        print(f"      ok  {nome} ({checks} checagens)")
    return nome, failures, checks


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    needle = args[0] if args else None

    suites = [
        ("coletor", FIXTURES, run_fixture),
        ("verificador", VERIFIER, run_verifier_case),
        ("portao de ci", CI, run_ci_case),
    ]

    total_checks = total_cases = failed = 0
    print()
    for title, directory, runner in suites:
        if not os.path.isdir(directory):
            sys.stderr.write(
                f"erro: {directory} nao existe.\n"
                "Este harness roda a partir do repositorio da skill, onde tests/ fica\n"
                "ao lado de scripts/. Numa copia instalada em .claude/skills/ ele nao\n"
                "vem de proposito -- clone o repositorio para rodar a suite.\n")
            return 2
        names = sorted(d for d in os.listdir(directory)
                       if os.path.isdir(os.path.join(directory, d)))
        # O filtro casa tanto nome de caso quanto nome de suite: "run_tests.py verif"
        # e a coisa mais natural de digitar para rodar so o verificador, e um filtro
        # que so olha nome de caso responde "nenhum caso encontrado" a isso.
        if needle and needle not in title:
            names = [n for n in names if needle in n]
        if not names:
            continue

        print(f"=== {title}: {len(names)} casos ===\n")
        for name in names:
            case_name, failures, checks = runner(
                os.path.join(directory, name), verbose)
            total_checks += checks
            total_cases += 1
            if failures:
                failed += 1
                print(f"  FALHOU  {case_name}  ({checks} checagens)")
                for item in failures:
                    print(f"          - {item}")
            else:
                print(f"  ok      {case_name}  ({checks} checagens)")
        print()

    if not needle or needle in "coerencia":
        alvo = CONSISTENCY
    else:
        alvo = [item for item in CONSISTENCY if needle in item[0]]
    if alvo:
        print(f"=== coerencia: {len(alvo)} verificacoes ===\n")
        for item in alvo:
            nome, failures, checks = run_consistency(item, verbose)
            total_checks += checks
            total_cases += 1
            if failures:
                failed += 1
                print(f"  FALHOU  {nome}  ({checks} checagens)")
                for problema in failures:
                    print(f"          - {problema}")
            else:
                print(f"  ok      {nome}  ({checks} checagens)")
        print()

    if not total_cases:
        sys.stderr.write("erro: nenhum caso encontrado\n")
        return 2

    print(f"{total_cases - failed}/{total_cases} casos, {total_checks} checagens\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
