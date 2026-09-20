#!/usr/bin/env python3
"""
lgpd-scan: o relatorio como dado.

O relatorio em markdown e para pessoas. Este modulo define o mesmo conteudo em
formato de maquina -- `.lgpd-scan/report.json` -- e e o que torna derivavel tudo o
que antes exigiria reescrever: o diff entre duas auditorias, o portao de CI, a saida
SARIF, qualquer painel.

Duas decisoes de desenho que valem explicacao, porque as duas contrariam o caminho
obvio.

**O JSON e escrito, nao extraido.** Seria mais simples fazer um parser do markdown,
e foi o que a primeira versao do verificador fez com os cabecalhos. E fragil pelo
motivo de sempre: o documento e prosa, e prosa muda. Aqui o agente escreve os dois, e
o verificador confere que concordam. Divergencia entre o JSON e o relatorio e erro --
o mesmo principio que rege o resto da ferramenta, aplicado a ela mesma.

**Nao existe nota de conformidade de 0 a 100.** E o primeiro pedido de todo mundo e
seria o jeito mais rapido de destruir o que a ferramenta tenta fazer: "78% em
conformidade" e uma frase que alguem leva para uma reuniao, e nenhum numero derivado
de leitura de codigo sustenta aquela frase diante da ANPD. O que existe e o
`indice_de_pendencia` -- soma ponderada das lacunas abertas, onde MENOR e melhor e
zero nao significa conformidade. Serve para ver tendencia entre duas execucoes, que e
a pergunta legitima, sem virar atestado.

Python 3.8+, biblioteca padrao.
"""

import argparse
import json
import os
import sys

SCHEMA = "lgpd-scan/report/1"

# Fonte unica da verdade sobre os 21 requisitos. `references/requirements/index.md`
# repete esta tabela para o leitor humano, e um fixture confere que as duas nao
# divergiram -- documentacao que contradiz o codigo e pior que documentacao nenhuma.
REQUIREMENTS = [
    ("R01", "Inventario de dados pessoais", "Art. 5o, I", "base"),
    ("R02", "Dados sensiveis identificados como tais", "Art. 11", "base"),
    ("R03", "Direito de eliminacao", "Art. 18, VI", "base"),
    ("R04", "Direito de acesso e portabilidade", "Art. 18, II e V", "base"),
    ("R05", "Direito de correcao", "Art. 18, III", "base"),
    ("R06", "Registro de consentimento", "Art. 8o, §1o", "base"),
    ("R07", "Retencao e expurgo", "Art. 15 e 16", "base"),
    ("R08", "Seguranca do armazenamento de credenciais", "Art. 46", "base"),
    ("R09", "Segredos fora do repositorio", "Art. 46", "base"),
    ("R10", "Minimizacao de dados em logs", "Art. 6o, III", "base"),
    ("R11", "Registro das operacoes de tratamento", "Art. 37", "base"),
    ("R12", "Compartilhamento com terceiros", "Art. 33", "base"),
    ("R13", "Registro de incidente de seguranca", "Res. CD/ANPD 15/2024, art. 10", "anpd"),
    ("R14", "Comunicacao de incidente no prazo", "Res. CD/ANPD 15/2024, art. 6o e 9o", "anpd"),
    ("R15", "Encarregado indicado e canal do titular", "Res. CD/ANPD 18/2024", "anpd"),
    ("R16", "Salvaguarda de transferencia internacional", "Res. CD/ANPD 19/2024", "anpd"),
    ("R17", "Anonimizacao e pseudonimizacao", "Art. 12", "anpd"),
    ("R18", "Verificacao de idade sem autodeclaracao", "Lei 15.211/2025", "eca"),
    ("R19", "Vinculacao a responsavel legal", "Lei 15.211/2025", "eca"),
    ("R20", "Configuracao padrao mais protetiva", "Lei 15.211/2025", "eca"),
    ("R21", "Perfilamento publicitario para menores", "Lei 15.211/2025", "eca"),
]

REQUIREMENT_IDS = [r[0] for r in REQUIREMENTS]
REQUIREMENT_BY_ID = {r[0]: {"title": r[1], "legal": r[2], "group": r[3]}
                     for r in REQUIREMENTS}
GROUPS = ("base", "anpd", "eca")

STATUSES = ("Atendido", "Parcial", "Nao atendido", "Nao verificavel", "Nao se aplica")
GAP_STATUSES = ("Parcial", "Nao atendido")
SEVERITIES = ("Alta", "Media", "Baixa")
CONFIDENCES = ("Alta", "Media", "Baixa")

# Peso das lacunas abertas. Deliberadamente sem teto e sem porcentagem: e uma
# contagem ponderada de pendencia, nao uma nota.
SEVERITY_WEIGHT = {"Alta": 3, "Media": 2, "Baixa": 1}

ACCENTS = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
                        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")


def deaccent(text):
    return (text or "").translate(ACCENTS)


def canonical_status(value):
    """Aceita o status como o relatorio o escreve, com acento e caixa livres."""
    wanted = deaccent(str(value)).strip().lower()
    for status in STATUSES:
        if deaccent(status).lower() == wanted:
            return status
    return None


def canonical_term(value, options):
    if value in (None, "", "-", "—"):
        return None
    wanted = deaccent(str(value)).strip().lower()
    for option in options:
        if deaccent(option).lower() == wanted:
            return option
    return False  # diferente de None: veio algo, e nao e do vocabulario


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _evidence_problems(rid, entry):
    problems = []
    for idx, item in enumerate(entry.get("evidence") or [], start=1):
        where = f"{rid}.evidence[{idx}]"
        if not isinstance(item, dict):
            problems.append(f"{where}: deveria ser um objeto com file, line e snippet")
            continue
        if not item.get("file"):
            problems.append(f"{where}: sem `file`")
        line = item.get("line")
        if not isinstance(line, int) or line < 1:
            problems.append(f"{where}: `line` deveria ser um inteiro >= 1")
        # O trecho e o que permite conferir que a linha diz o que foi afirmado. Sem
        # ele so se prova que a linha existe, e uma linha que existe pode dizer
        # qualquer outra coisa -- foi assim que duas citacoes inventadas passaram
        # pelo verificador na primeira execucao real.
        if not (item.get("snippet") or "").strip():
            problems.append(f"{where}: sem `snippet` — a citacao fica inconferivel")
    return problems


def check_evidence(data, repo):
    """Cada evidencia conferida contra o arquivo real.

    Importado sob demanda para nao criar ciclo: o verificador ja importa este
    modulo, e as tres perguntas (arquivo existe, linha esta dentro, trecho aparece
    por ali) sao dele.
    """
    from verify_report import check_evidence_item  # noqa: WPS433

    problems, cache, checked = [], {}, 0
    for entry in data.get("requirements") or []:
        for item in entry.get("evidence") or []:
            if not isinstance(item, dict):
                continue
            checked += 1
            problem = check_evidence_item(item, repo, cache)
            if problem:
                problems.append(f"{entry.get('id')}  {problem}")
    return problems, checked


def validate(data):
    """Problemas que impedem o JSON de ser usado. Lista vazia significa valido."""
    problems = []

    if data.get("schema") != SCHEMA:
        problems.append(f"schema: esperado {SCHEMA!r}, veio {data.get('schema')!r}")

    repo = data.get("repo") or {}
    if not isinstance(repo, dict) or not repo.get("root"):
        problems.append("repo.root ausente")

    entries = data.get("requirements")
    if not isinstance(entries, list) or not entries:
        problems.append("requirements: lista ausente ou vazia")
        return problems

    seen = {}
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append("requirements: item que nao e objeto")
            continue
        rid = entry.get("id")
        if rid not in REQUIREMENT_BY_ID:
            problems.append(f"requisito desconhecido: {rid!r}")
            continue
        if rid in seen:
            problems.append(f"{rid}: aparece duas vezes")
        seen[rid] = entry

        status = canonical_status(entry.get("status"))
        if status is None:
            problems.append(
                f"{rid}: status {entry.get('status')!r} fora do vocabulario "
                f"({', '.join(STATUSES)})")
            continue
        entry["status"] = status

        severity = canonical_term(entry.get("severity"), SEVERITIES)
        if severity is False:
            problems.append(f"{rid}: severidade {entry.get('severity')!r} invalida")
        confidence = canonical_term(entry.get("confidence"), CONFIDENCES)
        if confidence is False:
            problems.append(f"{rid}: confianca {entry.get('confidence')!r} invalida")

        has_evidence = bool(entry.get("evidence"))
        absence = (entry.get("absence") or "").strip()
        note = (entry.get("note") or "").strip()

        if status in GAP_STATUSES:
            if not severity:
                problems.append(f"{rid}: {status} exige severidade")
            # Uma lacuna se sustenta de dois jeitos: apontando o codigo que falha, ou
            # descrevendo a busca que nao achou nada. O que nao vale e afirmar a
            # lacuna e nao dizer nenhum dos dois -- e a diferenca entre achado e
            # palpite.
            if not has_evidence and not absence:
                problems.append(
                    f"{rid}: {status} sem `evidence` e sem `absence` — descreva a "
                    f"busca que nao achou nada, se for esse o caso")
        if status == "Atendido" and not has_evidence:
            problems.append(f"{rid}: Atendido sem nenhuma evidencia")
        if status in ("Nao verificavel", "Nao se aplica") and not note:
            problems.append(f"{rid}: {status} exige `note` com a razao")

        problems.extend(_evidence_problems(rid, entry))

    faltando = [rid for rid in REQUIREMENT_IDS if rid not in seen]
    if faltando:
        # Omitir um requisito e diferente de responde-lo com "nao se aplica": o
        # primeiro deixa o leitor sem saber se a pergunta foi feita.
        problems.append(
            "requisitos ausentes do JSON (use `Nao se aplica` com a razao em vez de "
            "omitir): " + ", ".join(faltando))

    return problems


def summarise(data):
    by_status = {status: 0 for status in STATUSES}
    by_severity = {severity: 0 for severity in SEVERITIES}
    pendencia = 0
    evidencias = 0

    for entry in data.get("requirements") or []:
        status = canonical_status(entry.get("status"))
        if status:
            by_status[status] += 1
        evidencias += len(entry.get("evidence") or [])
        if status in GAP_STATUSES:
            severity = canonical_term(entry.get("severity"), SEVERITIES)
            if severity:
                by_severity[severity] += 1
                pendencia += SEVERITY_WEIGHT[severity]

    decididos = sum(by_status[s] for s in ("Atendido", "Parcial", "Nao atendido"))
    avaliados = decididos + by_status["Nao verificavel"]

    return {
        "por_status": by_status,
        "lacunas_por_severidade": by_severity,
        "indice_de_pendencia": pendencia,
        "requisitos_decididos": decididos,
        "requisitos_avaliados": avaliados,
        "citacoes": evidencias,
        # Repetido na saida de proposito: este numero e citado fora de contexto com
        # frequencia suficiente para justificar carregar o aviso junto.
        "aviso": ("indice_de_pendencia e contagem ponderada de lacunas abertas "
                  "(Alta=3, Media=2, Baixa=1); menor e melhor e zero nao significa "
                  "conformidade"),
    }


def diff(old, new):
    """O que mudou entre duas auditorias do mesmo repositorio."""
    old_map = {e.get("id"): e for e in (old.get("requirements") or [])}
    new_map = {e.get("id"): e for e in (new.get("requirements") or [])}

    mudancas, resolvidos, regressoes = [], [], []
    for rid in REQUIREMENT_IDS:
        antes = canonical_status((old_map.get(rid) or {}).get("status"))
        agora = canonical_status((new_map.get(rid) or {}).get("status"))
        if antes == agora:
            continue
        item = {"id": rid, "de": antes, "para": agora,
                "titulo": REQUIREMENT_BY_ID[rid]["title"]}
        mudancas.append(item)
        if antes in GAP_STATUSES and agora == "Atendido":
            resolvidos.append(item)
        elif antes == "Atendido" and agora in GAP_STATUSES:
            regressoes.append(item)

    antes_resumo, agora_resumo = summarise(old), summarise(new)
    return {
        "mudancas": mudancas,
        "resolvidos": resolvidos,
        "regressoes": regressoes,
        "indice_de_pendencia": {
            "antes": antes_resumo["indice_de_pendencia"],
            "agora": agora_resumo["indice_de_pendencia"],
            "delta": (agora_resumo["indice_de_pendencia"]
                      - antes_resumo["indice_de_pendencia"]),
        },
    }


def render_summary(data, out=None):
    out = out or sys.stdout.write
    resumo = summarise(data)
    repo = data.get("repo") or {}
    out("\n=== lgpd-scan: resumo do relatorio ===\n")
    out(f"repositorio        {repo.get('root', '?')}\n")
    out(f"commit             {repo.get('commit') or 'sem git'}\n")
    out(f"ferramenta         lgpd-scan {data.get('tool_version', '?')}\n\n")
    for status in STATUSES:
        out(f"  {status:<18} {resumo['por_status'][status]}\n")
    out(f"\nlacunas            "
        f"Alta {resumo['lacunas_por_severidade']['Alta']}, "
        f"Media {resumo['lacunas_por_severidade']['Media']}, "
        f"Baixa {resumo['lacunas_por_severidade']['Baixa']}\n")
    out(f"indice de pendencia {resumo['indice_de_pendencia']}  "
        f"(menor e melhor; zero nao significa conformidade)\n")
    out(f"citacoes            {resumo['citacoes']}\n\n")
    return resumo


def render_diff(result, out=None):
    out = out or sys.stdout.write
    out("\n=== lgpd-scan: o que mudou ===\n")
    if not result["mudancas"]:
        out("nenhum requisito mudou de status.\n")
    for item in result["mudancas"]:
        marca = "  "
        if item in result["regressoes"]:
            marca = "!!"
        elif item in result["resolvidos"]:
            marca = "ok"
        out(f"{marca} {item['id']}  {item['de']} -> {item['para']}  "
            f"({item['titulo']})\n")
    indice = result["indice_de_pendencia"]
    sinal = "+" if indice["delta"] > 0 else ""
    out(f"\nindice de pendencia {indice['antes']} -> {indice['agora']} "
        f"({sinal}{indice['delta']})\n\n")
    return not result["regressoes"]


def main():
    parser = argparse.ArgumentParser(
        description="Valida, resume e compara o relatorio em formato de dado.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="confere o report.json contra o schema")
    p_val.add_argument("report", nargs="?", default=".lgpd-scan/report.json")
    p_val.add_argument("--repo", default=None,
                       help="tambem confere cada evidencia contra o codigo")

    p_sum = sub.add_parser("summary", help="contagens e indice de pendencia")
    p_sum.add_argument("report", nargs="?", default=".lgpd-scan/report.json")
    p_sum.add_argument("--json", action="store_true", help="saida em JSON")

    p_diff = sub.add_parser("diff", help="compara duas auditorias")
    p_diff.add_argument("antes")
    p_diff.add_argument("depois", nargs="?", default=".lgpd-scan/report.json")
    p_diff.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.cmd == "diff":
        for path in (args.antes, args.depois):
            if not os.path.isfile(path):
                sys.stderr.write(f"erro: nao encontrei {path}\n")
                return 2
        result = diff(load(args.antes), load(args.depois))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        return 0 if render_diff(result) else 1

    if not os.path.isfile(args.report):
        sys.stderr.write(f"erro: nao encontrei {args.report}\n")
        return 2
    data = load(args.report)

    if args.cmd == "validate":
        problems = validate(data)
        checked = 0
        if args.repo:
            evidencia, checked = check_evidence(data, args.repo)
            problems.extend(evidencia)
        if not problems:
            extra = f", {checked} evidencia(s) conferida(s)" if args.repo else ""
            print(f"ok: {args.report} confere com o schema {SCHEMA}{extra}")
            return 0
        sys.stderr.write(f"\n{len(problems)} problema(s) em {args.report}:\n")
        for item in problems:
            sys.stderr.write(f"  {item}\n")
        sys.stderr.write("\n")
        return 1

    if args.cmd == "summary":
        if args.json:
            print(json.dumps(summarise(data), ensure_ascii=False, indent=2))
        else:
            render_summary(data)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
