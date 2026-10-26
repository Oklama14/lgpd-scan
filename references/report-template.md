# Report template

Write the report to `RELATORIO-LGPD.md` at the repository root, in Brazilian
Portuguese, following the structure below.

Two notes on tone before the structure. Write for a developer who has twenty minutes,
not for a lawyer: short sentences, the concrete file, the concrete fix. And keep the
promise the report makes on its first page — every affirmation carries evidence, so
if you cannot cite a line, the claim belongs under "não verificável" instead of the
findings.

---

## Structure

````markdown
# Relatório de Conformidade LGPD — {nome do projeto}

| | |
|---|---|
| **Repositório** | `{caminho ou URL}` |
| **Commit** | `{git.commit do candidates.json, ou "sem git"}` |
| **Data** | {DD/MM/AAAA} |
| **Escopo** | {N} arquivos, stacks: {stacks detectadas} |
| **Ferramenta** | lgpd-scan {tool_version} · análise assistida por IA, revisão humana obrigatória |
| **Modelo** | {nome e versão do modelo que escreveu este relatório} |

## Resumo

{Dois ou três parágrafos. O que o sistema trata de dado pessoal, qual é o
problema mais grave encontrado, e o que exige atenção imediata. Sem lista aqui —
prosa, para quem vai ler só isso.}

### Situação por requisito

| # | Requisito | Art. | Status | Severidade |
|---|---|---|---|---|
| R01 | Inventário de dados pessoais | 5º, I | Atendido | — |
| R02 | Dados sensíveis | 11 | Não atendido | Alta |
| ... | | | | |

## Comece por aqui

{Três ações, na ordem em que devem ser feitas. Ordene por severidade — Alta antes de
Média, Média antes de Baixa; no empate, a de confiança maior primeiro e depois a mais
barata de corrigir. É a mesma ordem do plano de ação do DevComply, para que as duas
listas possam ser lidas lado a lado. Uma linha por ação: requisito, severidade,
arquivo e o que fazer. Com menos de três lacunas, liste as que existem; sem nenhuma,
diga isso aqui.}

1. **R09 · Alta** — Rotacionar a senha do banco que está em `docker-compose.yml:14`
   e só depois movê-la para variável de ambiente: apagar a linha não a tira do
   histórico do git.
2. **R03 · Alta** — Criar `DELETE /users/me` em
   `src/users/users.controller.ts`, derivando o id do token.
3. **R11 · Média** — Registrar as operações de tratamento: hoje nenhum serviço grava
   quem acessou ou alterou dado pessoal.

## Dados pessoais encontrados

| Tabela / entidade | Campo | Natureza | Onde |
|---|---|---|---|
| `usuarios` | `email` | Dado pessoal | `src/users/user.entity.ts:20` |
| `pacientes` | `cid` | **Dado sensível** (saúde) | `db/migration/V3__pac.sql:14` |

{Se não houver dado pessoal algum, diga isso e explique como chegou a essa
conclusão — é uma afirmação forte.}

## Achados

{Uma subseção por requisito, na ordem R01 a R12. Requisitos atendidos entram
também, em uma linha — o leitor precisa saber o que foi verificado e passou.}

### R03 — Direito de eliminação · Não atendido · Severidade alta

**O que a lei pede.** {Uma frase, sem jargão.}

**O que o código mostra.** Existe `DELETE /projects/:id` em
`src/projects/projects.controller.ts:49`, mas nenhuma rota permite que o próprio
titular exclua a conta. A busca por `excluir|deletar|remover` combinado com
`conta|cadastro|usuario` não retornou nada no repositório.

**Evidência.** Cada linha traz o caminho, a linha e o **trecho literal** dela:
- `src/projects/projects.controller.ts:49` — `@Delete(':id')` — exclusão de
  projeto, não de conta
- `src/users/users.controller.ts:20` — `export class UsersController` — nenhuma
  rota de exclusão de conta na classe inteira

**O que fazer.** Adicionar `DELETE /users/me`, derivando o id do token, que remova
o registro e as linhas dependentes. Se a exclusão precisar ser lógica por
obrigação legal, documentar a base e definir o prazo do apagamento definitivo.

**Confiança:** Alta.

## Declarado × código

{Só quando houver declarações do DevComply — o resultado de
`scripts/devcomply.py conciliar`. Uma linha por divergência: item que a equipe marcou
como implementado e cujo requisito o código mostra como `Parcial` ou `Não atendido`.
O verificador recusa o relatório que deixa uma de fora. Depois da tabela, uma frase
sobre o que se confirmou e o que está implementado sem ter sido declarado. Sem
declarações, omita a seção.}

| Item LGPD-Check | Declarado | O código mostra | Requisito | Onde |
|---|---|---|---|---|
| C-03 | Implementado | Não atendido · Alta | R06 | nenhuma coluna de aceite em `src/users/user.entity.ts:12` — `export class User` |
| D-03 | Implementado | Parcial · Média | R04 | `src/users/users.service.ts:88` — `exportar(` — a exportação deixa o consentimento de fora |

## Não verificável a partir do código

{O que você suspeitou mas não conseguiu confirmar, e por quê. Esta seção é o que
separa um relatório honesto de um relatório inflado — use. Uma linha por assunto, com
a pergunta que resolveria; o mesmo conteúdo vai em `unverifiable` no report.json, e é
de lá que o DevComply tira as perguntas para a equipe.}

| Assunto | Por que o código não responde | Pergunta para a equipe | LGPD-Check |
|---|---|---|---|
| Contrato com operadores | O código envia dados à API do Gemini (`src/ai/ai.service.ts:41`); se há contrato com o Google não aparece no repositório | Existe contrato ou termo de tratamento com o Google para a API? | D-09, C-02 |
| Treinamento da equipe | Não deixa rastro em código | A equipe recebeu capacitação em LGPD? | R-07 |

## Limitações desta análise

Esta análise lê o código-fonte. Ela mostra **o que está implementado**, não o que
é praticado. Ficam fora do alcance, e continuam sendo exigências da LGPD:

- contrato com operadores e suboperadores
- encarregado (DPO) designado e canal de atendimento ao titular
- treinamento das equipes e políticas internas
- segurança física e controles organizacionais
- relatório de impacto (RIPD) e registro das bases legais escolhidas
- o que acontece com os dados fora deste repositório

Nenhum resultado aqui constitui atestado de conformidade nem parecer jurídico.
O relatório serve como evidência técnica para revisão humana — idealmente do
encarregado ou da assessoria jurídica responsável.

{Se algum requisito não pôde ser avaliado por limitação da ferramenta — stack
não reconhecida, código gerado, binário — diga aqui.}
````

---

## O registro de máquina: `.lgpd-scan/report.json`

Escreva **os dois**. O markdown é o documento que as pessoas leem; o JSON é o mesmo
conteúdo em formato de dado, e é o que torna derivável tudo o que antes exigiria
reescrever — o diff com a auditoria anterior, o portão de CI, a saída SARIF.

Ele é **escrito, não extraído**. Um parser do markdown seria mais simples e é
exatamente o que a primeira versão do verificador fazia com os cabeçalhos: frágil,
porque prosa muda. Aqui você escreve os dois e o verificador confere que concordam —
divergência entre eles é erro, porque são dois registros da mesma auditoria e, se
discordam, não dá para saber qual está certo.

```json
{
  "schema": "lgpd-scan/report/1",
  "tool_version": "{tool_version}",
  "generated_at": "{ISO-8601}",
  "model": "{nome e versão do modelo}",
  "repo": {"root": "{caminho}", "commit": "{git.commit ou null}",
           "files_scanned": {N}, "stacks": ["node-typescript"]},
  "scope": {
    "groups": {"base": "avaliado", "anpd": "avaliado", "eca": "nao_se_aplica"},
    "eca_reason": "ferramenta interna B2B, sem menor entre os titulares"
  },
  "requirements": [
    {
      "id": "R03",
      "status": "Nao atendido",
      "severity": "Alta",
      "confidence": "Alta",
      "evidence": [
        {"file": "src/projects/projects.controller.ts", "line": 49,
         "snippet": "@Delete(':id')"}
      ],
      "note": "Exclui projeto, não a conta do titular."
    },
    {
      "id": "R06",
      "status": "Nao atendido",
      "severity": "Alta",
      "confidence": "Alta",
      "absence": "Nenhuma coluna de aceite, versão de política ou data de consentimento na entidade nem no DTO."
    }
  ],
  "personal_data": [
    {"entity": "usuarios", "field": "email", "nature": "pessoal",
     "file": "src/users/user.entity.ts", "line": 20}
  ],
  "third_parties": [
    {"name": "Google (Gemini API)", "data": "conteúdo submetido pelo titular",
     "country": "EUA", "file": "src/ai/ai.service.ts", "line": 41}
  ],
  "unverifiable": [
    {"topic": "Contrato com operadores", "requirement": "R12",
     "reason": "O código envia dados à API do Gemini; contrato com o Google não aparece no repositório.",
     "question": "Existe contrato ou termo de tratamento com o Google para a API?",
     "lgpd_check": ["D-09", "C-02"]}
  ]
}
```

Seis regras que o validador aplica, e o motivo de cada uma:

**Os 21 requisitos aparecem, sempre.** Omitir um é diferente de respondê-lo com
`Nao se aplica`: o primeiro deixa o leitor sem saber se a pergunta foi feita. Grupo
inteiro fora de escopo entra como 21 entradas, quatro delas `Nao se aplica` com a
razão.

**`evidence` ou `absence`, nunca nenhum dos dois.** Uma lacuna se sustenta apontando
o código que falha, ou dizendo o que foi procurado e não existe. Exigir citação das
duas empurraria para o pior resultado possível — citar uma linha qualquer só para
satisfazer o verificador.

**Toda evidência carrega `snippet`.** O JSON não pode ter padrão de prova mais baixo
que o documento que as pessoas leem, e ele passa pela mesma conferência: arquivo
existe, linha dentro dele, trecho aparece por ali.

**`Parcial` e `Nao atendido` exigem `severity`.** Sem ela não existe índice de
pendência, e sem índice não existe tendência entre duas execuções.

**No R09, a evidência vai mascarada.** O `snippet` de um segredo reproduz o segredo,
e o relatório vira o vazamento. Escreva a linha com o valor substituído:
`DB_PASS=***`. O identificador sobrevive, que é o que torna a citação conferível, e
o valor não sai do código. Vale para qualquer achado cujo trecho literal seja a
credencial.

**`unverifiable` não cita linha.** É opcional; quando vem, cada entrada traz `topic`
e `reason`, e pode trazer `requirement`, `question` e os códigos do LGPD-Check em
`lgpd_check` (sem eles, valem os do requisito). Nada de `evidence` nem `snippet`: o
que tem linha para citar é achado, não "não verificável" — e esta lista sai da skill
para o DevComply, onde trecho de código não deve ir. Escreva `reason` sem colar
código pelo mesmo motivo.

**Status sem acento no JSON** (`Nao atendido`, `Nao verificavel`, `Nao se aplica`) e
com acento no markdown. O validador aceita as duas formas; escreva a primeira no JSON
para que o arquivo não dependa de codificação.

Não existe nota de conformidade de 0 a 100 e não escreva uma. "78% em conformidade" é
uma frase que alguém leva para uma reunião, e nenhum número derivado de leitura de
código sustenta aquela frase diante da ANPD. O que a ferramenta calcula é o
`indice_de_pendencia` — soma ponderada das lacunas abertas, onde menor é melhor e
zero não significa conformidade.

## Rules that keep the report useful

**Every finding carries `arquivo:linha` AND a quoted snippet from that line.** The
citation alone only proves the line exists — and a line that exists can say something
completely different from what you claimed. Pairing it with a backticked fragment of
its real content is what makes the claim checkable, both by `verify_report.py` and by
the reader. A finding you cannot locate goes under "não verificável".

This is not a style preference. On the first real run of this skill, two citations out
of sixty-two pointed at the wrong line, and the verifier waved both through for
exactly one reason: neither carried a snippet.

**Report what passed.** A section listing only problems reads as alarmist and hides
what was actually checked. One line per met requirement is enough.

**Never print a secret.** For R09, cite the location and the kind of credential. Do
not reproduce the value — the report itself gets committed, shared and pasted into
chats.

**Say the confidence out loud.** Alta when you read the code and it is unambiguous.
Média when the evidence is indirect. Baixa when you are inferring from naming. A
Baixa-confidence finding is still worth reporting; a Baixa-confidence finding
presented as certain is what gets the tool uninstalled.

**Run the verifier before handing it over.** `scripts/verify_report.py` re-reads every
citation against the actual files. It costs a second and it is what keeps the promise
in the header from being a slogan.

**Actionable fixes, not restatements of the law.** "Adicionar `DELETE /users/me`
derivando o id do token" is useful. "Garantir a observância do art. 18" is not.
