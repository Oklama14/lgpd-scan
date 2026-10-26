#!/usr/bin/env python3
"""
lgpd-scan <-> DevComply.

O DevComply registra o que a equipe DECLARA, num checklist com os itens do
LGPD-Check. Esta skill registra o que o CODIGO faz. Este modulo liga os dois pelos
codigos do LGPD-Check (`report_data.LGPD_CHECK`), nos dois sentidos:

- `export`: o report.json vira `.lgpd-scan/devcomply.json`, a situacao de cada item
  do LGPD-Check no codigo, para o DevComply importar. Vai so arquivo e linha, nunca
  o trecho: o trecho pode carregar dado pessoal de um seed ou um segredo, e o
  DevComply manda texto para uma IA na nuvem. O contrato e o schema
  `lgpd-scan/devcomply/1`, e nao o report.json, para que uma mudanca interna da
  skill nao quebre a importacao em silencio.

- `conciliar`: as declaracoes exportadas pelo DevComply contra o report.json. Um item
  marcado como implementado cujo requisito direto o codigo mostra como `Parcial` ou
  `Nao atendido` e a divergencia que justifica ter as duas ferramentas -- e o que o
  `verify_report.py` exige ver na secao "Declarado x codigo" do relatorio.

Declaracao nunca e evidencia. Ela entra aqui como a politica de privacidade entra
no resto da skill: material para confrontar com o codigo, nao prova de nada.

Python 3.8+, biblioteca padrao.
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import report_data  # noqa: E402

EXPORT_SCHEMA = "lgpd-scan/devcomply/1"
CONCILIACAO_SCHEMA = "lgpd-scan/conciliacao/1"
DECLARACOES_SCHEMA = "devcomply/declaracoes/1"

# Do pior para o melhor: quando varios requisitos decidem o mesmo item, vale o pior.
ORDEM_LACUNA = ("Nao atendido", "Parcial")
ORDEM_SEVERIDADE = ("Alta", "Media", "Baixa")
ORDEM_CONFIANCA = ("Baixa", "Media", "Alta")

# O que a conciliacao conclui sobre cada item declarado.
DIVERGENTES = ("declarado_sem_implementacao", "declarado_com_lacuna")
RESULTADOS = (
    "declarado_sem_implementacao",  # marcado; o codigo mostra Nao atendido
    "declarado_com_lacuna",         # marcado; o codigo mostra Parcial
    "confirmado",                   # marcado; o codigo mostra Atendido
    "implementado_sem_declaracao",  # nao marcado; o codigo mostra Atendido
    "lacuna_confirmada",            # nao marcado; o codigo mostra a lacuna
    "so_a_organizacao",             # o codigo nao prova este item, por natureza
    "fora_da_skill",                # o codigo poderia provar; a skill ainda nao avalia
    "so_relacao_parcial",           # requisitos tocam o item, nenhum decide
    "nao_verificavel_no_codigo",    # requisito direto ficou Nao verificavel
    "nao_se_aplica",                # requisito direto ficou Nao se aplica
)

PADRAO_EXPORT = os.path.join(".lgpd-scan", "devcomply.json")
PADRAO_CONCILIACAO = os.path.join(".lgpd-scan", "conciliacao.json")
PADRAO_REPORT = os.path.join(".lgpd-scan", "report.json")


def agora():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _por_requisito(data):
    mapa = {}
    for entry in data.get("requirements") or []:
        if isinstance(entry, dict) and entry.get("id"):
            mapa[entry["id"]] = entry
    return mapa


def _status(entry):
    return report_data.canonical_status((entry or {}).get("status"))


def situacao_do_item(codigo, reqs, por_item=None):
    """Situacao de um item do LGPD-Check no codigo, a partir dos requisitos diretos.

    Devolve None quando nenhum requisito decide o item. Relacoes parciais nunca
    decidem: entram como contexto em `relacionados`.
    """
    por_item = por_item or report_data.lgpd_check_por_item()
    rel = por_item.get(codigo) or {"direta": [], "parcial": []}
    relacionados = [
        {"requisito": rid, "situacao": _status(reqs.get(rid))}
        for rid in rel["parcial"]
    ]
    if not rel["direta"]:
        return None, relacionados

    decisivos = [(rid, reqs.get(rid) or {}) for rid in rel["direta"]]
    status = [_status(e) for _, e in decisivos]

    lacunas = [s for s in status if s in ORDEM_LACUNA]
    if lacunas:
        situacao = min(lacunas, key=ORDEM_LACUNA.index)
        contam = [(rid, e) for rid, e in decisivos if _status(e) in ORDEM_LACUNA]
    elif "Atendido" in status:
        situacao = "Atendido"
        contam = [(rid, e) for rid, e in decisivos if _status(e) == "Atendido"]
    elif "Nao verificavel" in status:
        situacao = "Nao verificavel"
        contam = [(rid, e) for rid, e in decisivos if _status(e) == "Nao verificavel"]
    elif "Nao se aplica" in status:
        situacao = "Nao se aplica"
        contam = decisivos
    else:
        # Requisito ausente do report.json: o validador ja reclama; aqui so nao decide.
        return None, relacionados

    severidades = [report_data.canonical_term(e.get("severity"), report_data.SEVERITIES)
                   for _, e in contam]
    severidades = [s for s in severidades if s]
    severidade = min(severidades, key=ORDEM_SEVERIDADE.index) if severidades else None

    confiancas = [report_data.canonical_term(e.get("confidence"), report_data.CONFIDENCES)
                  for _, e in contam]
    confiancas = [c for c in confiancas if c]
    confianca = min(confiancas, key=ORDEM_CONFIANCA.index) if confiancas else None

    evidencias, vistas = [], set()
    for _, e in contam:
        for item in e.get("evidence") or []:
            if not isinstance(item, dict):
                continue
            chave = (item.get("file"), item.get("line"))
            if chave in vistas or not chave[0]:
                continue
            vistas.add(chave)
            # Sem `snippet`, de proposito (docstring do modulo).
            evidencias.append({"file": item.get("file"), "line": item.get("line")})

    ausencias = [(e.get("absence") or "").strip() for _, e in contam]
    return {
        "situacao": situacao,
        "severidade": severidade,
        "gravidade_devcomply": report_data.SEVERIDADE_DEVCOMPLY.get(severidade),
        "confianca": confianca,
        "requisitos": [rid for rid, _ in contam],
        "evidencias": evidencias[:5],
        "ausencia": " ".join(a for a in ausencias if a) or None,
    }, relacionados


def exportar(data):
    """report.json -> devcomply.json."""
    reqs = _por_requisito(data)
    por_item = report_data.lgpd_check_por_item()
    itens = []
    for codigo in report_data.LGPD_CHECK_CODIGOS:
        if codigo not in por_item:
            continue
        decisao, relacionados = situacao_do_item(codigo, reqs, por_item)
        item = {"codigo": codigo}
        if decisao:
            item.update(decisao)
        else:
            item["situacao"] = None
        item["relacionados"] = relacionados
        itens.append(item)

    # Achados da skill sem pergunta equivalente no checklist: o DevComply mostra a
    # parte, para o leitor saber que existem.
    sem_pergunta = []
    for rid in report_data.REQUIREMENT_IDS:
        if report_data.LGPD_CHECK[rid]["direta"]:
            continue
        entry = reqs.get(rid) or {}
        sem_pergunta.append({
            "requisito": rid,
            "titulo": report_data.REQUIREMENT_BY_ID[rid]["title"],
            "situacao": _status(entry),
            "severidade": report_data.canonical_term(entry.get("severity"),
                                                      report_data.SEVERITIES) or None,
        })

    repo = data.get("repo") or {}
    return {
        "schema": EXPORT_SCHEMA,
        "gerado_em": agora(),
        "origem": {
            "report_schema": data.get("schema"),
            "tool_version": data.get("tool_version"),
            "generated_at": data.get("generated_at"),
            "model": data.get("model"),
            "commit": repo.get("commit"),
        },
        "aviso": ("Situacao de cada item do LGPD-Check no codigo, levantada pela "
                  "lgpd-scan. Sem trechos de codigo: so arquivo e linha. Itens "
                  "parciais nao decidem a situacao; relacionados e contexto."),
        "itens": itens,
        "nao_verificavel": nao_verificavel(data),
        "so_a_organizacao": list(report_data.LGPD_CHECK_SO_ORGANIZACAO),
        "fora_da_skill": list(report_data.LGPD_CHECK_FORA_DA_SKILL),
        "requisitos_sem_item_direto": sem_pergunta,
    }


def _codigos_do_requisito(rid):
    rel = report_data.LGPD_CHECK.get(rid) or {"direta": [], "parcial": []}
    return list(rel["direta"]) + [c for c in rel["parcial"] if c not in rel["direta"]]


def nao_verificavel(data):
    """O que o codigo nao responde, em forma de pergunta para a equipe.

    Duas fontes: o requisito inteiro que ficou `Nao verificavel` (com a `note`), e
    cada entrada de `unverifiable` -- o que a auditoria suspeitou sem conseguir
    confirmar. O DevComply mostra cada uma como pergunta do checklist, ligada aos
    itens do LGPD-Check, e e isso que fecha o laco: o que a skill nao enxerga volta
    para quem pode responder.
    """
    saida = []
    for entry in data.get("requirements") or []:
        if not isinstance(entry, dict) or _status(entry) != "Nao verificavel":
            continue
        rid = entry.get("id")
        if rid not in report_data.REQUIREMENT_BY_ID:
            continue
        saida.append({
            "origem": "requisito",
            "requisito": rid,
            "assunto": report_data.REQUIREMENT_BY_ID[rid]["title"],
            "motivo": (entry.get("note") or "").strip() or None,
            "pergunta": None,
            "lgpd_check": _codigos_do_requisito(rid),
        })
    for entry in data.get("unverifiable") or []:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("requirement") or None
        codigos = [str(c).strip().upper() for c in entry.get("lgpd_check") or []]
        if not codigos and rid in report_data.LGPD_CHECK:
            codigos = _codigos_do_requisito(rid)
        saida.append({
            "origem": "auditoria",
            "requisito": rid,
            "assunto": (entry.get("topic") or "").strip(),
            "motivo": (entry.get("reason") or "").strip(),
            "pergunta": (entry.get("question") or "").strip() or None,
            "lgpd_check": codigos,
        })
    return saida


def ler_declaracoes(declaracoes):
    """Aceita o formato do DevComply e devolve {codigo: marcado} + avisos."""
    avisos = []
    if isinstance(declaracoes, list):
        itens = declaracoes
    else:
        if declaracoes.get("schema") not in (None, DECLARACOES_SCHEMA):
            avisos.append(f"schema {declaracoes.get('schema')!r}; esperado "
                          f"{DECLARACOES_SCHEMA!r} -- lido assim mesmo")
        itens = declaracoes.get("itens") or []

    marcados = {}
    for item in itens:
        if not isinstance(item, dict):
            continue
        codigo = str(item.get("codigo") or "").strip().upper()
        if codigo not in report_data.LGPD_CHECK_CODIGOS:
            avisos.append(f"codigo desconhecido no LGPD-Check: {codigo or '(vazio)'}")
            continue
        marcados[codigo] = bool(item.get("marcado"))
    return marcados, avisos


def conciliar(data, declaracoes):
    """Declaracoes do DevComply x situacao no codigo."""
    reqs = _por_requisito(data)
    por_item = report_data.lgpd_check_por_item()
    marcados, avisos = ler_declaracoes(declaracoes)

    itens = []
    for codigo in report_data.LGPD_CHECK_CODIGOS:
        if codigo not in marcados:
            continue
        marcado = marcados[codigo]
        decisao, relacionados = situacao_do_item(codigo, reqs, por_item)
        situacao = (decisao or {}).get("situacao")

        if codigo in report_data.LGPD_CHECK_SO_ORGANIZACAO:
            resultado = "so_a_organizacao"
        elif codigo in report_data.LGPD_CHECK_FORA_DA_SKILL:
            resultado = "fora_da_skill"
        elif decisao is None:
            resultado = "so_relacao_parcial"
        elif situacao == "Nao verificavel":
            resultado = "nao_verificavel_no_codigo"
        elif situacao == "Nao se aplica":
            resultado = "nao_se_aplica"
        elif marcado:
            resultado = {"Nao atendido": "declarado_sem_implementacao",
                         "Parcial": "declarado_com_lacuna",
                         "Atendido": "confirmado"}[situacao]
        else:
            resultado = ("implementado_sem_declaracao" if situacao == "Atendido"
                         else "lacuna_confirmada")

        item = {"codigo": codigo, "marcado": marcado, "resultado": resultado,
                "situacao_no_codigo": situacao}
        if decisao is None and relacionados:
            item["relacionados"] = relacionados
        if decisao:
            item["requisitos"] = decisao["requisitos"]
            item["severidade"] = decisao["severidade"]
            item["evidencias"] = decisao["evidencias"]
        itens.append(item)

    resumo = {r: 0 for r in RESULTADOS}
    for item in itens:
        resumo[item["resultado"]] += 1

    repo = data.get("repo") or {}
    return {
        "schema": CONCILIACAO_SCHEMA,
        "gerado_em": agora(),
        "origem": {"tool_version": data.get("tool_version"),
                   "commit": repo.get("commit"),
                   "generated_at": data.get("generated_at")},
        "declaracoes": {
            "projeto": (declaracoes or {}).get("projeto") if isinstance(declaracoes, dict) else None,
            "gerado_em": (declaracoes or {}).get("gerado_em") if isinstance(declaracoes, dict) else None,
            "itens": len(marcados),
        },
        "itens": itens,
        "divergencias": [i["codigo"] for i in itens if i["resultado"] in DIVERGENTES],
        "resumo": resumo,
        "avisos": avisos,
    }


def _gravar(caminho, conteudo):
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as handle:
        json.dump(conteudo, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _carregar_report(caminho):
    if not os.path.isfile(caminho):
        sys.stderr.write(f"erro: nao encontrei {caminho}. Rode a auditoria antes "
                         f"(o report.json e escrito no passo 5 do SKILL.md).\n")
        return None
    data = report_data.load(caminho)
    problemas = report_data.validate(data)
    if problemas:
        sys.stderr.write(f"erro: {caminho} fora do schema; corrija antes de exportar:\n")
        for p in problemas[:10]:
            sys.stderr.write(f"  {p}\n")
        return None
    return data


ROTULO = {
    "declarado_sem_implementacao": "!! declarado, o codigo nao mostra",
    "declarado_com_lacuna": "!  declarado, o codigo mostra lacuna",
    "confirmado": "ok confirmado",
    "implementado_sem_declaracao": "+  implementado, nao declarado",
    "lacuna_confirmada": "-  lacuna nos dois",
    "so_a_organizacao": "   so a organizacao prova",
    "fora_da_skill": "   a skill ainda nao avalia",
    "so_relacao_parcial": "   o codigo toca, sem decidir",
    "nao_verificavel_no_codigo": "?  nao verificavel no codigo",
    "nao_se_aplica": "   nao se aplica",
}


def main():
    parser = argparse.ArgumentParser(
        description="Liga a lgpd-scan ao DevComply pelos codigos do LGPD-Check.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_exp = sub.add_parser("export", help="report.json -> devcomply.json (sem trechos)")
    p_exp.add_argument("repo", nargs="?", default=".")
    p_exp.add_argument("--report", default=None)
    p_exp.add_argument("--out", default=None)

    p_con = sub.add_parser("conciliar", help="declaracoes do DevComply x codigo")
    p_con.add_argument("repo", nargs="?", default=".")
    p_con.add_argument("--declaracoes", required=True,
                       help="JSON exportado pelo DevComply (devcomply/declaracoes/1)")
    p_con.add_argument("--report", default=None)
    p_con.add_argument("--out", default=None)
    p_con.add_argument("--falhar-se-divergir", action="store_true",
                       help="sai com codigo 1 quando houver divergencia")

    args = parser.parse_args()
    report_path = args.report or os.path.join(args.repo, PADRAO_REPORT)
    data = _carregar_report(report_path)
    if data is None:
        return 2

    if args.cmd == "export":
        saida = exportar(data)
        destino = args.out or os.path.join(args.repo, PADRAO_EXPORT)
        _gravar(destino, saida)
        decididos = sum(1 for i in saida["itens"] if i.get("situacao"))
        print(f"ok: {destino} -- {decididos} itens do LGPD-Check decididos pelo "
              f"codigo, {len(saida['so_a_organizacao'])} so a organizacao prova")
        return 0

    if not os.path.isfile(args.declaracoes):
        sys.stderr.write(f"erro: nao encontrei {args.declaracoes}\n")
        return 2
    with open(args.declaracoes, "r", encoding="utf-8") as handle:
        declaracoes = json.load(handle)
    saida = conciliar(data, declaracoes)
    destino = args.out or os.path.join(args.repo, PADRAO_CONCILIACAO)
    _gravar(destino, saida)

    print("\n=== lgpd-scan: declarado (DevComply) x codigo ===\n")
    for item in saida["itens"]:
        reqs = ", ".join(item.get("requisitos") or []) or "-"
        print(f"  {item['codigo']}  {ROTULO[item['resultado']]:<38} "
              f"{item['situacao_no_codigo'] or '-':<15} {reqs}")
    for aviso in saida["avisos"]:
        print(f"  aviso: {aviso}")
    n = len(saida["divergencias"])
    print(f"\n{n} divergencia(s): {', '.join(saida['divergencias']) or 'nenhuma'}")
    if n:
        print("Cada uma entra na secao \"Declarado x codigo\" do relatorio; o "
              "verify_report.py confere.")
    print(f"gravado em {destino}\n")
    return 1 if (args.falhar_se_divergir and n) else 0


if __name__ == "__main__":
    sys.exit(main())
