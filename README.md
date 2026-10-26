# lgpd-scan

Uma skill de agente que audita conformidade com a LGPD, as resoluções da ANPD e o
ECA Digital usando **o código-fonte como evidência**, e escreve um relatório em
português onde todo achado aponta para `arquivo:linha` e cita o trecho daquela linha.

Gera também ROPA (art. 37), RIPD (art. 38), minuta de cláusulas com operador e a
própria política de privacidade — e, diferente do resto da categoria, **passa os
documentos que gera pelo próprio verificador**.

E roda no CI: grava uma baseline e reprova a PR que piora a conformidade — um segredo
novo em arquivo versionado, a rota de exclusão de conta que sumiu num refactor, um
campo de idade sem nada que verifique.

Ferramentas de conformidade normalmente pedem que o desenvolvedor *descreva* o
sistema num formulário, e então julgam a descrição. Quem escreve "usamos
criptografia forte nas senhas" recebe um relatório limpo mesmo quando o código usa
MD5. Esta skill não pergunta nada ao desenvolvedor: ela lê o que o sistema faz.

Roda inteiramente na máquina de quem usa. Sem backend, sem chave de API, sem enviar
código para lugar nenhum.

## Instalação

```bash
git clone https://github.com/Oklama14/lgpd-scan.git
cd lgpd-scan

./install.sh                 # detecta os agentes e instala no projeto atual
./install.sh --scope user    # instala para o usuário, valendo em todo projeto
./install.sh --dest ../meu-repo
./install.sh --dry-run       # mostra o que faria, sem escrever nada
```

No Windows, `.\install.ps1` com as mesmas opções (`-Scope user`, `-Dest`, `-DryRun`,
`-Uninstall`). Funciona no PowerShell 5.1 que já vem no sistema.

Agentes cobertos: **Claude Code**, **Codex**, **Gemini CLI**, **Cursor** e
**OpenCode**. Uma honestidade que muda a expectativa: só o Claude Code tem mecanismo
nativo de skill. Para os outros quatro, o instalador copia a pasta e escreve um
ponteiro no arquivo de contexto que aquele agente já lê (`AGENTS.md`, `GEMINI.md`,
`.cursor/rules`), delimitado por marcador — reinstalar troca o bloco, desinstalar o
remove. Funciona, mas não é a mesma coisa que uma skill registrada.

Instalação manual, se preferir: copie a pasta para `~/.claude/skills/lgpd-scan/`.

Depois é só pedir, em linguagem natural: *"audita este projeto pra LGPD"*,
*"esse schema tem problema de privacidade?"*, *"gera o ROPA do repositório"*.

Requisito: Python 3.8+ (só biblioteca padrão). Git é opcional, mas com ele a análise
fica bem melhor. Veja o [guia de uso](COMO-USAR.md) para o passo a passo.

## Como funciona

```
collect.py  →  candidates.json  →  o agente lê o código  →  RELATORIO-LGPD.md  →  verify_report.py
determinístico    onde olhar          julgamento          + .lgpd-scan/report.json   confere a evidência
      │                                                   ROPA · RIPD · DPA · política ↗
      └──→ ci_check.py  →  baseline.json  →  reprova a PR que piora  →  SARIF
           sem modelo, reproduzível, roda em segundos
```

O coletor varre o repositório, classifica arquivos e roda detecção por expressão
regular. Ele é rápido porque nunca monta AST e nunca chama modelo nenhum — e,
principalmente, **ele não julga**. Um casamento de regex é uma hipótese sobre onde
olhar, nunca um achado.

Quem julga é o agente, abrindo os arquivos apontados. Essa separação existe por dois
motivos: uma rota `DELETE /users/:id` que só marca `deleted_at` não é exclusão, e
descobrir isso exige ler o handler; e a coleta ser determinística é o que torna o
resultado reprodutível.

Se o projeto for um repositório git, a listagem sai do `git ls-files` — o que faz o
`.gitignore` ser respeitado de graça, então achado em código gerado ou em dependência
vendorizada simplesmente não acontece. Cada ocorrência também vem marcada como
versionada ou não, o que decide a gravidade de segredo no repositório: senha em
arquivo commitado continua no histórico depois de você apagar a linha.

E a listagem é conferida, não aceita por fé: o coletor conta os arquivos de texto no
disco e compara. Se o git devolveu zero e há arquivos lá, ele volta para a varredura de
diretório e avisa — é o que acontece quando a pasta varrida está dentro de um
repositório que a ignora, e sem a checagem a varredura não lia nada, não achava nada, e
o relatório saía limpo.

No fim, o `verify_report.py` relê todas as citações. Ele confere que cada
`arquivo:linha` existe, que a linha não é vazia, e que o trecho citado ao lado dela
aparece de fato ali — e, principalmente, lista as citações que **não** trouxeram
trecho, que são justamente as que nenhuma checagem alcança. Um relatório que inventa
evidência destrói a confiança na ferramenta mais rápido do que um achado perdido.

O verificador conhece os quatro documentos e aplica a checagem de cada um: no
relatório, achado sem evidência; no ROPA, **linha de tabela** sem evidência; no RIPD,
risco sem evidência; no DPA, anexo que foi copiado em vez de levantado. A regra que
carrega o peso é a das linhas: ou a linha cita evidência, ou declara que não há. Uma
linha que afirma uma operação de tratamento sem citar nada e sem admitir nada é uma
linha escrita de memória.

O sinal mais importante costuma ser a **ausência**: nenhuma rota de exclusão, nenhum
registro de consentimento, nenhuma rotina de expurgo. O coletor reporta ausências
explicitamente, porque um grep que não achou nada é indistinguível de um grep que
nunca rodou.

### Declaração não é implementação

Toda ocorrência vinda de política de privacidade, termos de uso ou página de cookie
sai marcada com `declaration_only`. Uma política que diz "verificamos a idade dos
titulares" é uma promessa; uma integração de verificação no cadastro é uma
implementação. Creditar a primeira como se fosse a segunda é o jeito mais fácil de
esta ferramenta produzir um relatório perigosamente errado, e por isso o relatório tem
uma seção só para reconciliar as duas.

### Supressão de falso positivo, com motivo obrigatório

O projeto pode discordar do coletor, no próprio código:

```ts
const nome = gerarApelido();  // lgpd-scan: ignorar personal_data_field — apelido publico, nao identifica
@Column() cid: string;        // @lgpd: classificacao=sensivel base_legal=art11_ii retencao=20anos
```

Duas regras de desenho que valem a menção. O **motivo é obrigatório**: marca sem razão
escrita é rejeitada e aparece no relatório como rejeitada. E **nada desaparece em
silêncio**: achado suprimido vai para uma seção própria com a razão do desenvolvedor,
porque a alternativa é uma auditoria que o auditado pode esvaziar sem deixar rastro.
Detalhes em [`references/annotations.md`](references/annotations.md).

### Auditoria interrompida

O coletor escreve `<repo>/.lgpd-scan/STATUS.md` com os sinais presentes e ausentes, as
anotações lidas e os checkpoints por requisito. Vinte e um requisitos não cabem numa
sessão, e o arquivo é o que permite retomar de onde parou em vez de recomeçar.

## O que é verificado

Vinte e um requisitos, em três grupos. O relatório declara cada um como `Atendido`,
`Parcial`, `Não atendido`, `Não verificável` ou `Não se aplica` — e a última importa
tanto quanto as outras, porque o leitor precisa saber que a pergunta foi feita.

### Lei 13.709/2018 — base

| # | Requisito | Base legal |
|---|---|---|
| R01 | Inventário de dados pessoais | Art. 5º, I |
| R02 | Dados sensíveis identificados e tratados como tais | Art. 11 |
| R03 | Direito de eliminação | Art. 18, VI |
| R04 | Direito de acesso e portabilidade | Art. 18, II e V |
| R05 | Direito de correção | Art. 18, III |
| R06 | Registro de consentimento | Art. 8º, §1º |
| R07 | Retenção e expurgo | Art. 15 e 16 |
| R08 | Segurança do armazenamento de credenciais | Art. 46 |
| R09 | Segredos fora do repositório | Art. 46 |
| R10 | Minimização de dados em logs | Art. 6º, III |
| R11 | Registro das operações de tratamento | Art. 37 |
| R12 | Compartilhamento com terceiros | Art. 33 |

### Resoluções da ANPD

| # | Requisito | Base legal |
|---|---|---|
| R13 | Registro de incidente de segurança | Res. CD/ANPD 15/2024, art. 10 |
| R14 | Comunicação de incidente em três dias úteis | Res. CD/ANPD 15/2024, art. 6º e 9º |
| R15 | Encarregado indicado e canal do titular | Res. CD/ANPD 18/2024 |
| R16 | Salvaguarda de transferência internacional | Res. CD/ANPD 19/2024 |
| R17 | Anonimização e pseudonimização | Art. 12 |

### ECA Digital — Lei 15.211/2025

Em vigor desde 17 de março de 2026. É onde um relatório tem mais chance de dizer ao
desenvolvedor algo que ele ainda não sabia.

| # | Requisito | Base legal |
|---|---|---|
| R18 | Verificação de idade **sem autodeclaração** | Lei 15.211/2025 |
| R19 | Vinculação a responsável legal | Lei 15.211/2025 |
| R20 | Configuração padrão mais protetiva | Lei 15.211/2025 |
| R21 | Perfilamento publicitário direcionado a menores | Lei 15.211/2025 |

Este grupo inverte o sinal de leitura do resto da auditoria. Em geral, encontrar um
campo é neutro e a ausência é o achado. Aqui, encontrar um campo de data de nascimento
ou uma caixa "confirmo que tenho 18 anos" **sem** nada que verifique *é* o achado — a
lei veda expressamente a autodeclaração, então o controle que o projeto acha que tem é
justamente o que a lei recusa.

Stacks com suporte específico: **Node/TypeScript** (Express, NestJS, Prisma, TypeORM,
Sequelize), **Java/Spring** (Spring Boot, Spring Data JPA, Hibernate, Flyway,
Liquibase) e **front-end** (Angular, React, Vue, Svelte, Next, Nuxt). Outras stacks
funcionam com o raciocínio genérico, e o relatório declara que a análise foi mais rasa
nesse caso.

O front-end tem achados que o back-end não mostra: o token de sessão no
`localStorage`, lido por qualquer script da página; a fonte do Google e o CDN, que
mandam o IP do titular a um terceiro sem o servidor enviar nada; o `gtag` no
`index.html` que roda antes de qualquer banner de cookies.

## Documentos que a skill gera

| Peça | Base legal | O que vem do código |
|---|---|---|
| `RELATORIO-LGPD.md` | — | tudo: é o produto principal |
| `.lgpd-scan/report.json` | — | o mesmo relatório em formato de máquina |
| `ROPA.md` | Art. 37 | operações, inventário, destinatários, medidas de segurança, retenção |
| `RIPD.md` | Art. 38 | tipos de dado, pontos de coleta, controles, riscos com evidência |
| `DPA-MINUTA-*.md` | Art. 39 e 46 | Anexo I (atividades) e Anexo II (medidas técnicas) |
| `POLITICA-PRIVACIDADE.md` | Art. 9º | os dados tratados e **só os direitos que o código implementa** |

Duas regras valem para os três artefatos, e são elas que os separam de um formulário
preenchido:

**O que o código não mostra vai marcado, não preenchido.** Finalidade, base legal
escolhida, prazo contratual, nome do encarregado, medidas organizacionais: nada disso
está no repositório, e entra como `⚠ A PREENCHER PELO CONTROLADOR`. Um ROPA com a base
legal chutada é pior que um ROPA com a lacuna visível — o primeiro será assinado como
se fosse verdade.

**O documento gerado é declaração, não apuração.** O ROPA é obrigação do controlador;
quem responde por ele é o controlador. O documento diz isso no rodapé, com essas
palavras.

### A política é a inversão da ferramenta

Toda ferramenta desta área gera política a partir de questionário: o desenvolvedor
responde "coletamos e-mail e telefone" e sai um texto sem relação com o sistema. Aqui
a política sai do inventário, então não pode omitir um campo que existe nem inventar
um que não existe. E vale uma regra a mais:

> **A política só promete o que o código entrega.**

Sem rota de exclusão, a política não diz "você pode excluir sua conta a qualquer
momento" — diz que a exclusão é feita mediante pedido ao encarregado, o que é legítimo
pela LGPD, é verdade, e é o que o sistema faz. Uma política que promete um botão que
não existe não é um texto ruim: é a não conformidade, documentada e publicada pelo
controlador.

O verificador aplica isso e cita a frase:

```
PROMESSA SEM IMPLEMENTACAO (3):
  promete exclusao da conta pelo titular e nenhum sinal sustenta (delete_route ou
  delete_route_alt): "Voce pode excluir a sua conta a qualquer momento nas
  configuracoes."
```

Promessa **mediada** ("solicite pelo canal do encarregado") passa: a lei garante o
direito, não o botão.

### O resto

A minuta de DPA é o artefato de menor valor dos quatro e o de maior risco de uso
indevido: o corpo das cláusulas é modelo, e o que a skill acrescenta de real são os
dois anexos. Vale dizer isso em voz alta em vez de entregar algo que pareça pronto
para assinatura.

## No CI: a auditoria deixa de ser uma foto

Uma auditoria envelhece na semana seguinte, porque o código continua andando e a
conformidade anda junto. O portão transforma a foto em regra:

```bash
python3 scripts/ci_check.py . --update-baseline   # uma vez, e commite a baseline
python3 scripts/ci_check.py . --fail-on alta      # a cada PR
```

```
=== lgpd-scan: portao de conformidade ===
achados            alta 3, media 1, baixa 0

  [alta] docker-compose.yml:4
           hardcoded_secret: credencial literal em arquivo versionado (sobrevive a remocao)
  [alta] (repositorio)
           delete_route: rota de exclusao existia na baseline e nao aparece mais
  [alta] src/cadastro.entity.ts:4
           age_self_declaration: passou a coletar idade sem provedor de verificacao
```

`action.yml` é uma GitHub Action pronta e `examples/github/lgpd-scan.yml` o workflow
para copiar; com `--sarif` os achados aparecem na aba Security do repositório.

**Isto só é possível porque o coletor é determinístico.** Uma skill que chama modelo
dá resposta diferente a cada execução, e um portão construído sobre isso oscila — time
nenhum aceita um check que reprova hoje o que aprovou ontem. A separação entre coletor
(regex, reproduzível) e julgamento (agente, caro, não determinístico) existe desde a
primeira versão por outro motivo, e é ela que paga aqui.

Três papéis, três granularidades, e a do meio é a que evita o alarme falso caro:

| Papel | Observado por | Por quê |
|---|---|---|
| risco | (sinal, arquivo) | credencial nova em outro arquivo é achado novo |
| controle | repositório inteiro | a rota mudar de arquivo num refactor não é regressão |
| inventário | contagem, não reprova | campo pessoal novo é o dia a dia de um produto que cresce |

Sem baseline o portão recusa rodar em vez de inventar um ponto de partida: não existe
"piorou" sem comparação, e um check que reprova a PR que o instalou é desinstalado na
mesma tarde.

## Integração com o DevComply

O DevComply e esta skill olham para o mesmo problema de
lados opostos, e é por isso que se completam. O DevComply é um checklist web sobre o
LGPD-Check: a equipe **declara** o que está implementado, e o que não deixa rastro em
código — encarregado, contratos, treinamento, plano de incidentes — só pode ser
declarado. A skill lê o que o **código faz**, e nisso uma declaração não a convence.

`references/requirements/lgpd-check.md` liga os dois: para cada um dos 61 itens do
LGPD-Check, qual requisito da skill o decide, qual só o toca, e quais só a organização
prova.

```bash
python3 scripts/devcomply.py conciliar . --declaracoes devcomply-declaracoes.json
python3 scripts/devcomply.py export .
```

```
=== lgpd-scan: declarado (DevComply) x codigo ===

  T-11  -  lacuna nos dois                     Nao atendido    R11
  C-03  !! declarado, o codigo nao mostra      Nao atendido    R06
  D-03  !  declarado, o codigo mostra lacuna   Parcial         R04
  D-04  +  implementado, nao declarado         Atendido        R05
  D-07  ok confirmado                          Atendido        R03
  S-02  ?  nao verificavel no codigo           Nao verificavel R16
  R-01  !! declarado, o codigo nao mostra      Nao atendido    R15
  R-07     so a organizacao prova              -               -

3 divergencia(s): C-03, D-03, R-01
```

**`conciliar`** confronta as declarações com o `report.json`. O achado que justifica
ter as duas ferramentas é a divergência — item marcado como implementado que o código
desmente —, e o verificador recusa o relatório que deixa uma de fora da seção
"Declarado × código".

**`export`** grava `.lgpd-scan/devcomply.json` para o DevComply importar: a situação
de cada item no código, a severidade nas duas escalas (`Alta`↔`Catastrófica`,
`Média`↔`Grave`, `Baixa`↔`Leve`), arquivo e linha — **sem trecho de código**, porque o
trecho pode carregar dado pessoal de um seed ou um segredo, e o DevComply manda texto
para uma IA na nuvem. O que o código não responde vai junto, como perguntas para a
equipe.

Os formatos são contratos versionados: `devcomply/declaracoes/1` na entrada,
`lgpd-scan/devcomply/1` e `lgpd-scan/conciliacao/1` na saída.

## Rodando o coletor sozinho

Útil para inspecionar o que a skill vai ver, ou para integrar em outro fluxo:

```bash
python3 scripts/collect.py /caminho/do/projeto
```

```
--out PATH        onde gravar o JSON (padrão: <repo>/.lgpd-scan/candidates.json)
--max-hits N      limite de ocorrências por sinal (padrão 40)
--include-tests   incluir arquivos de teste
--no-status       não escrever o STATUS.md
--quiet           só grava o JSON, sem resumo no terminal
```

E para conferir um documento já escrito:

```bash
python3 scripts/verify_report.py RELATORIO-LGPD.md --repo /caminho/do/projeto
python3 scripts/verify_report.py ROPA.md --repo /caminho/do/projeto --kind ropa
python3 scripts/report_data.py summary .lgpd-scan/report.json
python3 scripts/report_data.py diff .lgpd-scan/report-marco.json
```

O tipo é detectado pelo nome e pelo título; `--kind` força
(`relatorio`, `ropa`, `ripd`, `dpa`, `politica`). Quando existe um
`.lgpd-scan/report.json`, ele é validado junto: schema, evidência conferida contra o
código, e comparação com o que o markdown declara. Sai com código 1 se alguma citação apontar para
arquivo ou linha inexistente, se um achado afirmar lacuna sem citar nada, se uma linha
de tabela afirmar um fato sem evidência nem lacuna declarada, se o documento tiver
saído com marcador de modelo dentro, se faltar seção obrigatória, ou se o texto tiver
reproduzido uma credencial. `--strict` falha também nos avisos e nas citações sem
trecho.

## Testes

```bash
python3 scripts/run_tests.py          # tudo
python3 scripts/run_tests.py eca      # só os casos com "eca" no nome
python3 scripts/run_tests.py -v       # mostra cada asserção
```

**62 casos, 326 checagens**, em cinco suítes:

| Suíte | O que é cada caso |
|---|---|
| coletor | um repositório mínimo e um `expected.json` com o que deve e o que **não** deve aparecer |
| verificador | um documento escrito e as categorias que ele deve acusar |
| portão de CI | um par `antes/` e `depois/`, e os achados que a mudança deve gerar |
| devcomply | um `report.json` e as declarações do DevComply; o que a exportação e a conciliação devem dizer |
| coerência | invariantes entre arquivos: tabela de requisitos, ponte com o LGPD-Check, nomes de sinais, versão, frontmatter |

A regra que sustenta o crescimento de escopo: **nenhum requisito novo entra sem
fixture.** Um léxico regride em silêncio — você alarga um padrão para pegar um campo
real e três sinais sem relação passam a disparar em outro lugar. Vários dos casos
existem só para congelar falso positivo encontrado contra prosa portuguesa real:
"único parágrafo" virando provedor de verificação de idade, "responsável pelas
decisões" virando vínculo parental, "Todo titular tem direito" virando marcador não
preenchido, e a interpolação `{{ versao }}` de uma política em Angular virando buraco
de modelo.

## O que esta ferramenta não faz

Código mostra o que está **implementado**, não o que é **praticado**. Ficam fora do
alcance de qualquer análise estática, e continuam sendo exigências da lei: contrato
com operadores, encarregado designado que de fato atende, treinamento de equipe,
segurança física, plano de resposta a incidente testado, e o destino dos dados fora do
repositório.

Gerar ROPA, RIPD e minuta de DPA amplia o alcance mas não muda isso: um documento
gerado é declaração do controlador, não evidência que a ferramenta apurou. O relatório
distingue as duas coisas e diz na seção de limitações que varredura limpa não é
conformidade legal.

O relatório é evidência técnica para revisão humana. Não é atestado de conformidade
e não é parecer jurídico.

## Licença

MIT. Veja [LICENSE](LICENSE).
