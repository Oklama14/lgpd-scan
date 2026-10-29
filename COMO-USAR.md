# Como usar o lgpd-scan

Guia prático para quem vai rodar a skill num projeto. Se você quer entender como ela
funciona por dentro, o [README](README.md) explica.

## O que você vai receber

Um arquivo `RELATORIO-LGPD.md` na raiz do seu projeto, com vinte e uma seções — uma
por requisito que dá para verificar em código, vindos da LGPD, das resoluções da ANPD
e do ECA Digital. Cada achado diz o que a lei pede, o que o seu código faz, em qual
`arquivo:linha`, com o trecho daquela linha citado, e o que fazer a respeito.

Junto dele, um `.lgpd-scan/report.json` com o mesmo conteúdo em formato de máquina —
é ele que permite comparar duas auditorias e ver o que melhorou.

Se você pedir, também um `ROPA.md` (art. 37), um `RIPD.md` (art. 38), uma minuta de
cláusulas com operador ou a sua política de privacidade — todos levantados do mesmo
código e conferidos pelo mesmo verificador.

Um trecho real, para você saber o que esperar:

> ### R03 — Direito de eliminação · Não atendido · Severidade alta
>
> **O que o código mostra.** Existe `DELETE /projects/:id` em
> `src/projects/projects.controller.ts:49`, mas nenhuma rota permite que o próprio
> titular exclua a conta.
>
> **O que fazer.** Adicionar `DELETE /users/me`, derivando o id do token, que remova
> o registro e as linhas dependentes.
>
> **Confiança:** Alta.

## Antes de começar

Você precisa de **Python 3.8 ou superior** e de um agente de código com suporte a
skills. Confira o Python:

```bash
python3 --version
```

No Windows, o comando costuma ser `python` em vez de `python3` — se `python3` não
existir, use `python` em todos os comandos deste guia.

**Git é opcional, mas faz diferença de verdade.** Num repositório git a skill lista os
arquivos com `git ls-files`, o que significa que ela respeita o seu `.gitignore` e não
vai gerar achado dentro de `dist/`, `node_modules/` ou qualquer código gerado. E ela
consegue distinguir uma senha num arquivo commitado de uma senha num arquivo ignorado
— a primeira é exposição real, a segunda não. Sem git, os dois casos ficam iguais.

## Instalação

```bash
git clone https://github.com/Oklama14/lgpd-scan.git
cd lgpd-scan
./install.sh --scope user      # vale em todo projeto
```

No Windows:

```powershell
git clone https://github.com/Oklama14/lgpd-scan.git
cd lgpd-scan
.\install.ps1 -Scope user
```

Rode com `--dry-run` (ou `-DryRun`) primeiro se quiser ver o que ele vai escrever
antes de escrever. O instalador detecta quais agentes você tem e, para os que não são
o Claude Code, escreve um bloco delimitado no arquivo de contexto que aquele agente já
lê — `AGENTS.md` para Codex e OpenCode, `GEMINI.md` para o Gemini CLI,
`.cursor/rules/lgpd-scan.mdc` para o Cursor. Reinstalar troca o bloco em vez de
empilhar outro, e `--uninstall` remove tudo o que ele criou.

Confirme que ficou assim:

```
~/.claude/skills/lgpd-scan/
├── SKILL.md
├── scripts/
│   ├── collect.py
│   └── verify_report.py
└── references/
    ├── requirements/     R01–R21, um arquivo por grupo
    ├── artifacts/        ROPA, RIPD, DPA
    ├── stacks/           Node, Spring e front-end
    ├── annotations.md
    └── report-template.md
```

Sem instalador, funciona igual: copie a pasta para `~/.claude/skills/lgpd-scan/`.

## Rodando

Abra o agente **dentro da pasta do projeto que você quer auditar** e peça em português
mesmo. Qualquer uma destas frases funciona:

- "audita este projeto pra LGPD"
- "gera um relatório de conformidade do repositório"
- "esse schema tem problema de privacidade?"
- "a gente está tratando dado pessoal direito aqui?"
- "gera o ROPA" · "preciso do RIPD" · "monta a minuta de DPA do Google"
- "escreve a política de privacidade a partir do código"
- "esse produto alcança menor de idade, e a verificação de idade tá ok?"

Você não precisa citar o nome da skill. Ela também é acionada quando você pede revisão
de privacidade de um schema, de uma migration ou de um fluxo de autenticação, mesmo
sem falar "LGPD".

Num projeto de porte médio a análise leva alguns minutos, quase todos gastos pelo
agente lendo os arquivos — a varredura em si termina em segundos.

## Como ler o relatório

Comece pela seção **Comece por aqui** — três ações priorizadas, porque vinte e uma
seções são uma parede e você precisa saber onde gastar a próxima hora. Depois a tabela
**Situação por requisito**, que mostra os vinte e um de uma vez e é o mapa do resto.

Cada requisito recebe um status:

| Status | O que significa |
|---|---|
| **Atendido** | Tem evidência no código de que está resolvido |
| **Parcial** | Existe, mas com defeito ou incompleto |
| **Não atendido** | Procurou e não achou, ou achou algo que falha |
| **Não verificável** | Não dá para saber só pelo código |
| **Não se aplica** | O requisito não alcança este tipo de produto |

`Não se aplica` aparece principalmente no grupo do ECA Digital (R18 a R21): numa
ferramenta interna B2B não há menor entre os titulares, e o relatório diz isso com a
razão escrita em vez de ficar calado — você precisa saber que a pergunta foi feita.

E cada lacuna recebe severidade **Alta**, **Média** ou **Baixa**, medida por exposição
do titular, não por trabalho de corrigir. Uma rota de exclusão faltando é alta porque
nega um direito que a lei garante; falta de trilha de auditoria é média.

Preste atenção especial em duas seções que existem justamente para o relatório ser
honesto: **Não verificável a partir do código**, que lista o que a ferramenta
suspeitou mas não conseguiu confirmar, e **Limitações desta análise**.

Cada achado também traz uma **confiança**. Confiança Baixa quer dizer que o agente
inferiu pelo nome de um campo sem confirmar o uso — vale conferir antes de agir.

## Quando o relatório errar

Vai acontecer. A skill foi desenhada para admitir isso, e nenhum achado vem sem a
citação que permite você conferir em dez segundos.

Se um achado estiver errado, diga ao agente qual e por quê — *"o R03 está errado, a
exclusão de conta está em `AccountService.purge()`"*. Ele corrige e reescreve a seção.
Isso vale a pena mesmo que você não vá guardar o relatório: erro recorrente é sinal de
que o campo ou a convenção do seu projeto merece entrar nas regras da skill.

Se um achado parecer inventado — arquivo que não existe, linha que não bate — rode a
verificação você mesmo:

```bash
python3 ~/.claude/skills/lgpd-scan/scripts/verify_report.py RELATORIO-LGPD.md
python3 ~/.claude/skills/lgpd-scan/scripts/verify_report.py ROPA.md --kind ropa
```

Ela relê todas as citações e aponta as que não fecham: arquivo inexistente, linha além
do fim do arquivo, linha em branco, trecho citado que não bate com a linha, e a
categoria mais importante — as citações que vieram sem trecho ao lado, que são as
únicas que nenhuma checagem automática alcança. O agente já roda isso antes de
entregar, mas rodar de novo custa um segundo.

## Quando o achado é falso positivo de verdade

Diferente do caso acima: não é que o agente errou o julgamento, é que o coletor marca
uma linha que legitimamente não é o que ele pensa. Um campo `nome` que guarda apelido
público, uma coluna `cpf_mascarado` que nunca teve CPF inteiro. Dizer isso ao agente
resolve naquela conversa e volta na próxima.

Para resolver de vez, marque no próprio código:

```ts
const nome = gerarApelido();  // lgpd-scan: ignorar personal_data_field — apelido publico, nao identifica
```

O **motivo depois do travessão é obrigatório**. Marca sem razão escrita não é
respeitada: ela aparece no relatório como supressão rejeitada, com a explicação do que
falta. Uma marca que silencia sem explicar transfere o problema para o próximo leitor,
que provavelmente é você em seis meses.

E nada desaparece de vez: achado suprimido vai para uma seção própria do relatório,
com a sua razão do lado. Isso é de propósito — uma auditoria que o auditado pode
esvaziar sem deixar rastro não serve de evidência para ninguém.

O mesmo mecanismo serve para **declarar** o que o código não diz:

```ts
@Column() cid: string;  // @lgpd: classificacao=sensivel base_legal=art11_ii retencao=20anos
```

Isso entra no relatório como declaração sua — evidência positiva, citada como
declaração, não como algo que a ferramenta apurou. Vocabulário completo em
`references/annotations.md`.

## Gerando ROPA, RIPD e minuta de DPA

```
"gera o ROPA deste projeto"
"preciso do RIPD, a ANPD pediu"
"monta a minuta de cláusulas com o Google, que é o operador aqui"
```

Peça depois da auditoria, não antes: o ROPA reaproveita o inventário que o relatório
já levantou, e gerar antes significa fazer o mesmo trabalho duas vezes.

Três coisas que vale saber antes de pedir:

**O que o código não mostra vem marcado, não preenchido.** Base legal, finalidade
contratual, prazo de retenção, nome do encarregado: você vai ver
`⚠ A PREENCHER PELO CONTROLADOR` no lugar do valor. Isso é o desenho funcionando, não
um documento incompleto — um ROPA com a base legal chutada seria assinado como se
fosse verdade.

**O documento passa pelo mesmo verificador do relatório.** Cada linha da tabela de
operações precisa citar evidência ou declarar que não há. É o que separa um ROPA
levantado do código de um ROPA respondido de memória, e é a razão de a ferramenta
gerar esses documentos em vez de mandar você preencher um formulário.

**A minuta de DPA é ponto de partida para uma conversa com advogado, não contrato.**
O corpo das cláusulas é modelo, disponível em qualquer lugar. O que a skill acrescenta
de real são os dois anexos — atividades e medidas técnicas, levantados do seu código,
que é justamente a parte que costuma vir em branco. O documento diz isso na primeira
linha, e é para dizer mesmo.

## Rodando no CI

Uma auditoria é uma foto: ela envelhece na semana seguinte, porque o código continua
andando. O portão transforma a foto em regra — ele roda só o coletor, leva segundos e
não chama modelo nenhum, então pode rodar em toda PR.

Uma vez, para gravar o ponto de partida:

```bash
python3 ~/.claude/skills/lgpd-scan/scripts/ci_check.py . --update-baseline
git add .lgpd-scan/baseline.json
git commit -m "chore: baseline lgpd-scan"
```

Depois, em cada PR:

```bash
python3 ~/.claude/skills/lgpd-scan/scripts/ci_check.py . --fail-on alta
```

No GitHub, copie `examples/github/lgpd-scan.yml` para `.github/workflows/` e pronto;
com o SARIF ligado os achados aparecem na aba Security do repositório.

**O que reprova, e o que não.** Segredo novo em arquivo versionado, controle que
sumiu (a rota de exclusão de conta que desapareceu num refactor), campo de idade novo
sem nada que verifique. Campo pessoal novo **não** reprova — é o dia a dia de um
produto que cresce, e aparece como informação. Um portão que grita em refactor é
desligado na primeira semana, então a rota de exclusão mudar de arquivo não é
regressão: só sumir de vez é.

**Sem baseline ele recusa rodar.** Não existe "piorou" sem ponto de comparação, e um
check que reprova a PR que o instalou é desinstalado na mesma tarde.

E o mais importante: passar no portão **não significa conformidade**. Significa que
não houve regressão detectável em código desde a última comparação. A auditoria
completa continua sendo outra coisa.

## Comparando duas auditorias

```bash
python3 ~/.claude/skills/lgpd-scan/scripts/report_data.py diff .lgpd-scan/report-marco.json
```

```
ok R03  Nao atendido -> Atendido  (Direito de eliminacao)
ok R06  Nao atendido -> Atendido  (Registro de consentimento)
!! R10  Atendido -> Parcial  (Minimizacao de dados em logs)

indice de pendencia 25 -> 17 (-8)
```

O **índice de pendência** é a soma ponderada das lacunas abertas (Alta 3, Média 2,
Baixa 1). Menor é melhor, e **zero não significa conformidade** — é uma contagem de
pendências, não uma nota. Você não vai encontrar "78% em conformidade" em lugar
nenhum desta ferramenta, de propósito: é uma frase que alguém leva para uma reunião, e
nenhum número derivado de leitura de código sustenta aquela frase diante da ANPD.

## Comparando com o que a equipe declarou no DevComply

Se a equipe preencheu o checklist do [DevComply](https://dev-comply.vercel.app), exporte
as declarações de lá: no checklist do projeto, o botão **Comparar com o código** baixa o
`devcomply-declaracoes.json`. Salve o arquivo na raiz do repositório e peça ao agente:
"compara com o que declaramos no DevComply". Ou rode direto, depois de uma auditoria:

```bash
python3 ~/.claude/skills/lgpd-scan/scripts/devcomply.py conciliar . --declaracoes devcomply-declaracoes.json
```

O que olhar primeiro são as linhas `!!`: itens marcados como implementados que o
código desmente. Cada uma entra na seção "Declarado × código" do relatório, e o
verificador recusa o relatório que deixa uma de fora. `--falhar-se-divergir` faz o
comando sair com erro quando houver divergência, se você quiser usá-lo no CI.

O caminho inverso prepara o resultado da auditoria para o DevComply (a importação, do
lado do DevComply, ainda não existe):

```bash
python3 ~/.claude/skills/lgpd-scan/scripts/devcomply.py export .
```

Grava `.lgpd-scan/devcomply.json` com a situação de cada item do checklist no código,
com arquivo e linha e **sem trecho de código** — o trecho pode conter um segredo ou
dado pessoal de teste, e o DevComply envia texto para uma IA na nuvem.

## Arquivos que aparecem no seu projeto

A skill cria uma pasta `.lgpd-scan/` com: o `candidates.json`, que é a lista bruta de
onde o coletor olhou; o `STATUS.md`, que registra os sinais encontrados, os ausentes e
quais requisitos já foram avaliados; o `report.json` com o relatório em formato de
máquina; se você usar o portão, a `baseline.json`; e, se comparar com o DevComply, o
`conciliacao.json` e o `devcomply.json`.

**A `baseline.json` é a exceção: essa você commita.** É o ponto de comparação do CI, e
sem ela no repositório o portão não tem com o que comparar. As outras três não fazem
falta. O segundo é o que
permite retomar uma auditoria interrompida de onde ela parou — se você pedir a
auditoria em outro dia, o agente lê o STATUS.md antes de recomeçar. Nenhum dos dois
faz falta no repositório:

```gitignore
.lgpd-scan/
!.lgpd-scan/baseline.json
```

Quanto ao `RELATORIO-LGPD.md`, você decide. Commitar tem uma vantagem real: o próximo
relatório vira um diff, e dá para ver conformidade melhorando ou piorando ao longo do
tempo. Só lembre que ele fica visível para quem tiver acesso ao repositório.

## Rodando só o coletor

Se você quiser ver o que a skill enxerga, sem gastar tokens de agente:

```bash
python3 ~/.claude/skills/lgpd-scan/scripts/collect.py .
```

Sai um resumo no terminal com os sinais encontrados, os sinais **ausentes** (que
costumam ser os achados mais importantes) e a contagem de arquivos por categoria.

Opções:

```
--out PATH        onde gravar o JSON
--max-hits N      limite de ocorrências por sinal (padrão 40)
--include-tests   incluir arquivos de teste na varredura
--no-status       não escrever o STATUS.md
--quiet           só grava o JSON, sem resumo
```

## Perguntas que aparecem sempre

**Meu código sai da minha máquina?** Não. O coletor é um script Python local sem
acesso à rede, e a leitura dos arquivos é feita pelo agente que já está rodando aí.
Não existe servidor do lgpd-scan.

**Funciona com a minha stack?** Node/TypeScript e Java/Spring têm notas específicas —
o agente sabe onde o NestJS esconde as rotas e onde o Spring guarda o encoder de
senha. Outras stacks funcionam com o raciocínio genérico, e o relatório declara na
seção de limitações que a análise foi mais rasa.

**Posso rodar em monorepo?** Pode, e a partir da raiz mesmo — a skill procura os
manifestos (`package.json`, `pom.xml`) até três níveis abaixo, então um repositório com
`api/` e `client/` é reconhecido normalmente. Apontar para um subprojeto continua
valendo quando você quer um relatório mais focado.

**Passar no portão de CI significa que estou em conformidade?** Não. Significa que
não houve regressão detectável em código desde a última comparação — que é uma
pergunta bem menor, e a única que um check automático consegue responder honestamente.

**Isso me deixa em conformidade com a LGPD?** Não, e é importante ser claro nisso.
Código mostra o que está **implementado**, não o que é **praticado**. Contrato com
operador, encarregado designado, treinamento de equipe, segurança física, relatório de
impacto — nada disso existe num repositório, e tudo isso a lei exige. O relatório é
evidência técnica para uma revisão humana, de preferência do encarregado ou da
assessoria jurídica. Não é atestado de conformidade e não é parecer jurídico.
