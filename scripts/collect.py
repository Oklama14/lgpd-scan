#!/usr/bin/env python3
"""
lgpd-scan collector.

Walks a repository, classifies files into buckets, and runs cheap regex detection
for the signals that matter to an LGPD audit. Emits JSON.

This tool deliberately does NOT judge anything. It answers one question -- "where
should a reviewer look?" -- and leaves every conclusion to the agent that reads its
output. A regex match is a hypothesis, never a finding.

Python 3.8+, standard library only, no network access.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

TOOL_VERSION = "0.5.0"

# --------------------------------------------------------------------------
# What we never walk into
# --------------------------------------------------------------------------

EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "bower_components", "vendor",
    "dist", "build", "out", "target", "bin", "obj", ".next", ".nuxt",
    "__pycache__", ".venv", "venv", "env", ".tox", ".mypy_cache",
    ".pytest_cache", ".gradle", ".mvn", ".idea", ".vscode", "coverage",
    ".nyc_output", ".terraform", ".serverless", ".cache", ".parcel-cache",
    ".angular", ".svelte-kit", "Pods", "DerivedData", ".lgpd-scan",
    # Configuracao de agente nao e o produto auditado. Alem de ruido, e onde esta
    # skill se instala: rodar a auditoria num projeto com a skill dentro fazia o
    # coletor ler a propria documentacao de referencia e reportar `tls_disabled` em
    # `references/requirements/base-lgpd.md` (que cita `rejectUnauthorized: false`
    # como exemplo) e `placeholder_unfilled` no modelo de politica. Ruido com cara
    # de evidencia, que e o pior tipo.
    ".claude", ".cursor", ".codex", ".gemini", ".opencode", ".windsurf",
}

TEST_DIR_HINTS = {"test", "tests", "spec", "specs", "__tests__", "e2e", "fixtures"}

# The tool's own output must never become its own input. A committed report quotes
# every signal it discusses, so scanning it produces a second generation of findings
# that cite the first -- noise that looks like evidence.
#
# The generated artefacts matter more than the report here, and in a way that is easy
# to miss: a ROPA or a DPA lands in the `legal` bucket by name, so on the next run the
# tool would read its own document as the project's privacy policy -- crediting its own
# ROPA as a declaration, and flagging its own pendency markers as R15 placeholders.
# The audit would then be quoting itself and calling it evidence.
OWN_OUTPUT = re.compile(
    r"(?i)(^|/)(RELATORIO-LGPD\.md|ROPA\.md|RIPD\.md|DPA-MINUTA[\w.\-]*\.md"
    r"|\.lgpd-scan/)")

TEXT_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".java", ".kt", ".kts",
    ".py", ".rb", ".php", ".go", ".rs", ".cs", ".scala", ".groovy",
    ".sql", ".prisma", ".graphql", ".gql",
    ".json", ".yml", ".yaml", ".xml", ".properties", ".toml", ".ini", ".conf",
    ".env", ".sh", ".bash", ".tf", ".tfvars", ".gradle", ".md", ".txt", ".html",
}

# Files where a personal-data field name means a field, not prose. The lexicon
# signals run only here: `email` in a migration is an inventory entry, `email` in a
# planning document is a word.
CODE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".java", ".kt", ".kts",
    ".py", ".rb", ".php", ".go", ".rs", ".cs", ".scala", ".groovy",
    ".sql", ".prisma", ".graphql", ".gql", ".html", ".vue", ".svelte",
}

MAX_FILE_BYTES = 1_500_000
SNIPPET_MAX = 160

# One noisy file must not eat the whole per-signal budget. Without this, forty hits
# from a single seed file leave the rest of the repository invisible.
MAX_HITS_PER_FILE = 5

# --------------------------------------------------------------------------
# Bucket classification -- by path and filename, never by content
# --------------------------------------------------------------------------

BUCKET_RULES = [
    ("schema", [
        r"(^|/)migrations?/", r"(^|/)db/migrate/", r"(^|/)changelog",
        r"\.sql$", r"schema\.prisma$", r"\.entity\.(ts|js)$",
        r"(^|/)entities?/", r"(^|/)models?/", r"(^|/)domain/",
        r"Entity\.java$", r"(^|/)liquibase", r"(^|/)flyway",
        r"schema\.(rb|ts|js|json)$",
        # Personal data is declared as often in the transport layer as in the
        # persistence layer -- a CreateUserDto lists exactly the fields collected.
        r"(^|/)dtos?/", r"\.dto\.(ts|js)$", r"Dto\.java$",
        r"(^|/)forms?/", r"(^|/)serializers?/", r"(^|/)validators?/",
        r"(^|/)schemas?/", r"(^|/)payloads?/",
        r"Request\.java$", r"Response\.java$",
    ]),
    ("api", [
        r"\.controller\.(ts|js)$", r"Controller\.java$", r"Resource\.java$",
        r"(^|/)routes?/", r"(^|/)controllers?/", r"(^|/)handlers?/",
        r"(^|/)api/", r"(^|/)endpoints?/", r"router\.(ts|js)$",
        r"\.resolver\.(ts|js)$",
    ]),
    ("security", [
        r"(^|/)auth", r"security", r"jwt", r"passport", r"guard",
        r"PasswordEncoder", r"(^|/)crypto", r"encryption",
    ]),
    ("config", [
        r"(^|/)\.env", r"docker-compose", r"[Dd]ockerfile",
        r"application.*\.(ya?ml|properties)$", r"(^|/)config/",
        r"\.github/workflows/", r"\.gitlab-ci", r"(^|/)k8s/", r"\.tfvars$",
    ]),
    ("deps", [
        r"(^|/)package\.json$", r"(^|/)pom\.xml$", r"(^|/)build\.gradle",
        r"requirements.*\.txt$", r"(^|/)Gemfile$", r"(^|/)composer\.json$",
        r"(^|/)go\.mod$", r"(^|/)Cargo\.toml$",
    ]),
    ("logging", [
        r"logback", r"log4j", r"logger", r"logging", r"winston", r"pino",
    ]),
    ("legal", [
        r"privacidade", r"privacy", r"termos", r"terms", r"lgpd", r"gdpr",
        r"cookie",
        # Um arquivo chamado so `politica.html` e a politica de privacidade em
        # metade dos projetos brasileiros, e sem o bucket legal ele era lido como
        # se fosse codigo: os achados dele entravam sem `declaration_only`, isto e,
        # a promessa era creditada como implementacao. So extensao de documento --
        # `politica.ts` costuma ser regra de autorizacao, que e codigo de verdade.
        r"(^|/)politicas?/",
        r"(^|/)politica[\w.\-]*\.(html?|md|txt)$",
        r"(^|/)(aviso|consentimento|eula)[\w.\-]*\.(html?|md|txt)$",
        r"(^|/)legal/",
    ]),
]

BUCKET_RULES = [(name, [re.compile(p, re.I) for p in pats]) for name, pats in BUCKET_RULES]

# --------------------------------------------------------------------------
# Signals -- what to grep for, per line
#
# Each signal is (name, compiled regex, which buckets it is worth checking in).
# An empty bucket set means "any file".
# --------------------------------------------------------------------------

PERSONAL_FIELDS = (
    r"cpf|cnpj|rg|nome|sobrenome|full_?name|first_?name|last_?name|"
    r"e?_?mail|telefone|celular|phone|mobile|whatsapp|"
    r"endereco|address|logradouro|cep|zip_?code|bairro|complemento|"
    r"nasc\w*|birth_?date|dob|idade|age|"
    r"genero|gender|sexo|estado_?civil|"
    r"foto|avatar|profile_?pic|"
    r"ip_?address|user_?agent|latitude|longitude|geoloc\w*|"
    r"cartao|card_?number|pix|conta_?bancaria|agencia|"
    r"nis|pis|titulo_?eleitor|cnh|passaporte|passport|"
    r"matricula|documento|salario|renda"
)

SENSITIVE_FIELDS = (
    r"saude|health|doenca|disease|diagnostic\w*|prontuario|medic(o|a|al|amento)|"
    r"sanguineo|blood_?type|gravidez|gestante|vacina|cirurgia|internacao|"
    r"exame|laudo|psicolog|psiquiatr|sorologi|transfusao|comorbidade|"
    # `cid` puro e o nome mais comum de coluna de dado de saude em sistema
    # brasileiro -- o proprio template do relatorio usa `cid` como exemplo, e o
    # coletor nao o detectava. Esta regra nao tem fronteira a direita (os termos sao
    # prefixos de proposito: `religi`, `biometri`), entao `cid` precisa da dele, ou
    # casaria `cidade` e `cidadao`, que sao endereco e prosa.
    r"cid(?:_?1[01])?(?![A-Za-z])|"
    r"alergia|allerg|deficien|disabilit|"
    r"religi|raca|etnia|ethnic|racial|"
    r"sindicat|union_?member|partido|filiacao_?partidaria|"
    # "politica" in Portuguese means "policy" at least as often as "politics", and a
    # privacy-policy page is not political-opinion data. Require the political sense.
    r"opiniao_?politica|political_?(opinion|affiliation|party|view)|"
    r"orientacao_?sexual|sexual_?orientation|"
    r"biometri|digital_?impressao|impressao_?digital|face_?id|reconhecimento_?facial|"
    r"genetic|dna_"
)

# A boundary where `_` counts as a separator. Python's \b does not, which is why
# `\bnascimento\b` silently fails to match `data_nascimento`.
LB = r"(?<![A-Za-z0-9])"
RB = r"(?![A-Za-z0-9])"

CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

ACCENTS = str.maketrans(
    "áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ",
    "aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN",
)


def deaccent(text):
    """Strip accents before matching.

    Identifiers in code are usually unaccented, so this went unnoticed while the
    signals only read code. It stops being invisible the moment they read prose:
    a privacy policy says "exclusao da conta" as "exclusão da conta", and every
    ASCII pattern in this file silently misses it. All patterns here are ASCII, so
    folding the haystack is safe and removes the whole class of miss at once.
    """
    return text.translate(ACCENTS)


def normalise_identifiers(text):
    """Split camelCase so the field lexicons see word edges.

    `dataNascimento` becomes `data_Nascimento`, which LB/RB can then bracket. Only
    the two lexicon signals use this -- applying it everywhere would break patterns
    that depend on camelCase spelling, such as `@DeleteMapping`.
    """
    return CAMEL_BOUNDARY.sub("_", text)


LEXICON_SIGNALS = {"personal_data_field", "sensitive_data_field"}

# Todo sinal que procura NOME DE IDENTIFICADOR sofre do mesmo problema: `\b` nao
# dispara antes de `_`, e camelCase nao tem separador nenhum. Em vez de remendar
# regex por regex, estes sinais passam pela normalizacao de camelCase e usam LB/RB
# no lugar de `\b`. Foi uma fixture do ECA Digital que expos a recaida:
# `vinculo_responsavel_em` nao casava com `vinculo_?responsavel\b`.
IDENTIFIER_SIGNALS = LEXICON_SIGNALS | {
    "age_self_declaration", "age_verification_provider", "parental_link",
    "minor_flag", "content_removal", "ad_targeting", "default_privacy_open",
    "incident_register", "incident_notification", "transfer_safeguard",
    "dsar_flow", "anonymization",
}

# Bucketing these by path was a recall bug: `src/users/dto/create-user.dto.ts`
# matches no bucket, so a DTO declaring cpf, nome and dataNascimento was invisible.
# They now run over every code file instead, held in check by the noise filter and
# the per-file cap.
# Planning documents talk about consent, auditing and bcrypt constantly. Those are
# discussions, not implementations, and a report must never cite a .md as evidence
# that something is built.
CODE_ONLY_SIGNALS = LEXICON_SIGNALS | {
    "pii_in_log", "consent_record", "audit_trail", "retention_marker",
    "password_hash_strong", "password_hash_weak", "encryption_at_rest",
    "soft_delete_marker", "delete_route_alt",
    # ECA Digital: todos falam de implementacao, nao de intencao. A politica de
    # privacidade dizendo "verificamos a idade" nao e verificacao de idade.
    "age_self_declaration", "age_verification_provider", "parental_link",
    "minor_flag", "default_privacy_open", "content_removal",
    # Resolucoes da ANPD: idem. Um plano de acao dizendo "implementar trilha de
    # incidentes" nao e trilha de incidentes.
    "incident_register", "incident_notification", "transfer_safeguard",
    "dsar_flow", "dsar_deadline", "anonymization",
    # O plano de acao do proprio projeto auditado dizia "instruir o modelo a
    # ignorar instrucoes vindas do texto" — descricao da mitigacao, nao ataque.
    # Um sinal que acusa a vitima de ser o agressor gasta a confianca do leitor
    # mais rapido do que um achado perdido, entao este fica restrito a codigo.
    "suspicious_instruction",
}

# The inventory requirement needs breadth, not a sample: a 40-hit cap on a schema
# with many personal fields silently truncates the very thing R01 must enumerate.
HIGH_VOLUME_SIGNALS = LEXICON_SIGNALS

# A third party is declared in a dependency manifest or reached from code. Prose that
# mentions "Gemini" or "Sentry" in a planning document declares nothing, and letting
# it match turned a 1-hit signal into 27.
MANIFEST_OR_CODE_SIGNALS = {
    "third_party_sdk", "cloud_region", "external_http_call",
    # SDK de anuncio aparece no manifesto de dependencia tanto quanto no codigo.
    "ad_targeting",
}
MANIFEST_BUCKETS = {"deps", "config"}

SIGNAL_RULES = [
    # ---- what personal data exists
    # LB/RB instead of \b: in `data_nascimento` the underscore is a word character,
    # so \b never fires between them and the field is missed entirely -- exactly the
    # naming convention these codebases use. See normalise_identifiers() for the
    # camelCase half of the same problem.
    ("personal_data_field",
     rf"(?i){LB}({PERSONAL_FIELDS}){RB}",
     set()),
    ("sensitive_data_field",
     rf"(?i){LB}({SENSITIVE_FIELDS})",
     set()),

    # ---- rights of the data subject
    # These four only locate routes. Deciding which DELETE is "erasure of the data
    # subject's account" and which merely removes a row is the reviewer's job, and
    # a regex that tries to guess it produces both false positives and, worse,
    # false absences -- the class-level @Controller('users') that gives the route
    # its meaning usually sits far above the decorator.
    ("delete_route",
     r"(?i)(@Delete\b|@DeleteMapping|\.(delete|destroy)\s*\(|router\.delete|"
     r"app\.delete|def\s+delete|DELETE\s+FROM)",
     {"api", "schema"}),
    # A forma nominal e tao comum quanto a verbal -- "exclusao da conta" aparece
    # mais em politica e em rota nomeada do que "excluir conta" -- e o conector
    # curto ("da", "de") separa as duas palavras na maioria dos textos.
    ("delete_route_alt",
     r"(?i)(excluir|exclusao|deletar|delecao|remover|remocao|encerrar|"
     r"encerramento|cancelar|cancelamento|apagar|apagamento|eliminar|eliminacao)"
     r"([-_ ]|\s+d[ao]s?\s+)?(conta|cadastro|usuario|perfil|dados)",
     set()),
    ("export_route",
     r"(?i)(portabilidade|meus[-_]?dados|my[-_]?data|data[-_]?export|"
     r"export[-_]?(data|dados|user)|download[-_]?(dados|data)|"
     r"((@Get|@GetMapping|\.get)\s*\(.{0,60}?(export|download)))",
     set()),
    ("update_route",
     r"(?i)(@Patch\b|@Put\b|@PutMapping|@PatchMapping|\.(put|patch)\s*\(|"
     r"router\.(put|patch)|app\.(put|patch))",
     {"api"}),

    # ---- lawful basis
    ("consent_record",
     r"(?i)\b(consent(imento|o)?|opt_?in|aceite_?termos|termo_?aceito|"
     r"accepted_?(terms|privacy)|privacy_?accepted|lgpd_?aceite)\b",
     set()),

    # ---- retention
    # Bare `ttl` matched every rate-limiter config and meant nothing for retention.
    ("retention_marker",
     r"(?i)\b(data_?retention|retention_?(period|days|policy)|retencao_?de_?dados|"
     r"expurgo|purge_?(old|data|job)|expires_?at|expira_?em|valid_?until|"
     r"@Scheduled|cron\.schedule|node-cron|anonimiz|anonymiz|pseudonimiz)\b",
     set()),
    ("soft_delete_marker",
     r"(?i)\b(deleted_?at|excluido_?em|is_?deleted|ativo\s*=|@SQLDelete|"
     r"paranoid\s*:\s*true|softDelete)\b",
     set()),

    # ---- security of storage
    ("password_hash_strong",
     r"(?i)\b(bcrypt|argon2|scrypt|pbkdf2|BCryptPasswordEncoder|"
     r"Argon2PasswordEncoder|password_hash\s*\()",
     set()),
    ("password_hash_weak",
     r"(?i)(createHash\s*\(\s*['\"](md5|sha1)|MessageDigest\.getInstance\s*\(\s*"
     r"\"(MD5|SHA-1)\"|NoOpPasswordEncoder|\bmd5\s*\(|hashlib\.(md5|sha1)\s*\()",
     set()),
    ("encryption_at_rest",
     r"(?i)\b(createCipheriv|AES[-_/]?(256|GCM|CBC)|Cipher\.getInstance|"
     r"pgcrypto|encrypt\s*\(|@Convert\b.*Crypt)",
     set()),
    ("tls_disabled",
     r"(?i)(rejectUnauthorized\s*:\s*false|verify\s*=\s*False|"
     r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|trustAllCerts|sslmode=disable)",
     set()),

    # ---- secrets in the repository
    # Two shapes: quoted values in code, and bare values in yml/properties/env/compose.
    ("hardcoded_secret",
     r"(?i)(password|passwd|pass|pwd|senha|secret|api[-_]?key|apikey|access[-_]?key|"
     r"auth[-_]?token|client[-_]?secret|private[-_]?key|jwt[-_]?secret)"
     r"\s*[:=]\s*(['\"][^'\"$\{\}<>\s]{6,}['\"]|[^\s'\"$\{\}<>#]{6,})\s*;?\s*$",
     set()),
    ("private_key_block",
     r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
     set()),
    ("cloud_credential",
     r"(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{20,}|sk-[A-Za-z0-9]{20,}|"
     r"ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})",
     set()),

    # ---- data minimisation in logs
    ("pii_in_log",
     rf"(?i)(console\.(log|info|warn|error)|logger?\.(info|debug|warn|error|log)|"
     rf"System\.out\.print|print\s*\().{{0,120}}?\b({PERSONAL_FIELDS})\b",
     set()),

    # ---- record of processing operations
    ("audit_trail",
     r"(?i)\b(audit|auditoria|trilha_?auditoria|access_?log|log_?acesso|"
     r"@EntityListeners|@Audited|envers|@CreatedBy|@LastModifiedBy)\b",
     set()),

    # ---- sharing and international transfer
    ("external_http_call",
     r"(?i)(fetch|axios|got|request|RestTemplate|WebClient|HttpClient|"
     r"requests\.(get|post))\s*[\.\(].{0,60}https?://([a-z0-9.-]+)",
     set()),
    ("third_party_sdk",
     r"(?i)\b(google-analytics|gtag|googletagmanager|facebook|meta-pixel|"
     r"hotjar|mixpanel|amplitude|segment|sentry|datadog|new-?relic|"
     r"firebase|onesignal|intercom|clarity\.ms|"
     # AI providers receive whatever the application sends them for inference, which
     # in a compliance tool is often the most sensitive payload in the whole system.
     r"generative-?ai|gemini|openai|anthropic|vertex-?ai|bedrock|cohere|huggingface|"
     r"mistral|azure-?openai|"
     r"stripe|mercadopago|pagseguro|twilio|sendgrid|mailgun|nodemailer|"
     r"aws-sdk|@aws-sdk|cloudinary|s3\.amazonaws)\b",
     set()),
    ("cloud_region",
     r"(?i)\b(us-east-[0-9]|us-west-[0-9]|eu-west-[0-9]|eu-central-[0-9]|"
     r"sa-east-[0-9]|ap-south[a-z]*-[0-9])\b",
     set()),

    # ---- Resolucoes da ANPD, so o que deixa rastro em codigo
    # Res. 15/2024: comunicacao em 3 dias uteis (em dobro para agente de pequeno
    # porte) e registro do incidente por, no minimo, cinco anos. O registro e a
    # parte verificavel: ou existe tabela/log de incidente, ou nao existe.
    ("incident_register",
     rf"(?i){LB}(incidentes?_?(de_?)?seguranca|security_?incidents?|data_?breach|"
     rf"vazamento_?(de_?)?dados|breach_?(log|register|registry|record)|"
     rf"registro_?de_?incidentes?|incidents?_?(log|table|report))",
     set()),
    ("incident_notification",
     rf"(?i){LB}(notificar_?anpd|comunicar_?(incidente|anpd)|breach_?notification|"
     rf"notify_?(authority|anpd|dpa)|comunicacao_?de_?incidente|"
     rf"prazo_?(de_?)?comunicacao)",
     set()),
    # Res. 18/2024: encarregado indicado e canal de atendimento ao titular.
    ("dpo_contact",
     rf"(?i)(dpo@|encarregado@|privacidade@|privacy@|protecao_?de_?dados@"
     rf"|{LB}(encarregado_?(de_?dados)?|data_?protection_?officer|dpo_?(email|contato"
     rf"|contact))|canal_?(do_?)?titular)",
     set()),
    # O marcador nunca preenchido e um achado, nao um detalhe de redacao: a politica
    # manda o titular procurar um canal que nao existe. Restrito ao texto legal,
    # porque TODO em codigo e outra conversa.
    # TODO e FIXME so contam em CAIXA ALTA, e nao por elegancia: "todo" e uma das
    # palavras mais comuns do portugues, e "Todo titular tem direito de acesso" numa
    # politica de privacidade legitima virava marcador nao preenchido. Terceira
    # aparicao da mesma familia de erro (depois de `unico` e `responsavel`): padrao
    # curto, case-insensitive, lido contra prosa.
    ("placeholder_unfilled",
     r"(?i)(\[\s*e-?mail\s*\]|\[\s*inserir[^\]]{0,30}\]|\[\s*preencher[^\]]{0,30}\]"
     r"|\[\s*nome[^\]]{0,20}\]|<inserir[^>]{0,30}>"
     # Chaves duplas so contam com vocabulario de preenchimento: `{{ versao }}` num
     # template Angular ou Handlebars de politica e interpolacao, nao buraco de
     # modelo, e o bucket legal agora alcanca exatamente esses arquivos.
     r"|\{\{\s*(?:inserir|preencher|informar|nome|e-?mail|empresa|razao|cnpj|cpf|dpo|"
     r"encarregado|endereco|telefone|definir|xxx|todo)[^}]{0,40}\}\}"
     r"|lorem ipsum|a_definir|[:=]\s*a\s+definir"
     r"|(?-i:\bTODO\b|\bFIXME\b|\bXXXX+\b))",
     {"legal"}),
    # Res. 19/2024: salvaguarda que fundamenta a transferencia internacional.
    ("transfer_safeguard",
     rf"(?i){LB}(clausulas?_?(contratuais_?)?padrao|standard_?contractual|"
     rf"\bsccs?\b|clausulas?_?especificas|normas_?corporativas_?globais|"
     rf"binding_?corporate_?rules|\bbcrs?\b|decisao_?de_?adequacao|"
     rf"adequacy_?decision|garantias_?adequadas)",
     set()),
    # Art. 18, §1o: prazo de atendimento ao titular.
    ("dsar_flow",
     rf"(?i){LB}(solicitacao_?(do_?)?titular|requisicao_?(do_?)?titular|"
     rf"pedido_?(do_?)?titular|data_?subject_?request|\bdsar\b|"
     rf"direitos_?do_?titular|subject_?access_?request)",
     set()),
    ("dsar_deadline",
     rf"(?i)((15|quinze)\s*dias(\s*(uteis|corridos))?|{LB}(prazo_?(de_?)?resposta|"
     rf"response_?deadline|sla_?(titular|atendimento)|deadline_?days))",
     set()),
    # Art. 12: anonimizacao e pseudonimizacao.
    ("anonymization",
     rf"(?i){LB}(anonimiz\w*|anonymiz\w*|pseudonimiz\w*|pseudonymiz\w*|"
     rf"k_?anonymity|token_?vault|tokeniz\w*|mascaramento|data_?masking|"
     rf"redact\w*|hash_?irreversivel)",
     set()),

    # ---- ECA Digital (Lei 15.211/2025), em vigor desde 17/03/2026
    # A lei veda a autodeclaracao de idade, o que torna um campo de nascimento ou
    # uma caixa "sou maior de 18" evidencia de NAO conformidade em vez de controle.
    # O par age_self_declaration / age_verification_provider e o que permite ao
    # agente distinguir "coleta a idade e confia" de "coleta e verifica".
    ("age_self_declaration",
     rf"(?i){LB}(maior_?de_?idade|sou_?maior|over_?(18|16|13)|is_?adult|"
     rf"confirmo_?que_?tenho|declaro_?ser_?maior|age_?gate|idade_?minima|"
     rf"age_?check(box)?|(data_?de_?)?nasc\w*\s*[:=]|birth_?date\s*[:=]|"
     rf"idade\s*[:=])",
     set()),
    ("age_verification_provider",
     rf"(?i){LB}(serpro|acesso\.gov\.br|gov_?br_?(auth|login|oauth|sso|id)|"
     rf"idwall|unico_?(check|id|idcloud)|@unico/|bigdatacorp|caf\.io|clearsale|"
     rf"didit|yoti|veriff|jumio|onfido|sumsub|persona_?id|stripe_?identity|"
     rf"age_?verification|verificacao_?de_?idade|document_?check|liveness)",
     set()),
    ("parental_link",
     rf"(?i){LB}(responsavel_?(legal|id)|vinculo_?responsavel\w*|"
     rf"guardian(_?id|_?account)?|parent_?(id|account|consent)|tutor_?id|"
     rf"supervised_?account|conta_?supervisionada)",
     set()),
    ("minor_flag",
     rf"(?i){LB}(is_?minor|eh_?menor|menor_?de_?idade|faixa_?etaria|age_?group|"
     rf"age_?band|child_?account|conta_?infantil|kids_?mode)",
     set()),
    # Configuracao padrao no nivel mais protetivo: um default permissivo e o achado.
    ("default_privacy_open",
     r"(?i)((is_?public|publico|visibility|visibilidade|searchable|discoverable|"
     r"perfil_?publico)\s*[:=]\s*(true|'public'|\"public\"|1)\b"
     r"|default\s*:\s*(true|'public'|\"public\")\s*\}?\s*\)?\s*(public|is_?public|"
     r"visib|searchable))",
     set()),
    # Perfilamento publicitario direcionado a menores e vedado.
    ("ad_targeting",
     rf"(?i){LB}(admob|adsense|doubleclick|adservices|ad_?manager|fbq\(|"
     rf"remarketing|lookalike|custom_?audience|audience_?network|"
     rf"interest_?based_?ads?|ad_?targeting|segmentacao_?publicitaria)",
     set()),
    ("content_removal",
     rf"(?i){LB}(denuncia(r|s)?_?(conteudo|post|usuario)?|report_?(content|abuse|post)|"
     rf"moderacao|moderation_?queue|takedown|remover_?conteudo|remove_?content|"
     rf"flag_?content|canal_?de_?denuncia)",
     set()),

    # ---- prompt injection attempts aimed at this very audit
    # "ignore as instrucoes anteriores" e a forma mais natural do ataque em
    # portugues, e a versao anterior deste padrao perdia exatamente ela: exigia a
    # palavra de direcao logo depois do artigo, sem espaco para o substantivo.
    ("suspicious_instruction",
     r"(?i)((ignore|ignorar|desconsidere|desconsiderar|disregard|esqueca)\s"
     r".{0,40}?(previous|above|anterior|acima|prompt|instru)"
     r"|marque? (tudo )?como conforme|mark .{0,20}as compliant"
     r"|this file is exempt|nao audite|do not audit|skip this file)",
     set()),
]

SIGNAL_RULES = [(n, re.compile(p), b) for n, p, b in SIGNAL_RULES]

# O haystack e dobrado para ASCII antes do casamento, entao um padrao com acento
# nunca casaria com nada. Isso aconteceu de verdade: `nao audite` estava escrito
# com til e ficou morto no instante em que o deaccent entrou. A guarda abaixo faz
# o erro aparecer na importacao, nao num relatorio seis meses depois.
_acentuados = [n for n, p, _ in SIGNAL_RULES if not p.pattern.isascii()]
if _acentuados:  # pragma: no cover
    raise AssertionError(
        "padrao com caractere acentuado nunca casa (o haystack e dobrado): "
        + ", ".join(_acentuados))

# Routes rarely fit on one line: a decorator sits above the handler it decorates,
# so `@Delete(':id')` and `removeUser(...)` are two lines apart. These signals are
# matched against a small joined window instead of a single line.
# Only export_route needs to see across lines: an @Get decorator on one line and
# the path it maps on the next. The other route signals are single tokens now, and
# joining lines for them would just report the same route once per overlapping
# window. Overlapping windows are collapsed by the proximity check in scan().
# pii_in_log needs the window for a reason the DevComply run made obvious: a logger
# call is routinely split across lines, with `this.logger.error(` on one and the
# interpolated e-mail on the next. Matching line by line missed a real finding.
WINDOW_SIGNALS = {"export_route", "pii_in_log"}
WINDOW_LINES = 3

# Comments and import statements mention field names constantly without declaring
# anything ("// salva o documento", "import { HealthModule }"). For signals that are
# supposed to find declarations, those lines are noise. Signals that legitimately
# live in comments -- suspicious_instruction above all -- are excluded from this.
NOISE_SKIP_SIGNALS = {
    "personal_data_field", "sensitive_data_field", "consent_record",
    "retention_marker", "audit_trail", "soft_delete_marker", "third_party_sdk",
    "age_self_declaration", "age_verification_provider", "parental_link",
    "minor_flag", "default_privacy_open", "ad_targeting", "content_removal",
    "incident_register", "incident_notification", "dpo_contact",
    "transfer_safeguard", "dsar_flow", "dsar_deadline", "anonymization",
}

COMMENT_PREFIXES = ("//", "#", "*", "/*", "--", "<!--", '"""', "'''")

# --------------------------------------------------------------------------
# Anotacoes no codigo: supressao e declaracao
# --------------------------------------------------------------------------
#
# Supressao existe porque o que mata o habito de usar a ferramenta nao e o erro,
# e o erro que nao morre: sem um jeito de dizer "isto aqui esta certo", o mesmo
# falso positivo volta identico em toda execucao. Tres decisoes de desenho:
#
# 1. E aplicada AQUI, por codigo, e nao por instrucao no SKILL.md. Supressao que
#    depende do agente lembrar de respeitar e discricionaria, e um dia ele passa
#    reto.
# 2. O motivo e obrigatorio. Marcador sem justificativa nao e honrado — supressao
#    sem motivo e exatamente como divida de conformidade se esconde.
# 3. Nada desaparece: o que foi suprimido vai para `suppressed` no JSON, com o
#    motivo, para o relatorio poder mostrar numa secao propria. Num relatorio de
#    conformidade, achado que some silenciosamente e pior que ruido.
#
# A sintaxe de comentario nao importa (`//`, `#`, `--`, `<!--`): o que se procura
# e o marcador, na propria linha ou na linha imediatamente acima.
# Reconhecer o marcador e exigir o motivo sao duas etapas de proposito. Na primeira
# versao eram uma so, e o efeito foi ruim: uma supressao sem motivo simplesmente
# nao casava, entao nao era honrada (correto) e nao era reportada (errado) — o dev
# escrevia o marcador, nada acontecia, e nao tinha como descobrir o porque. Regra
# silenciosa e vivida como ferramenta quebrada.
# Um documento que a propria ferramenta gerou (politica, ROPA, RIPD) fica no
# repositorio e cai no bucket `legal` pelo nome. Ler isso como "a declaracao do
# projeto" torna a reconciliacao politica x codigo circular: a ferramenta confere o
# texto que ela mesma escreveu a partir daquele codigo e conclui, sem surpresa, que
# batem. O marcador nao exclui o arquivo -- ele continua sendo a politica viva do
# projeto, e o R15 precisa enxerga-lo -- mas as ocorrencias saem etiquetadas para o
# relatorio poder dizer de onde o texto veio.
GENERATED_MARKER = re.compile(
    r"<!--\s*lgpd-scan\s*:\s*generated\b|@lgpd-scan\s*:\s*generated\b", re.I)

SUPPRESSION_MARKER = re.compile(
    r"lgpd-scan\s*:\s*ignor(?:e|ar)\s+(?P<signal>[a-z_]+|\*)(?P<rest>.*)$", re.I)

SUPPRESSION_REASON = re.compile(
    r"^\s*(?:—|–|--|-|:)\s*(?P<reason>\S.*?)\s*(?:\*/|-->|\*\))?\s*$")

# Declaracao positiva. O vocabulario `@lgpd:` ja e usado pelas duas outras skills
# de LGPD em circulacao, entao ler o mesmo formato da interoperabilidade de graca:
# quem anotou o schema para elas nao anota de novo para esta.
ANNOTATION = re.compile(
    r"@lgpd:\s*(?P<kind>[a-z_]+)\s*=\s*(?P<value>[^\s*/;,]+)", re.I)
# Somente import e package. `export class Foo` estava aqui por causa de um falso
# positivo antigo do export_route, que depois foi corrigido no proprio padrao — e
# manter a linha na lista de ruido passou a esconder evidencia legitima: para um
# sinal baseado em nome de entidade, `export class SecurityIncident` E o achado.
IMPORT_LINE = re.compile(
    r"^\s*(import\b|from\s+\S+\s+import\b|package\b|using\b|require\s*\()"
)

# Words that collide with the lexicons but mean something else in code.
# A literal after `password:` is only a secret if it is a value. These are the four
# shapes that are not: a reference to configuration, a type annotation, a function
# call, and a placeholder in an example file.
NOT_A_SECRET = re.compile(
    r"(?i)"
    r"(process\.env|import\.meta\.env|System\.getenv|os\.environ|ENV\[|"
    r"config(Service)?\.get|@Value|\$\{|<%|%\()"          # configuration reference
    r"|:\s*(string|number|boolean|any|Date|String|Integer|char)\b"  # type annotation
    r"|[:=]\s*[A-Za-z_$][\w.$]*\s*\("                      # function call
    r"|(YOUR[-_]|CHANGE[-_]?ME|REPLACE[-_]|EXAMPLE|PLACEHOLDER|SEU[-_]|"
    r"xxx+|\.\.\.|<[^>]+>)"                                  # placeholder
)

DENY_RULES = {
    "sensitive_data_field": re.compile(
        r"(?i)health(module|controller|check|indicator|service|z|y)\b|"
        r"['\"/]health['\"/]?|actuator|corsAllow|racecondition|"
        r"politica.{0,3}(de.{0,3})?privacidade|privacy.{0,3}polic"
    ),
    "personal_data_field": re.compile(
        r"(?i)\b(documento|document)\b\s*$|getElementById|document\.(get|query|create)"
    ),
    "hardcoded_secret": NOT_A_SECRET,
}

# Example and template files hold placeholders by design. A realistic-looking value
# there is still worth mentioning -- people copy them verbatim -- but it is a
# different, much milder finding than a credential in a real config file.
EXAMPLE_FILE = re.compile(r"(?i)\.(example|sample|template|dist)$|\.(example|sample|template)\.")


def is_noise_line(line):
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(COMMENT_PREFIXES):
        return True
    return bool(IMPORT_LINE.match(line))


# Signals whose absence is itself worth reporting.
SECRET_SIGNALS = {"hardcoded_secret", "private_key_block", "cloud_credential"}

# A politica de privacidade dizendo "verificamos a idade" nao e verificacao de
# idade; e uma promessa. Ocorrencias vindas do bucket `legal` seguem sendo
# coletadas -- sao a materia-prima da reconciliacao politica x codigo -- mas vem
# marcadas, e a contagem no resumo as separa. Sem essa separacao, uma promessa no
# HTML da politica entra na mesma linha que uma implementacao no controller, e foi
# exatamente assim que o link da ANPD virou "provedor de verificacao de idade".
DECLARATION_BUCKET = "legal"

ABSENCE_MATTERS = {
    "delete_route", "delete_route_alt", "export_route", "update_route",
    "consent_record", "retention_marker", "audit_trail", "password_hash_strong",
    "encryption_at_rest",
    # Ausencia destes e o achado do ECA Digital: coletar idade sem verificar, ou
    # tratar menor sem vinculo com responsavel, e justamente o que a lei veda.
    "age_verification_provider", "parental_link", "content_removal",
    # Ausencia nas resolucoes: sem registro de incidente nao ha como cumprir os
    # cinco anos do art. 10 da Res. 15/2024, e sem canal do encarregado o titular
    # nao tem a quem recorrer.
    "incident_register", "dpo_contact", "dsar_flow", "anonymization",
}

# --------------------------------------------------------------------------
# Stack detection
# --------------------------------------------------------------------------

STACK_MARKERS = [
    ("node-typescript", ["package.json", "tsconfig.json"]),
    ("java-spring", ["pom.xml", "build.gradle", "build.gradle.kts"]),
    ("python", ["requirements.txt", "pyproject.toml", "manage.py"]),
    ("php-laravel", ["composer.json", "artisan"]),
    ("ruby-rails", ["Gemfile", "config/routes.rb"]),
]

FRAMEWORK_HINTS = {
    "node-typescript": {
        "nestjs": "@nestjs/core", "express": "\"express\"", "fastify": "\"fastify\"",
        "prisma": "\"prisma\"", "typeorm": "\"typeorm\"", "sequelize": "\"sequelize\"",
        "mongoose": "\"mongoose\"", "drizzle": "drizzle-orm",
    },
    "java-spring": {
        "spring-boot": "spring-boot", "spring-data-jpa": "spring-boot-starter-data-jpa",
        "hibernate": "hibernate", "flyway": "flyway", "liquibase": "liquibase",
        "spring-security": "spring-boot-starter-security",
    },
}


MANIFEST_DEPTH = 3


def find_manifests(root, max_depth=MANIFEST_DEPTH):
    """Locate build manifests anywhere in the first few directory levels.

    Looking only at the repository root was wrong for the most ordinary layout there
    is: a repository holding `api/` and `client/`, each with its own package.json,
    reported no stack at all -- so the framework notes that make the audit accurate
    were never loaded. Monorepos are the common case, not the exception.
    """
    wanted = {m for _, markers in STACK_MARKERS for m in markers if "/" not in m}
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.replace("\\", "/").count("/") + 1
        if depth >= max_depth:
            dirnames[:] = []
        else:
            dirnames[:] = [d for d in dirnames
                           if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for name in filenames:
            if name in wanted:
                found.setdefault(name, []).append(os.path.join(dirpath, name))
    return found


def detect_stacks(root):
    manifests = find_manifests(root)
    found, frameworks = [], []

    for stack, markers in STACK_MARKERS:
        if any(os.path.basename(m) in manifests for m in markers):
            found.append(stack)

    for stack, markers in STACK_MARKERS:
        if stack not in found:
            continue
        for marker in markers:
            for path in manifests.get(os.path.basename(marker), []):
                content = (read_text(path) or "").lower()
                for name, needle in FRAMEWORK_HINTS.get(stack, {}).items():
                    if needle.lower() in content and name not in frameworks:
                        frameworks.append(name)
    return found, frameworks


# --------------------------------------------------------------------------
# Walking and reading
# --------------------------------------------------------------------------

def read_text(path):
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, ValueError):
        return None


def is_text_file(name):
    ext = os.path.splitext(name)[1].lower()
    if ext in TEXT_EXTS:
        return True
    return name.lower() in {
        "dockerfile", "makefile", "procfile", ".env", ".gitignore", "gemfile",
    } or name.startswith(".env")


def looks_like_test(rel_path):
    parts = {p.lower() for p in rel_path.replace("\\", "/").split("/")}
    if parts & TEST_DIR_HINTS:
        return True
    base = os.path.basename(rel_path).lower()
    return ".spec." in base or ".test." in base or base.startswith("test_")


def classify(rel_path):
    buckets = []
    normalised = rel_path.replace("\\", "/")
    for name, patterns in BUCKET_RULES:
        if any(p.search(normalised) for p in patterns):
            buckets.append(name)
    return buckets


SELF_SKILL = re.compile(r"(?m)^name:\s*lgpd-scan\s*$")


def find_self_roots(root, max_depth=4):
    """Pastas que contem esta propria skill, para nao audita-la junto do projeto.

    `.claude/skills/` ja sai pelo EXCLUDE_DIRS, mas a skill tambem e clonada solta
    dentro do repositorio, e ai o nome da pasta nao ajuda -- um projeto pode ter uma
    pasta `lgpd-scan/` que seja dele. O que identifica a skill e o `SKILL.md` com o
    proprio nome dentro.
    """
    roots = []
    base_depth = root.rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count(os.sep) - base_depth >= max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames
                       if d not in EXCLUDE_DIRS and not d.startswith(".git")]
        if "SKILL.md" not in filenames:
            continue
        try:
            with open(os.path.join(dirpath, "SKILL.md"), encoding="utf-8",
                      errors="replace") as handle:
                head = handle.read(600)
        except OSError:
            continue
        if SELF_SKILL.search(head):
            rel = os.path.relpath(dirpath, root).replace("\\", "/")
            roots.append("" if rel == "." else rel)
            dirnames[:] = []
    return roots


def excluded_path(rel_path):
    if OWN_OUTPUT.search(rel_path):
        return True
    return bool({p for p in rel_path.split("/")} & EXCLUDE_DIRS)


def _git(root, *args, timeout=20):
    """Run a git command in root. Returns stdout bytes, or None on any failure."""
    try:
        done = subprocess.run(
            ["git", "-C", root, *args],
            capture_output=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _git_line(root, *args):
    out = _git(root, *args)
    return out.decode("utf-8", "replace").strip() if out is not None else None


def _git_zlist(root, *args):
    out = _git(root, *args)
    if out is None:
        return None
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def git_context(root):
    """Repository metadata, plus the file list and the set of tracked paths.

    Letting git enumerate the files is worth more than the metadata: it honours
    .gitignore for free, so generated code, build output and vendored dependencies
    stop producing findings nobody can act on. `--cached --others --exclude-standard`
    means tracked files plus new files that are not ignored -- exactly the set the
    developer considers part of the project.

    Knowing which files are tracked also decides the most severe requirement in the
    audit: a password in an ignored .env is an operational note, while the same
    password in a committed docker-compose.yml is an exposure that outlives its
    deletion, because removing the line does not remove it from history.
    """
    info = {
        "is_repo": False, "commit": None, "branch": None,
        "dirty": None, "listing_source": "walk", "listing_note": None,
    }
    if _git_line(root, "rev-parse", "--is-inside-work-tree") != "true":
        return info, None, None

    info["is_repo"] = True
    info["commit"] = _git_line(root, "rev-parse", "--short", "HEAD")
    info["branch"] = _git_line(root, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git_line(root, "status", "--porcelain")
    info["dirty"] = bool(status) if status is not None else None

    candidates = _git_zlist(root, "ls-files", "-z", "--cached", "--others",
                            "--exclude-standard")
    tracked = _git_zlist(root, "ls-files", "-z", "--cached")
    if candidates is None:
        return info, None, None

    # Confiar na listagem do git sem conferir tem um modo de falha silencioso e grave,
    # encontrado rodando a suite de dentro de uma pasta que o repositorio de cima
    # ignorava: o caminho varrido esta dentro de um repositorio git em que ele proprio
    # esta no .gitignore, entao `ls-files --others --exclude-standard` devolve ZERO
    # arquivo. O coletor nao leu nada, nao achou nada, e o relatorio sai limpo -- que e
    # o pior resultado possivel para uma ferramenta de conformidade. Uma pasta
    # instalada em `.claude/skills/`, um subprojeto ignorado, uma pasta de entrega:
    # todos caem nisso.
    usable = _count_listing(root, candidates)
    on_disk = _count_walk(root)

    if usable == 0 and on_disk > 0:
        info["listing_note"] = (
            f"a listagem do git devolveu zero arquivo, mas ha {on_disk} arquivo(s) de "
            f"texto no disco — este caminho provavelmente esta no .gitignore de um "
            f"repositorio acima dele. Voltei a varrer o sistema de arquivos; o "
            f"`tracked` dos achados fica indefinido.")
        return info, None, None

    if on_disk >= usable + 10 and usable * 2 < on_disk:
        info["listing_note"] = (
            f"o git lista {usable} arquivo(s) de texto e ha {on_disk} no disco: o "
            f".gitignore esconde mais da metade da arvore. Pode ser legitimo (dados, "
            f"build) ou pode ser codigo fora da auditoria — vale conferir antes de "
            f"tratar sinal ausente como lacuna.")

    info["listing_source"] = "git"
    return info, candidates, set(tracked or [])


def _count_listing(root, candidates):
    """Quantos dos caminhos listados pelo git o coletor de fato leria."""
    total = 0
    for rel_path in candidates:
        rel_path = rel_path.replace("\\", "/")
        if excluded_path(rel_path) or not is_text_file(os.path.basename(rel_path)):
            continue
        if os.path.isfile(os.path.join(root, *rel_path.split("/"))):
            total += 1
    return total


def _count_walk(root):
    """Quantos arquivos de texto existem no disco, pelos mesmos filtros da varredura.

    So conta, nao le -- e barato o suficiente para rodar sempre, e e o numero que
    torna a listagem do git conferivel em vez de confiavel por fe.
    """
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in EXCLUDE_DIRS and not d.startswith(".git")]
        for name in filenames:
            rel_path = os.path.relpath(
                os.path.join(dirpath, name), root).replace("\\", "/")
            if excluded_path(rel_path) or not is_text_file(name):
                continue
            total += 1
    return total


def iter_files(root, include_tests, git_files=None):
    if git_files is not None:
        for rel_path in sorted(git_files):
            rel_path = rel_path.replace("\\", "/")
            if excluded_path(rel_path):
                continue
            if not is_text_file(os.path.basename(rel_path)):
                continue
            if not include_tests and looks_like_test(rel_path):
                continue
            abs_path = os.path.join(root, *rel_path.split("/"))
            if os.path.isfile(abs_path):
                yield rel_path, abs_path
        return

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".git")]
        for name in filenames:
            abs_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(abs_path, root).replace("\\", "/")
            if excluded_path(rel_path):
                continue
            if not is_text_file(name):
                continue
            if not include_tests and looks_like_test(rel_path):
                continue
            yield rel_path, abs_path


# --------------------------------------------------------------------------
# Main scan
# --------------------------------------------------------------------------

def scan(root, include_tests=False, max_hits=40):
    stacks, frameworks = detect_stacks(root)
    git_info, git_files, tracked_set = git_context(root)
    # Varrer a propria skill instalada dentro do projeto produz achados que citam a
    # documentacao da ferramenta. Sao excluidas a menos que a raiz varrida SEJA a
    # skill -- auditar o proprio repositorio dela e legitimo, e e o que o dogfood faz.
    self_roots = [r for r in find_self_roots(root) if r]

    signals = {name: [] for name, _, _ in SIGNAL_RULES}
    suppressed, suppression_rejected, declared = [], [], []
    truncated = set()
    buckets = {name: [] for name, _ in BUCKET_RULES}
    scanned = skipped = 0

    for rel_path, abs_path in iter_files(root, include_tests, git_files):
        if any(rel_path == r or rel_path.startswith(r + "/") for r in self_roots):
            skipped += 1
            continue
        content = read_text(abs_path)
        if content is None:
            skipped += 1
            continue
        scanned += 1

        is_code = os.path.splitext(rel_path)[1].lower() in CODE_EXTS
        is_example = bool(EXAMPLE_FILE.search(rel_path))
        # So o cabecalho: um documento que CITA o marcador no meio do texto (esta
        # propria skill, por exemplo) nao e um documento gerado.
        is_generated = bool(GENERATED_MARKER.search(content[:400]))
        tracked = None if tracked_set is None else (rel_path in tracked_set)
        file_buckets = classify(rel_path)
        for bucket in file_buckets:
            if len(buckets[bucket]) < 400:
                buckets[bucket].append(rel_path)

        lines = content.splitlines()
        total = len(lines)

        # Supressoes validas do arquivo, indexadas pela linha que elas cobrem: a
        # propria e a de baixo. Um marcador sem motivo entra em `rejected` em vez
        # de silenciar coisa alguma.
        file_suppressions = {}
        for idx, raw in enumerate(lines, start=1):
            marker = SUPPRESSION_MARKER.search(raw)
            if not marker:
                continue
            signal = marker.group("signal").lower()
            reason_match = SUPPRESSION_REASON.match(marker.group("rest"))
            reason = reason_match.group("reason").strip() if reason_match else ""

            if len(reason) < 4:
                suppression_rejected.append({
                    "file": rel_path, "line": idx, "signal": signal,
                    "why": "sem motivo: escreva `lgpd-scan: ignore "
                           f"{signal} — por que este achado esta errado`",
                    "snippet": raw.strip()[:SNIPPET_MAX],
                })
                continue
            if signal != "*" and signal not in signals:
                suppression_rejected.append({
                    "file": rel_path, "line": idx, "signal": signal,
                    "why": "nome de sinal desconhecido; confira a lista em "
                           "references/annotations.md",
                    "snippet": raw.strip()[:SNIPPET_MAX],
                })
                continue

            entry = {"signal": signal, "reason": reason, "declared_at": idx}
            for covered in (idx, idx + 1):
                file_suppressions.setdefault(covered, []).append(entry)

        for idx, raw in enumerate(lines, start=1):
            for match in ANNOTATION.finditer(raw):
                declared.append({
                    "file": rel_path, "line": idx,
                    "kind": match.group("kind").lower(),
                    "value": match.group("value"),
                    "snippet": raw.strip()[:SNIPPET_MAX],
                })
        for name, pattern, wanted_buckets in SIGNAL_RULES:
            if wanted_buckets and not (wanted_buckets & set(file_buckets)):
                continue
            if name in CODE_ONLY_SIGNALS and not is_code:
                continue
            if name in MANIFEST_OR_CODE_SIGNALS and not (
                    is_code or (MANIFEST_BUCKETS & set(file_buckets))):
                continue
            hits = signals[name]
            in_this_file = 0
            cap = max_hits * 3 if name in HIGH_VOLUME_SIGNALS else max_hits
            windowed = name in WINDOW_SIGNALS
            skip_noise = name in NOISE_SKIP_SIGNALS
            deny = DENY_RULES.get(name)
            normalise = name in IDENTIFIER_SIGNALS
            last_hit_line = None

            for idx, line in enumerate(lines, start=1):
                if len(line) > 2000:
                    line = line[:2000]
                if skip_noise and is_noise_line(line):
                    continue

                if windowed:
                    chunk = " ".join(
                        raw.strip() for raw in lines[idx - 1: idx - 1 + WINDOW_LINES]
                    )[:2000]
                else:
                    chunk = line

                haystack = deaccent(chunk)
                if normalise:
                    haystack = normalise_identifiers(haystack)
                if not pattern.search(haystack):
                    continue
                if deny and deny.search(chunk):
                    continue
                if windowed and last_hit_line is not None and \
                        idx - last_hit_line < WINDOW_LINES:
                    continue
                if in_this_file >= MAX_HITS_PER_FILE:
                    break  # this file's share is spent; other files still get theirs
                if len(hits) >= cap:
                    truncated.add(name)
                    break

                applicable = [sup for sup in file_suppressions.get(idx, [])
                              if sup["signal"] in (name, "*")]
                if applicable:
                    suppressed.append({
                        "file": rel_path, "line": idx, "signal": name,
                        "reason": applicable[0]["reason"],
                        "declared_at": applicable[0]["declared_at"],
                        "snippet": line.strip()[:SNIPPET_MAX],
                    })
                    continue

                last_hit_line = idx
                in_this_file += 1
                hit = {
                    "file": rel_path,
                    "line": idx,
                    "snippet": (chunk if windowed else line).strip()[:SNIPPET_MAX],
                    "buckets": file_buckets,
                    "tracked": tracked,
                }
                if is_example:
                    hit["example_file"] = True
                if is_generated:
                    hit["generated_by_tool"] = True
                if DECLARATION_BUCKET in file_buckets:
                    hit["declaration_only"] = True
                hits.append(hit)

    absent = sorted(n for n in ABSENCE_MATTERS if not signals.get(n))

    return {
        "schema_version": 2,
        "tool": "lgpd-scan collector",
        "tool_version": TOOL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": os.path.abspath(root),
        "git": git_info,
        "stacks_detected": stacks,
        "frameworks_detected": frameworks,
        "counts": {
            "files_scanned": scanned,
            "files_skipped": skipped,
            "tests_included": include_tests,
        },
        "buckets": {k: v for k, v in buckets.items() if v},
        "signals": {k: v for k, v in signals.items() if v},
        "truncated_signals": sorted(truncated),
        "absent_signals": absent,
        "suppressed": suppressed,
        "suppression_rejected": suppression_rejected,
        "declared": declared,
        "disclaimer": (
            "Cada item aqui e uma hipotese produzida por expressao regular, nao um "
            "achado. Abra o arquivo antes de concluir qualquer coisa. O campo "
            "'tracked' diz se o arquivo esta versionado no git (null = sem git)."
        ),
    }


def print_summary(result):
    out = sys.stdout.write
    counts = result["counts"]
    git = result.get("git", {})
    out("\n=== lgpd-scan: candidatos coletados ===\n")
    out(f"raiz              {result['root']}\n")
    out(f"arquivos lidos    {counts['files_scanned']} "
        f"({counts['files_skipped']} ignorados)\n")
    if git.get("is_repo"):
        dirty = " (com alteracoes nao commitadas)" if git.get("dirty") else ""
        out(f"git               {git.get('commit') or '?'} em "
            f"{git.get('branch') or '?'}{dirty}\n")
        out("listagem          git (respeita .gitignore)\n"
            if git.get("listing_source") == "git" else
            "listagem          varredura de diretorio\n")
    else:
        out("git               nao e um repositorio "
            "(sem status de versionamento nos achados)\n")
    if git.get("listing_note"):
        out(f"\n!! ATENCAO NA LISTAGEM: {git['listing_note']}\n")
    out(f"stacks            {', '.join(result['stacks_detected']) or 'nao identificada'}\n")
    if result["frameworks_detected"]:
        out(f"frameworks        {', '.join(result['frameworks_detected'])}\n")

    out("\n-- sinais encontrados (arquivo:linha no JSON) --\n")
    if not result["signals"]:
        out("  nenhum\n")
    for name in sorted(result["signals"], key=lambda n: -len(result["signals"][n])):
        hits = result["signals"][name]
        mark = " (truncado)" if name in result["truncated_signals"] else ""
        files = sorted({h["file"] for h in hits})
        sample = files[0] if files else ""
        extra = f" +{len(files) - 1} arquivos" if len(files) > 1 else ""
        versioned = sum(1 for h in hits if h.get("tracked") is True)
        declarative = sum(1 for h in hits if h.get("declaration_only"))
        flag = ""
        if name in SECRET_SIGNALS and versioned:
            flag = f"  [{versioned} VERSIONADO(S)]"
        if declarative:
            flag += f"  ({declarative} em texto legal, nao implementacao)"
        examples = sum(1 for h in hits if h.get("example_file"))
        if examples:
            flag += f"  ({examples} em arquivo de exemplo)"
        out(f"  {name:<24} {len(hits):>4}{mark}   {sample}{extra}{flag}\n")

    if result["absent_signals"]:
        out("\n-- NENHUM sinal para (confirme antes de tratar como lacuna) --\n")
        for name in result["absent_signals"]:
            out(f"  {name}\n")

    if result.get("suppressed"):
        out(f"\n-- suprimido por anotacao no codigo ({len(result['suppressed'])}) --\n")
        for item in result["suppressed"][:10]:
            out(f"  {item['signal']:<24} {item['file']}:{item['line']}\n"
                f"  {'':<24} motivo: {item['reason'][:70]}\n")
        if len(result["suppressed"]) > 10:
            out(f"  ... e mais {len(result['suppressed']) - 10}\n")

    if result.get("suppression_rejected"):
        out(f"\n-- supressao NAO aplicada ({len(result['suppression_rejected'])}) --\n")
        for item in result["suppression_rejected"]:
            out(f"  {item['file']}:{item['line']}  {item['signal']}: {item['why']}\n")

    if result.get("declared"):
        kinds = {}
        for item in result["declared"]:
            kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
        out(f"\n-- anotacoes @lgpd: no codigo ({len(result['declared'])}) --\n")
        for kind, count in sorted(kinds.items()):
            out(f"  {kind:<24} {count}\n")

    out("\n-- arquivos por categoria --\n")
    for bucket, files in result["buckets"].items():
        out(f"  {bucket:<12} {len(files):>4}\n")
    out("\n")


STATUS_TEMPLATE = """# Estado da auditoria LGPD

| | |
|---|---|
| **Coletor** | lgpd-scan {version} |
| **Ultima varredura** | {when} |
| **Commit** | {commit} |
| **Arquivos lidos** | {files} |
| **Stacks** | {stacks} |
{listing_note}
## Sinais com ocorrencia

{present}

## Sinais ausentes (confirmar antes de tratar como lacuna)

{absent}

## Anotacoes no codigo

| | |
|---|---|
| Supressoes honradas | {suppressed} |
| Supressoes rejeitadas | {rejected} |
| Declaracoes `@lgpd:` | {declared} |

## Checkpoints

<!-- O agente marca aqui o que ja julgou. Uma auditoria de 21 requisitos nao cabe
     numa sessao; sem este registro, a segunda sessao recomeca do zero e o relatorio
     final vira colagem de dois julgamentos diferentes. -->

- [ ] R01 a R12 — base da Lei 13.709
- [ ] R13 a R17 — resolucoes da ANPD
- [ ] R18 a R21 — ECA Digital
- [ ] Reconciliacao politica x codigo
- [ ] Relatorio escrito
- [ ] Verificador rodado e limpo
"""


def write_status(root, result, path=None):
    """Grava o estado da varredura para a proxima sessao encontrar.

    Vinte e um requisitos nao caem numa sessao so. Sem estado, a auditoria ou
    recomeca inteira -- caro e inconsistente -- ou o agente inventa continuidade
    que nao tem. O arquivo tambem faz a segunda execucao render um diff legivel
    quando o projeto versiona a pasta.
    """
    present = "\n".join(
        f"- `{name}` — {len(hits)} ocorrencia(s)"
        + (f", {sum(1 for h in hits if h.get('declaration_only'))} em texto legal"
           if any(h.get("declaration_only") for h in hits) else "")
        for name, hits in sorted(result["signals"].items(), key=lambda kv: -len(kv[1]))
    ) or "- nenhum"
    absent = "\n".join(f"- `{name}`" for name in result["absent_signals"]) or "- nenhum"

    text = STATUS_TEMPLATE.format(
        version=result.get("tool_version", "?"),
        when=result["generated_at"],
        commit=(result.get("git") or {}).get("commit") or "sem git",
        files=result["counts"]["files_scanned"],
        stacks=", ".join(result["stacks_detected"]) or "nao identificada",
        listing_note=(
            f"\n> **Atencao na listagem.** {(result.get('git') or {})['listing_note']}\n"
            if (result.get("git") or {}).get("listing_note") else ""),
        present=present,
        absent=absent,
        suppressed=len(result.get("suppressed", [])),
        rejected=len(result.get("suppression_rejected", [])),
        declared=len(result.get("declared", [])),
    )
    target = path or os.path.join(root, ".lgpd-scan", "STATUS.md")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(text)
    return target


def main():
    parser = argparse.ArgumentParser(
        description="Collect LGPD audit candidates from a repository."
    )
    parser.add_argument("repo", nargs="?", default=".", help="repository root")
    parser.add_argument("--out", default=None, help="JSON output path")
    parser.add_argument("--max-hits", type=int, default=40,
                        help="max hits kept per signal (default 40)")
    parser.add_argument("--include-tests", action="store_true",
                        help="also scan test files")
    parser.add_argument("--quiet", action="store_true",
                        help="write JSON only, no summary")
    parser.add_argument("--no-status", action="store_true",
                        help="do not write .lgpd-scan/STATUS.md")
    args = parser.parse_args()

    root = os.path.abspath(args.repo)
    if not os.path.isdir(root):
        sys.stderr.write(f"error: {root} is not a directory\n")
        return 2

    result = scan(root, include_tests=args.include_tests, max_hits=args.max_hits)

    out_path = args.out or os.path.join(root, ".lgpd-scan", "candidates.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)

    status_path = None
    if not args.no_status:
        status_path = write_status(root, result)

    if not args.quiet:
        print_summary(result)
        sys.stdout.write(f"JSON completo: {out_path}\n")
        if status_path:
            sys.stdout.write(f"Estado:        {status_path}\n")
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
