#!/usr/bin/env python3
"""
lgpd-scan: portao de integracao continua.

Uma auditoria e uma foto. Ela envelhece na semana seguinte, porque o codigo continua
andando e a conformidade anda junto -- alguem adiciona uma coluna de CPF numa
migration, alguem commita uma chave, alguem remove a rota de exclusao de conta num
refactor. Este script transforma a foto em regra: roda o coletor a cada PR, compara
com a `baseline.json` da ultima vez e falha quando o que mudou piora a situacao.

**Por que isto so e possivel com um coletor deterministico.** Uma skill que chama
modelo da resposta diferente a cada execucao; um portao construido sobre isso oscila,
e time nenhum aceita um check que reprova hoje o que aprovou ontem. A separacao entre
coletor (regex, reproduzivel, hashavel) e julgamento (agente, caro, nao
deterministico) existe desde a primeira versao por outro motivo, e e ela que paga
aqui.

    python3 scripts/ci_check.py . --update-baseline     # grava o ponto de partida
    python3 scripts/ci_check.py .                       # compara e falha se piorou
    python3 scripts/ci_check.py . --fail-on media       # mais rigoroso
    python3 scripts/ci_check.py . --sarif lgpd.sarif    # aba Security do GitHub

Python 3.8+, biblioteca padrao.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

SCHEMA = "lgpd-scan/baseline/1"

# --------------------------------------------------------------------------
# A politica: o que cada sinal significa para um portao
# --------------------------------------------------------------------------
# Tres papeis, e a granularidade de cada um nao e a mesma -- foi a decisao que mais
# mudou o resultado em teste.
#
# RISCO e observado por (sinal, arquivo): uma credencial nova em `docker-compose.yml`
# e um achado ainda que ja houvesse outra em `.env`.
#
# CONTROLE e observado pelo repositorio inteiro: a rota de exclusao mudar de arquivo
# num refactor nao e regressao, e observar controle por arquivo transformaria toda
# reorganizacao de pastas em alarme. O que importa e ter sumido de vez.
#
# INVENTARIO nunca reprova sozinho: campo pessoal novo e o dia a dia de um produto
# que cresce. Entra no relatorio do portao como informacao, e so vira achado quando
# e dado sensivel ou terceiro novo, que sao decisoes, nao crescimento.

RISCOS = {
    "hardcoded_secret": ("alta", "credencial literal no codigo"),
    "private_key_block": ("alta", "bloco de chave privada"),
    "cloud_credential": ("alta", "credencial de provedor de nuvem"),
    "password_hash_weak": ("media", "hash fraco de senha"),
    "tls_disabled": ("media", "verificacao de certificado desativada"),
    "pii_in_log": ("media", "dado pessoal em log"),
    "placeholder_unfilled": ("media", "marcador nunca preenchido no texto legal"),
    "default_privacy_open": ("media", "padrao permissivo de privacidade"),
    "suspicious_instruction": ("media", "texto dirigido a quem audita"),
    # `age_self_declaration` NAO entra aqui. Coletar idade nao e risco por si; o
    # achado do ECA Digital e coletar sem nada que verifique, e isso e uma leitura
    # cruzada de dois sinais, tratada em `_achado_eca`. Quando estava nesta tabela,
    # o mesmo arquivo saia duas vezes no relatorio do portao, uma como baixa e outra
    # como alta -- e um portao que se repete e um portao que ninguem le inteiro.
}

CONTROLES = {
    "delete_route": "rota de exclusao",
    "delete_route_alt": "exclusao pelo titular",
    "export_route": "exportacao/portabilidade",
    "update_route": "correcao pelo titular",
    "consent_record": "registro de consentimento",
    "retention_marker": "marcador de retencao",
    "audit_trail": "trilha de auditoria",
    "password_hash_strong": "hash forte de senha",
    "encryption_at_rest": "cifragem em repouso",
    "incident_register": "registro de incidente",
    "incident_notification": "comunicacao de incidente",
    "dpo_contact": "canal do encarregado",
    "dsar_flow": "fluxo de pedido do titular",
    "anonymization": "anonimizacao",
    "transfer_safeguard": "salvaguarda de transferencia",
    "age_verification_provider": "verificacao de idade",
    "parental_link": "vinculo com responsavel",
    "content_removal": "remocao de conteudo",
}

# Crescimento que e decisao, nao rotina.
NOVIDADE_RELEVANTE = {
    "sensitive_data_field": ("media", "campo de dado sensivel novo"),
    "third_party_sdk": ("media", "terceiro novo recebendo dado"),
    "cloud_region": ("baixa", "regiao/destino novo"),
    "ad_targeting": ("media", "SDK de perfilamento publicitario novo"),
    "minor_flag": ("media", "o sistema passou a distinguir menor de idade"),
}

INVENTARIO = {"personal_data_field", "external_http_call", "dsar_deadline",
              "soft_delete_marker"}

ORDEM = {"alta": 3, "media": 2, "baixa": 1}


def _hits_por_arquivo(result, signal):
    por_arquivo = {}
    for hit in result["signals"].get(signal, []):
        entry = por_arquivo.setdefault(
            hit["file"], {"count": 0, "tracked": hit.get("tracked"),
                          "line": hit.get("line")})
        entry["count"] += 1
    return por_arquivo


def build_baseline(result):
    return {
        "schema": SCHEMA,
        "tool_version": result.get("tool_version"),
        "generated_at": result.get("generated_at"),
        "commit": (result.get("git") or {}).get("commit"),
        "listing_source": (result.get("git") or {}).get("listing_source"),
        "risks": {name: _hits_por_arquivo(result, name)
                  for name in sorted(RISCOS) if result["signals"].get(name)},
        "novelty": {name: sorted({h["file"] for h in result["signals"][name]})
                    for name in sorted(NOVIDADE_RELEVANTE)
                    if result["signals"].get(name)},
        "controls": sorted(name for name in CONTROLES if result["signals"].get(name)),
        "eca": {
            "self_declaration": bool(result["signals"].get("age_self_declaration")),
            "verification_provider": bool(
                result["signals"].get("age_verification_provider")),
        },
        "inventory": {name: len(result["signals"].get(name, []))
                      for name in sorted(INVENTARIO)
                      if result["signals"].get(name)},
    }


def compare(baseline, result):
    """Achados do portao: o que mudou e piora a situacao."""
    achados = []

    for signal, (severidade, rotulo) in sorted(RISCOS.items()):
        antes = (baseline.get("risks") or {}).get(signal, {})
        agora = _hits_por_arquivo(result, signal)
        for arquivo in sorted(set(agora) - set(antes)):
            info = agora[arquivo]
            nivel = severidade
            detalhe = rotulo
            # Segredo em arquivo rastreado sobrevive a propria remocao: apagar a
            # linha nao apaga o historico. Em arquivo ignorado e nota operacional.
            if signal in ("hardcoded_secret", "private_key_block", "cloud_credential"):
                if info["tracked"] is True:
                    detalhe += " em arquivo versionado (sobrevive a remocao)"
                elif info["tracked"] is False:
                    nivel = "media"
                    detalhe += " em arquivo ignorado pelo git"
            achados.append({
                "tipo": "risco_novo", "signal": signal, "severity": nivel,
                "file": arquivo, "line": info["line"], "message": detalhe,
            })

    presentes = {name for name in CONTROLES if result["signals"].get(name)}
    for signal in sorted(set(baseline.get("controls") or []) - presentes):
        achados.append({
            "tipo": "controle_removido", "signal": signal, "severity": "alta",
            "file": None, "line": None,
            "message": f"{CONTROLES.get(signal, signal)} existia na baseline e nao "
                       f"aparece mais em lugar nenhum do repositorio",
        })

    for signal, (severidade, rotulo) in sorted(NOVIDADE_RELEVANTE.items()):
        antes = set((baseline.get("novelty") or {}).get(signal) or [])
        agora = {h["file"]: h for h in result["signals"].get(signal, [])}
        for arquivo in sorted(set(agora) - antes):
            achados.append({
                "tipo": "novidade", "signal": signal, "severity": severidade,
                "file": arquivo, "line": agora[arquivo].get("line"),
                "message": rotulo,
            })

    achados.extend(_achado_eca(baseline, result))

    informativo = []
    for signal, antes in sorted((baseline.get("inventory") or {}).items()):
        agora = len(result["signals"].get(signal, []))
        if agora != antes:
            informativo.append(f"{signal}: {antes} -> {agora}")
    for signal in sorted(INVENTARIO):
        if signal not in (baseline.get("inventory") or {}) and result["signals"].get(signal):
            informativo.append(
                f"{signal}: 0 -> {len(result['signals'][signal])}")

    achados.sort(key=lambda a: (-ORDEM[a["severity"]], a["signal"], a["file"] or ""))
    return achados, informativo


def _achado_eca(baseline, result):
    """Coletar idade sem verificar: a leitura cruzada que o ECA Digital exige.

    A presenca de um campo de idade nao e achado, e a ausencia de verificacao
    tambem nao -- o achado e a combinacao, e so quando ela e nova. Um projeto que ja
    nasceu assim aparece na auditoria completa; o portao existe para o dia em que
    alguem adiciona o campo de data de nascimento sem o resto.
    """
    declara = bool(result["signals"].get("age_self_declaration"))
    verifica = bool(result["signals"].get("age_verification_provider"))
    if not declara or verifica:
        return []

    antes = baseline.get("eca") or {}
    ja_era_assim = antes.get("self_declaration") and not antes.get(
        "verification_provider")
    if ja_era_assim:
        return []

    hit = result["signals"]["age_self_declaration"][0]
    if antes.get("verification_provider"):
        motivo = ("a verificacao de idade existia na baseline e sumiu, e a coleta "
                  "por autodeclaracao continua")
    else:
        motivo = ("passou a coletar idade sem provedor de verificacao — a Lei "
                  "15.211/2025 veda a autodeclaracao")
    return [{
        "tipo": "eca_autodeclaracao", "signal": "age_self_declaration",
        "severity": "alta", "file": hit["file"], "line": hit["line"],
        "message": motivo,
    }]


def to_sarif(achados, root, tool_version):
    regras, vistos = [], set()
    for achado in achados:
        if achado["signal"] in vistos:
            continue
        vistos.add(achado["signal"])
        regras.append({
            "id": achado["signal"],
            "name": achado["signal"],
            "shortDescription": {"text": achado["message"][:120]},
            "help": {"text": "lgpd-scan: candidato levantado do codigo. Confirme "
                             "lendo o arquivo antes de tratar como achado."},
            "defaultConfiguration": {
                "level": {"alta": "error", "media": "warning",
                          "baixa": "note"}[achado["severity"]]},
        })

    resultados = []
    for achado in achados:
        location = []
        if achado["file"]:
            location = [{"physicalLocation": {
                "artifactLocation": {"uri": achado["file"].replace("\\", "/")},
                "region": {"startLine": max(1, achado["line"] or 1)},
            }}]
        resultados.append({
            "ruleId": achado["signal"],
            "level": {"alta": "error", "media": "warning",
                      "baixa": "note"}[achado["severity"]],
            "message": {"text": f"{achado['message']} ({achado['tipo']})"},
            "locations": location,
        })

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "lgpd-scan",
                "version": tool_version,
                "informationUri": "https://github.com/Oklama14/lgpd-scan",
                "rules": regras,
            }},
            "results": resultados,
        }],
    }


def render(achados, informativo, limite, baseline_info, out=None):
    out = out or sys.stdout.write
    out("\n=== lgpd-scan: portao de conformidade ===\n")
    out(f"baseline           {baseline_info}\n")
    contagem = {nivel: sum(1 for a in achados if a["severity"] == nivel)
                for nivel in ("alta", "media", "baixa")}
    out(f"achados            alta {contagem['alta']}, media {contagem['media']}, "
        f"baixa {contagem['baixa']}\n")
    out(f"reprova a partir de {limite}\n")

    if achados:
        out("\n-- o que mudou e piora --\n")
    for achado in achados:
        onde = f"{achado['file']}:{achado['line']}" if achado["file"] else "(repositorio)"
        out(f"  [{achado['severity']}] {onde}\n"
            f"           {achado['signal']}: {achado['message']}\n")

    if informativo:
        out("\n-- inventario (nao reprova) --\n")
        for item in informativo:
            out(f"  {item}\n")

    bloqueantes = [a for a in achados if ORDEM[a["severity"]] >= ORDEM[limite]]
    if bloqueantes:
        out(f"\n{len(bloqueantes)} achado(s) em nivel {limite} ou acima.\n")
        out("Cada um e um CANDIDATO levantado por expressao regular, nao um veredito:\n"
            "abra o arquivo antes de corrigir. Se for falso positivo, marque no codigo\n"
            "com `lgpd-scan: ignorar <sinal> — motivo` (o motivo e obrigatorio) e\n"
            "rode de novo.\n\n")
    else:
        out("\nNada novo que piore a conformidade desde a baseline.\n")
        out("Isso NAO significa conformidade: significa que nao houve regressao "
            "detectavel\nem codigo desde o ultimo ponto de comparacao.\n\n")
    return not bloqueantes


def main():
    parser = argparse.ArgumentParser(
        description="Portao de CI: compara o repositorio com a baseline de conformidade.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--baseline", default=None,
                        help="padrao: <repo>/.lgpd-scan/baseline.json")
    parser.add_argument("--update-baseline", action="store_true",
                        help="grava a baseline com o estado atual e sai")
    parser.add_argument("--fail-on", default="alta",
                        choices=["alta", "media", "baixa", "nenhum"],
                        help="nivel minimo que reprova (padrao: alta)")
    parser.add_argument("--sarif", default=None, help="grava o resultado em SARIF")
    parser.add_argument("--json", default=None, help="grava os achados em JSON")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not os.path.isdir(args.repo):
        sys.stderr.write(f"erro: {args.repo} nao existe\n")
        return 2

    result = collect.scan(args.repo, include_tests=args.include_tests, max_hits=200)
    listing_note = (result.get("git") or {}).get("listing_note")
    if listing_note:
        sys.stderr.write(f"aviso: {listing_note}\n")

    baseline_path = args.baseline or os.path.join(
        args.repo, ".lgpd-scan", "baseline.json")

    if args.update_baseline:
        baseline = build_baseline(result)
        os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
        with open(baseline_path, "w", encoding="utf-8") as handle:
            json.dump(baseline, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"baseline gravada em {baseline_path}")
        print(f"  {len(baseline['risks'])} sinal(is) de risco, "
              f"{len(baseline['controls'])} controle(s) presentes")
        return 0

    if not os.path.isfile(baseline_path):
        # Primeira execucao sem baseline nao pode reprovar: nao existe "piorou" sem
        # um ponto de comparacao, e um portao que reprova a PR que o instalou e
        # desinstalado na mesma tarde.
        sys.stderr.write(
            f"erro: nao encontrei {baseline_path}.\n"
            f"Rode uma vez com --update-baseline para gravar o ponto de partida "
            f"e commite o arquivo.\n")
        return 2

    with open(baseline_path, "r", encoding="utf-8") as handle:
        baseline = json.load(handle)
    if baseline.get("schema") != SCHEMA:
        sys.stderr.write(
            f"erro: {baseline_path} tem schema {baseline.get('schema')!r}, "
            f"esperado {SCHEMA!r}. Regrave com --update-baseline.\n")
        return 2

    achados, informativo = compare(baseline, result)

    if args.sarif:
        os.makedirs(os.path.dirname(os.path.abspath(args.sarif)) or ".", exist_ok=True)
        with open(args.sarif, "w", encoding="utf-8") as handle:
            json.dump(to_sarif(achados, args.repo,
                               result.get("tool_version", "?")), handle,
                      ensure_ascii=False, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"achados": achados, "inventario": informativo},
                      handle, ensure_ascii=False, indent=2)

    limite = args.fail_on
    info = f"{baseline_path} (commit {baseline.get('commit') or '?'})"
    if limite == "nenhum":
        render(achados, informativo, "baixa", info,
               out=(lambda _t: None) if args.quiet else None)
        return 0
    ok = render(achados, informativo, limite,
                info, out=(lambda _t: None) if args.quiet else None)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
