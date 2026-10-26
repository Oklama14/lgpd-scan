# Bridge to the LGPD-Check

The LGPD-Check is the inspection checklist of Mendes, Viana and Rivero (SBES 2021),
evaluated by Neitzke et al. (SBQS 2023), with 61 items in its consolidated version.
It is the checklist the DevComply asks a team to fill in. This file maps the 21
requirements of this skill onto it, so that a report from one tool can be read
against a report from the other.

The mapping is this skill's, not the papers': the LGPD-Check has no R01–R21. Read it
when the user brings DevComply declarations (the **Conciliação** scenario in
`SKILL.md`), when they ask how a finding relates to a checklist item, or when the
DevComply export is requested. `scripts/report_data.py` holds the same table as data
(`LGPD_CHECK`), and the test suite fails if the two drift apart.

Two kinds of relation:

- **Direta** — the requirement answers the same question as the item, so the
  requirement's status is the item's status in the code. When several requirements
  answer one item, the worst status wins.
- **Parcial** — the requirement touches the item but does not settle it alone. Report
  it as context, never as the item's status.

## Requirement → LGPD-Check

| # | Requisito | Direta | Parcial |
|---|---|---|---|
| R01 | Inventário de dados pessoais | S-07 | T-11 |
| R02 | Dados sensíveis identificados como tais | S-05 | T-02 |
| R03 | Direito de eliminação | D-07 | — |
| R04 | Direito de acesso e portabilidade | D-03, D-06, T-06 | D-01 |
| R05 | Direito de correção | D-04 | T-08 |
| R06 | Registro de consentimento | C-03 | C-01, C-04 |
| R07 | Retenção e expurgo | D-08 | — |
| R08 | Segurança do armazenamento de credenciais | S-17 | S-01, S-08 |
| R09 | Segredos fora do repositório | — | S-01, S-08 |
| R10 | Minimização de dados em logs | — | D-05, S-10 |
| R11 | Registro das operações de tratamento | T-11 | S-07, S-10 |
| R12 | Compartilhamento com terceiros | D-09 | C-02, S-03 |
| R13 | Registro de incidente de segurança | — | S-11, R-03 |
| R14 | Comunicação de incidente no prazo | R-03 | — |
| R15 | Encarregado indicado e canal do titular | R-01, R-02 | D-02 |
| R16 | Salvaguarda de transferência internacional | S-02 | S-03 |
| R17 | Anonimização e pseudonimização | T-13 | — |
| R18 | Verificação de idade sem autodeclaração | — | — |
| R19 | Vinculação a responsável legal | — | C-05 |
| R20 | Configuração padrão mais protetiva | — | S-06 |
| R21 | Perfilamento publicitário para menores | — | — |

R18 and R21 have no counterpart: the LGPD-Check predates the ECA Digital
(Lei 15.211/2025). A project assessed only with the checklist was never asked these
questions — say so when it matters.

## Items only the organisation can prove

These leave no trace in a repository. The DevComply checklist asks them; this skill
lists them under "Não verificável" and never infers them from code.

Só a organização: T-01, T-10, T-12, R-04, R-05, R-06, R-07, S-12, S-14, S-15

| Item | What it asks |
|---|---|
| T-01 | Finalidades do tratamento definidas pela organização |
| T-10 | Legítimo interesse avaliado conforme a lei |
| T-12 | Titular e autoridades informados sobre operações baseadas em legítimo interesse |
| R-04 | Avaliação de impacto quando o tratamento é de alto risco |
| R-05 | RIPD elaborado e fornecido à ANPD quando solicitado |
| R-06 | Atividades do encarregado registradas |
| R-07 | Colaboradores capacitados em LGPD |
| S-12 | Certificações ou selos de proteção de dados |
| S-14 | Processo formal de registro e cancelamento de usuários dos sistemas |
| S-15 | Processo formal para conceder e revogar acesso |

A RIPD this skill generates (`references/artifacts/ripd.md`) is a draft levantado do
código, not the assessment R-04 and R-05 ask for. Say that when you point to it.

## Items the code could answer, not yet covered

These do leave a trace, but no requirement here decides them yet — candidates for
future requirements. The policy × code reconciliation already touches the first four.

Fora da skill: T-03, T-04, T-05, T-07, T-09, T-14, C-06, C-07, C-08, D-10, D-11, D-12, D-13, D-14, D-15, S-04, S-09, S-13, S-16

| Item | What it asks |
|---|---|
| T-03 | Finalidades informadas ao titular |
| T-05 | Forma e duração do tratamento informadas |
| T-09 | Informações sobre o tratamento e identificação do controlador |
| T-14 | Titular informado antes da coleta |
| T-04 | Tratamento de acordo com a finalidade apresentada |
| T-07 | Dados armazenados com exatidão e clareza |
| C-06 | Titular avisado de mudança de finalidade, com opção de revogar |
| C-07 | Declaração de consentimento compreensível e sem termos abusivos |
| C-08 | Direitos informados na declaração de consentimento |
| D-10 | Titular informado de que pode negar o consentimento, e das consequências |
| D-11 | Titular informado quando o tratamento é condição do serviço |
| D-12 | Oposição ao tratamento de forma fácil |
| D-13 | Motivo informado quando um direito não pode ser atendido de imediato |
| D-14 | Titular informado de decisões automatizadas e perfilamento |
| D-15 | Revisão de decisões automatizadas |
| S-04 | Mecanismos contra dano, destruição ou perda (backup) |
| S-09 | Integridade dos dados, contra alteração indevida |
| S-13 | Cadastro, cancelamento e provisionamento de acesso |
| S-16 | Registro atualizado dos usuários autorizados |

## Severity

The scales measure the same thing — how much a gap exposes the data subject — with
different names. Use this correspondence when a report is read next to the DevComply:

| lgpd-scan | DevComply | Example |
|---|---|---|
| Alta | Catastrófica | no path at all for the subject to exercise a right; sensitive data unprotected |
| Média | Grave | a right served only manually or partly; no record of processing operations |
| Baixa | Leve | a documentation or form defect with no direct harm to the subject |

## Declaration is not evidence

A DevComply declaration — "marquei C-03 como implementado" — is what the team says.
It goes through the same rule as a privacy policy: a lead on where to look, and the
material for the **Declarado × código** section, never evidence that something is
built. A declared item whose direct requirement the code shows as `Parcial` or
`Não atendido` is the most useful single finding this comparison produces, and
`verify_report.py` refuses a report that leaves one out.
