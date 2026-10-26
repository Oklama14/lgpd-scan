# Requirements index

Twenty-one requirements, each verifiable in source code, grouped by the instrument
that creates them. Load only the group you are working through — the whole set does
not fit usefully in one context, which is why this index exists instead of a single
file.

| Group | File | Requirements |
|---|---|---|
| Lei 13.709/2018, base | `base-lgpd.md` | R01–R12 |
| Resoluções da ANPD | `anpd-resolucoes.md` | R13–R17 |
| ECA Digital, Lei 15.211/2025 | `eca-digital.md` | R18–R21 |

## The whole list, for the report's summary table

| # | Requisito | Base legal | Grupo |
|---|---|---|---|
| R01 | Inventário de dados pessoais | Art. 5º, I | base |
| R02 | Dados sensíveis identificados como tais | Art. 11 | base |
| R03 | Direito de eliminação | Art. 18, VI | base |
| R04 | Direito de acesso e portabilidade | Art. 18, II e V | base |
| R05 | Direito de correção | Art. 18, III | base |
| R06 | Registro de consentimento | Art. 8º, §1º | base |
| R07 | Retenção e expurgo | Art. 15 e 16 | base |
| R08 | Segurança do armazenamento de credenciais | Art. 46 | base |
| R09 | Segredos fora do repositório | Art. 46 | base |
| R10 | Minimização de dados em logs | Art. 6º, III | base |
| R11 | Registro das operações de tratamento | Art. 37 | base |
| R12 | Compartilhamento com terceiros | Art. 33 | base |
| R13 | Registro de incidente de segurança | Res. CD/ANPD 15/2024, art. 10 | anpd |
| R14 | Comunicação de incidente no prazo | Res. CD/ANPD 15/2024, art. 6º e 9º | anpd |
| R15 | Encarregado indicado e canal do titular | Res. CD/ANPD 18/2024 | anpd |
| R16 | Salvaguarda de transferência internacional | Res. CD/ANPD 19/2024 | anpd |
| R17 | Anonimização e pseudonimização | Art. 12 | anpd |
| R18 | Verificação de idade sem autodeclaração | Lei 15.211/2025 | eca |
| R19 | Vinculação a responsável legal | Lei 15.211/2025 | eca |
| R20 | Configuração padrão mais protetiva | Lei 15.211/2025 | eca |
| R21 | Perfilamento publicitário para menores | Lei 15.211/2025 | eca |

## Which groups apply

R01–R12 apply to every project that handles personal data. R13–R17 apply to every
controller, but their code trace varies: a project with no incident-response
tooling at all produces R13 and R14 as gaps, which is a true finding.

R18–R21 apply only where minors are plausibly among the data subjects — a social
network, a game, an education product, any service that does not exclude them. On a
B2B internal tool they are `Não se aplica`, and saying so explicitly is better than
silence: the reader needs to know the question was asked. Do not decide this from
the code alone; if there is no age signal anywhere and nothing suggests a consumer
product, say the scope was judged inapplicable and why.

## Status and severity vocabulary

| Status | Meaning |
|---|---|
| `Atendido` | Evidence in the code shows the requirement is met |
| `Parcial` | Partly implemented, or implemented with a defect |
| `Não atendido` | Searched and found nothing, or found something that fails |
| `Não verificável` | Cannot be determined from code alone |
| `Não se aplica` | The requirement does not reach this kind of product |

Severity applies to gaps only: `Alta`, `Média`, `Baixa`, weighed by exposure of data
subjects rather than by effort to fix. Confidence is a different question — how sure
you are, not how bad it is — and every finding carries both.

| Severity | Criterion | Examples |
|---|---|---|
| `Alta` | Directly breaches the law, exposes sensitive data, or stops the subject from exercising a right | sensitive data (health, biometrics) or children's data unprotected; no path at all to exercise a right; age by self-declaration only; a credential in a tracked file; passwords hashed with MD5 or SHA-1 |
| `Média` | Compromises a right of the subject or puts data at risk | a right served only by a manual, slow request; no record of processing operations; no incident register; the DPO channel left as a template placeholder |
| `Baixa` | A defect of form or documentation, with no direct harm to the subject | a policy with no update date; a working process nobody documented; a consent record without the version of the text accepted |

Where a requirement's own section fixes the severity, that wins; the table calibrates
the rest. Torn between two levels: pick the higher one when sensitive data or
children are involved, the lower one otherwise.

The criteria and the tie-break are the DevComply's (its `criterios.ts`), with
examples swapped for what code can show, so the two tools grade the same gap the
same way. The DevComply calls the levels `Catastrófica`, `Grave` and `Leve`, one to
one, as `lgpd-check.md` records. One example did not carry over: the DevComply calls
"no procedure to notify an incident" catastrophic, but here that is R14, and nothing
in a repository proves the procedure is missing — a controller can meet the deadline
by hand. Grade R14 as the process gap it is.

## Bridge to the LGPD-Check

`lgpd-check.md` maps R01–R21 onto the 61 items of the LGPD-Check, the checklist the
DevComply uses: which item each requirement decides, which it only touches, and which
items only the organisation can prove. Read it when the user brings DevComply
declarations or asks for the DevComply export — not on an ordinary audit.

## Declaration versus implementation

Every hit the collector produces carries `declaration_only: true` when it came from
a file in the `legal` bucket — a privacy policy, terms of use, a cookie page.

This distinction is the spine of the whole audit. A policy that says "verificamos a
idade dos titulares" is a promise; an age-verification integration in the signup
flow is an implementation. Crediting the first as if it were the second is the
single easiest way for this tool to produce a dangerously wrong report.

Use declaration hits for two things only: the policy × code reconciliation section,
and as leads on where to look in the code. Never as evidence that something is
built.
