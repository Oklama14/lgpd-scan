# Changelog

## 0.6.0 — o declarado contra o codigo

O DevComply registra o que a equipe **declara**, num checklist com os itens do
LGPD-Check; esta skill registra o que o **codigo faz**. Ate aqui os dois nao se
falavam: listas de requisitos, escalas e ate o sentido de "evidencia" eram
diferentes. Esta versao liga um ao outro e cobre o front-end, que a skill nao lia.

**62 casos, 326 checagens**, em cinco suites: coletor, verificador, portao de CI,
DevComply e coerencia entre arquivos.

### Ponte com o LGPD-Check

`references/requirements/lgpd-check.md` liga R01–R21 aos 61 itens do LGPD-Check.
Duas relacoes: **direta** (o requisito responde a mesma pergunta do item, e o status
dele e o status do item no codigo) e **parcial** (toca o item sem decidir). Os 61
itens caem em quatro grupos, sem sobra nem repeticao: 17 decididos pelo codigo, 15 so
tocados, 10 que so a organizacao prova (encarregado, treinamento, RIPD) e 19 que o
codigo poderia responder e a skill ainda nao avalia — candidatos a requisito.

A tabela existe duas vezes, no documento e em `report_data.LGPD_CHECK`, e a suite de
coerencia falha se as duas divergirem.

A ligacao **nao** e um campo `lgpd_check` escrito pelo modelo em cada requisito do
report.json. E derivada da tabela na exportacao: o que se deriva nao se escreve, e o
que nao se escreve nao diverge.

### Conciliacao: declarado x codigo

`scripts/devcomply.py conciliar` le as declaracoes exportadas pelo DevComply
(`devcomply/declaracoes/1`) contra o report.json e grava
`.lgpd-scan/conciliacao.json`. Declaracao entra como a politica de privacidade entra
no resto da skill: pista de onde olhar, nunca evidencia.

O resultado que importa e a **divergencia** — item marcado como implementado cujo
requisito direto o codigo mostra como `Parcial` ou `Nao atendido`. O verificador
ganhou a categoria **DECLARACAO SEM IMPLEMENTACAO**, irma de PROMESSA SEM
IMPLEMENTACAO: le a conciliacao sozinho e recusa o relatorio que deixa uma
divergencia fora da secao "Declarado × codigo". Conciliacao feita contra um
report.json anterior tambem e recusada: cobraria a secao a partir da auditoria errada.

### Exportacao para o DevComply

`scripts/devcomply.py export` grava `.lgpd-scan/devcomply.json`
(`lgpd-scan/devcomply/1`): a situacao de cada item do LGPD-Check no codigo, com a
severidade nas duas escalas, arquivo e linha. **Sem trecho de codigo**, e de
proposito: o trecho pode carregar dado pessoal de um seed ou um segredo, e o
DevComply manda texto para uma IA na nuvem. O contrato e o schema da exportacao, nao
o report.json, para que uma mudanca interna da skill nao quebre a importacao em
silencio.

### "Nao verificavel" como dado

O report.json aceita `unverifiable`: o que a auditoria suspeitou e o codigo nao
responde, com assunto, motivo, a pergunta que resolveria e os itens do LGPD-Check.
Vai na exportacao junto dos requisitos que ficaram `Nao verificavel`, e e de la que o
DevComply tira perguntas para a equipe. O validador recusa entrada sem motivo, codigo
inexistente e qualquer `evidence`: o que tem linha para citar e achado.

### Uma escala de severidade

A skill ja tinha `Alta`, `Media` e `Baixa`; faltava dizer o que cada uma significa.
`references/requirements/index.md` traz agora o criterio, os exemplos e a regra de
desempate do DevComply, com os exemplos trocados pelo que o codigo mostra. A
correspondencia e de um para um com `Catastrofica`, `Grave` e `Leve`, e o
`ci_check.py --fail-on` aceita os dois nomes.

O template ganhou **Comece por aqui** — que o SKILL.md ja prometia e o template nao
tinha —, ordenado por severidade como o plano de acao do DevComply.

### Front-end

`references/stacks/frontend.md`, para Angular, React, Vue, Svelte, Next e Nuxt, e
quatro sinais novos:

- `web_storage_token` — token de sessao em `localStorage`/`sessionStorage` (R08);
- `content_security_policy` — lido em codigo e em configuracao de hospedagem
  (`vercel.json`, `netlify.toml`, `nginx.conf`), nunca em prosa;
- `third_party_web_resource` — fonte, CDN, mapa, captcha: o navegador do titular
  manda IP e user agent ao terceiro sem o back-end enviar nada (R12);
- `cookie_consent_ui` — banner ou gestor de consentimento (R06).

Folhas de estilo passam a ser lidas, mas so para recurso de terceiro: `@import url()`
e por onde a fonte do Google entra, e `.user-email` numa folha de estilo e nome de
classe, nao campo.

### Correcoes

- **`.vue` e `.svelte` nunca eram lidos.** Estavam em `CODE_EXTS` e nao em
  `TEXT_EXTS`: um formulario de cadastro inteiro em Vue saia do inventario sem aviso.
- **Arquivos de referencia ausentes do repositorio.** O `.gitignore` ignorava
  `ROPA.md`, `RIPD.md` e `POLITICA-PRIVACIDADE.md` em qualquer pasta — para nao
  commitar a saida da skill num projeto auditado — e com isso ignorava tambem
  `references/artifacts/ropa.md`, `ripd.md` e `politica-privacidade.md` (o git no
  Windows nao diferencia maiuscula). Quem clonava ficava sem as instrucoes dos
  artefatos, e a fixture 19 falhava. Os padroes agora sao ancorados na raiz.
- **A checagem de nomes de sinal so lia metade das linhas.** Procurava "sinais:", e
  os requisitos em ingles dizem "collector signals:". Agora le as duas, e o sentido
  inverso tambem: sinal do coletor que nenhuma referencia explica falha a suite. Ela
  achou tres — `dsar_flow`, `dsar_deadline` e `content_removal` —, agora documentados.
- **Sinal sem papel no portao de CI** passa a falhar a suite: o portao ignorava em
  silencio qualquer sinal que nao estivesse numa das quatro tabelas.

## 0.5.0 — a auditoria deixa de ser uma foto

As tres coisas desta versao respondem a mesma pergunta: uma auditoria vale por quanto
tempo? Hoje, ate a proxima PR. O relatorio vira dado, o dado vira portao de CI, e o
portao so e possivel porque o coletor e deterministico — a decisao de arquitetura da
primeira versao, que finalmente paga.

**52 casos, 221 checagens**, em quatro suites: coletor, verificador, portao de CI e
coerencia entre arquivos.

### O relatorio como dado

`.lgpd-scan/report.json` — a mesma auditoria em formato de maquina, com `schema`,
`repo`, `scope`, e uma entrada por requisito com status, severidade, confianca e
evidencia. `scripts/report_data.py` valida, resume e compara duas execucoes.

**Ele e escrito, nao extraido.** Um parser do markdown seria mais simples, e e o que
a primeira versao do verificador fazia com os cabecalhos: fragil, porque prosa muda.
Aqui o agente escreve os dois e o verificador confere que concordam — divergencia
entre eles e erro, porque sao dois registros da mesma auditoria e, discordando, nao
da para saber qual esta certo. As citacoes do JSON passam pela mesma checagem das do
markdown: arquivo existe, linha dentro dele, trecho aparece por ali.

Cinco regras do validador, cada uma por um motivo:

- **os 21 requisitos aparecem sempre** — omitir e diferente de responder `Nao se
  aplica`; o primeiro deixa o leitor sem saber se a pergunta foi feita;
- **`evidence` ou `absence`, nunca nenhum dos dois** — exigir citacao das duas
  empurraria para o pior resultado possivel, citar uma linha qualquer so para
  satisfazer o verificador;
- **toda evidencia carrega `snippet`** — o registro de maquina nao pode ter padrao de
  prova mais baixo que o documento que as pessoas leem;
- **lacuna exige severidade** — sem ela nao ha indice, e sem indice nao ha tendencia;
- **no R09 a evidencia vai mascarada** (`DB_PASS=***`) — o identificador sobrevive,
  que e o que torna a citacao conferivel, e o valor nao sai do codigo. O verificador
  agora procura credencial reproduzida tambem dentro do JSON, que e o arquivo que vai
  commitado sem ninguem reler.

**Nao existe nota de conformidade de 0 a 100, e isso e deliberado.** E o primeiro
pedido de todo mundo e seria o jeito mais rapido de destruir o que a ferramenta tenta
fazer: "78% em conformidade" e uma frase que alguem leva para uma reuniao, e nenhum
numero derivado de leitura de codigo sustenta aquela frase diante da ANPD. O que
existe e o `indice_de_pendencia` — soma ponderada das lacunas abertas, menor e melhor,
zero nao significa conformidade. Serve para ver tendencia, que e a pergunta legitima.

### Portao de integracao continua

`scripts/ci_check.py` grava uma `baseline.json` e, a cada PR, falha quando o que mudou
piora a situacao. Saida SARIF para a aba Security do GitHub, `action.yml` pronto e um
workflow de exemplo em `examples/github/`.

A decisao que mais mudou o resultado em teste foi a **granularidade por papel**:

| Papel | Observado por | Por que |
|---|---|---|
| risco | (sinal, arquivo) | credencial nova em outro arquivo e achado novo |
| controle | repositorio inteiro | rota de exclusao mudar de arquivo num refactor nao e regressao |
| inventario | contagem, sem reprovar | campo pessoal novo e o dia a dia de um produto que cresce |

Controle por arquivo transformaria toda reorganizacao de pastas em alarme alto, e um
portao que grita em refactor e desligado na primeira semana. O fixture
`05-refactor-move-controle` congela isso.

Sem baseline o portao **recusa rodar** em vez de inventar um ponto de partida: nao
existe "piorou" sem comparacao, e um check que reprova a PR que o instalou e
desinstalado na mesma tarde.

### Politica de privacidade gerada a partir do codigo

`references/artifacts/politica-privacidade.md`. Toda ferramenta desta area gera
politica a partir de questionario — o desenvolvedor responde "coletamos e-mail e
telefone" e sai um texto sem relacao com o sistema. E a mesma inversao que esta skill
existe para desfazer, produzida em vez de detectada.

Aqui a politica sai do inventario, entao nao pode omitir um campo que existe nem
inventar um que nao existe. E vale a regra que da nome ao artefato:

> **A politica so promete o que o codigo entrega.**

Sem rota de exclusao, a politica nao diz "voce pode excluir sua conta a qualquer
momento" — diz que a exclusao e feita mediante pedido ao encarregado, o que e
legitimo pela LGPD, e verdade, e e o que o sistema faz. Uma politica que promete um
botao que nao existe nao e um texto ruim: e a nao conformidade, documentada e
publicada pelo controlador, e e o achado que o R15 levanta depois.

`--kind politica` roda o coletor e recusa o documento quando ele promete automacao
sem lastro, com a frase citada. Promessa **mediada** ("solicite pelo canal do
encarregado") passa: a lei garante o direito, nao o botao.

A evidencia vai em anexo separado, porque politica e documento publico lido por
titular e `arquivo:linha` ali seria absurdo — alem de expor a estrutura interna sem
necessidade.

### Erros e limites encontrados testando

**A skill instalada dentro do projeto era auditada junto.** Rodando o portao na
propria pasta apareceram cinco sinais de risco que eram a ferramenta se lendo: a
documentacao de referencia cita `rejectUnauthorized: false` como exemplo do R08 e
`[E-MAIL]` como exemplo de marcador nao preenchido, e o coletor reportava os dois
como achados. Num projeto de usuario isso acontece assim que a skill e instalada em
`.claude/skills/` — ruido com cara de evidencia, que e o pior tipo. Agora as pastas
de configuracao de agente saem da varredura, e qualquer pasta com um `SKILL.md` que
se declare `lgpd-scan` e podada, o que cobre a copia clonada solta dentro do
repositorio. Auditar o repositorio da propria skill continua funcionando, que e o que
o dogfood faz. Fixture 20.

**`cid` nao era dado de saude.** O proprio template do relatorio usava `cid` como
exemplo de campo do art. 11, e o coletor nao o detectava — so `cid_10`. `cid` puro e
o nome mais comum de coluna de dado de saude em sistema brasileiro. A regra de dados
sensiveis nao tem fronteira a direita de proposito (os termos sao prefixos:
`religi`, `biometri`), entao `cid` precisou da sua, ou casaria `cidade` e `cidadao`.
Fixture 18. Entraram junto `psicolog`, `psiquiatr`, `sorologi`, `transfusao` e
`comorbidade`.

**O portao se repetia.** `age_self_declaration` estava na tabela de riscos e tambem
na leitura cruzada do ECA, e o mesmo arquivo saia duas vezes, uma como baixa e outra
como alta. Coletar idade nao e risco por si: o achado e coletar sem nada que
verifique, e isso e uma leitura de dois sinais, nao de um.

**Uma lacuna sem citacao nem sempre e um achado sem evidencia.** A categoria
ACHADOS SEM EVIDENCIA reprovava um requisito `Nao atendido` justificado por ausencia
("nenhuma coluna de consentimento em lugar nenhum") — que e o caso mais comum e nao
tem o que citar. Pior: a regra empurrava para citar uma linha qualquer so para passar
no verificador. Agora uma afirmacao de busca sem resultado sustenta a lacuna, e a
guarda continua pegando "isso precisa ser corrigido com urgencia", que nao sustenta
nada.

**A documentacao citava dois sinais que nunca existiram** — `ai_provider` e
`payment_gateway`, escritos por mim no indice dos artefatos. A nova suite de coerencia
confere que todo sinal citado na documentacao existe no coletor, que a tabela dos 21
requisitos em `report_data.py` bate com a de `requirements/index.md`, que a versao
concorda nos quatro arquivos onde ela aparece, e que o frontmatter do `SKILL.md` nao
tem chave fora do spec do agentskills.io.

E a primeira versao dessa checagem de sinais acusou quatro lugares certos para pegar
um errado (`deleted_at`, `opiniao_politica`, `responsavel_id` sao nome de coluna, nao
de sinal). Um teste que grita onde nao deve e um teste que alguem desliga.


## 0.4.0 — de doze para vinte e um requisitos, com suite de teste

Esta versão triplica o alcance da skill e, por isso, começa pelo que segura o
alcance: uma suite de fixtures. Ir de doze para vinte e um requisitos multiplica a
superfície de falso positivo junto com a cobertura, e um léxico é exatamente o tipo
de artefato que regride em silêncio — você alarga um padrão para pegar um campo real
e três sinais sem relação passam a disparar em outro lugar. A regra que passou a
valer: **nenhum requisito novo entra sem fixture.**

**32 casos, 137 checagens.** `python3 scripts/run_tests.py` roda as duas suites:
17 fixtures de coletor (cada um um repositório mínimo com o que deve e o que não deve
ser encontrado) e 15 casos de verificador (cada um um documento escrito com as
categorias que deve acusar). Quatro dos casos existem só para guardar falso positivo,
o que é metade do valor da suite.

### Vinte e um requisitos

| Grupo | Requisitos | Instrumento |
|---|---|---|
| base | R01–R12 | Lei 13.709/2018 |
| anpd | R13–R17 | Res. CD/ANPD nº 15, 18 e 19/2024, e art. 12 |
| eca | R18–R21 | ECA Digital, Lei 15.211/2025 |

**R13 a R17** — registro de incidente (art. 10 da Res. 15/2024, mínimo de cinco
anos), comunicação no prazo de três dias úteis (em dobro para agente de pequeno
porte), encarregado e canal do titular, salvaguarda de transferência internacional
(Res. 19/2024) e anonimização versus pseudonimização (art. 12). Oito sinais novos.

**R18 a R21** — ECA Digital, em vigor desde 17 de março de 2026. Verificação de idade
**sem autodeclaração** (a lei veda expressamente), vinculação a responsável legal,
configuração padrão mais protetiva e proibição de perfilamento publicitário
direcionado a menores. Sete sinais novos.

Este grupo inverte o sinal de leitura do resto da auditoria, e é o que o torna
interessante: em geral encontrar um campo é neutro e a ausência é o achado; aqui,
encontrar um campo de data de nascimento ou uma caixa "confirmo que tenho 18 anos"
**sem** nada que verifique é a evidência direta de não conformidade. O controle que o
projeto acha que tem é justamente o que a lei recusa. O par `age_self_declaration` ×
`age_verification_provider` existe para distinguir os quatro casos possíveis.

Antes de avaliar o grupo, decide-se se ele se aplica: numa ferramenta interna B2B os
quatro saem como `Não se aplica` com a razão escrita, e dizer isso é melhor que o
silêncio — o leitor precisa saber que a pergunta foi feita.

### Três artefatos gerados, e a regra que os torna diferentes

`references/artifacts/` traz ROPA (art. 37), RIPD (art. 38) e minuta de cláusulas com
operador (arts. 39 e 46).

**O artefato passa pelo verificador.** Gerar um ROPA é o que toda ferramenta desta
área faz. Gerar um ROPA cujas afirmações apontam para linhas de código que existem é
a diferença, e é o que esta versão implementa: o `verify_report.py` conhece os quatro
documentos e aplica a checagem que cabe a cada um.

| Documento | O que é conferido além das citações |
|---|---|
| relatório | achado `Parcial` ou `Não atendido` que não cita nada |
| ROPA | cada linha da tabela de operações e do inventário |
| RIPD | cada bloco `RISCO nn` |
| DPA | os Anexos I e II, que são a única parte levantada do código |

A regra das linhas de tabela é a que carrega o peso: **ou a linha cita evidência, ou
declara que não há.** Uma linha que afirma uma operação de tratamento sem citar nada
e sem admitir nada é uma linha escrita de memória — e num documento que o controlador
assina, é o risco inteiro.

Duas categorias novas, nos dois casos por simetria com o que a própria ferramenta
reporta:

- **MARCADOR NÃO PREENCHIDO** — o documento saiu com `[INSERIR NOME]` ou
  `{nome do projeto}` dentro. É exatamente a falha que a skill reporta como R15, a
  política que manda o titular procurar um canal que ninguém preencheu. Fazer isso na
  própria saída não é opção. Para o que depende do controlador existe a marca visível
  `⚠ A PREENCHER PELO CONTROLADOR`, que não é marcador de modelo e não é acusada.
- **DOCUMENTO SEM LASTRO NO CÓDIGO** — menos citações do que o tipo de documento
  exige. Um ROPA sem nenhum rastro foi escrito de memória, diga o cabeçalho o que
  disser.

O que o código não mostra vai **marcado, não preenchido**. Um ROPA com a base legal
chutada é pior que um ROPA com a lacuna visível: o primeiro será assinado como se
fosse verdade.

### Supressão de falso positivo pelo próprio projeto

Duas anotações, documentadas em `references/annotations.md`:

```ts
const nome = gerarApelido();  // lgpd-scan: ignorar personal_data_field — apelido publico, nao identifica
@Column() cid: string;        // @lgpd: classificacao=sensivel base_legal=art11_ii retencao=20anos
```

Três decisões de desenho que valem registro. **O motivo é obrigatório**: supressão sem
razão escrita é rejeitada e aparece no relatório como rejeitada, com a instrução do que
fazer — uma marca que silencia sem explicar transfere o problema para o próximo leitor.
**Nada desaparece em silêncio**: achado suprimido vai para seção própria do relatório,
com a razão do desenvolvedor, porque a alternativa é uma auditoria que o auditado pode
esvaziar sem deixar rastro. E **nome de sinal desconhecido é rejeitado**, senão um erro
de digitação suprime nada e parece ter funcionado.

### Continuação, e onde a auditoria parou

O coletor passa a escrever `<repo>/.lgpd-scan/STATUS.md` com os sinais presentes e
ausentes, as anotações lidas e os checkpoints da auditoria. Uma auditoria de vinte e
um requisitos não cabe numa sessão, e sem isso a segunda sessão recomeça do zero.

### Documentação dividida por grupo

`references/requirements.md` virou `references/requirements/` com `index.md` mais um
arquivo por grupo. Os vinte e um requisitos juntos não cabem de modo útil em contexto,
e ler um grupo que você não vai julgar custa atenção que o código precisa.

### Instaladores

`install.sh` (POSIX sh: macOS, Linux, WSL, Git Bash) e `install.ps1` (Windows
PowerShell 5.1 e PowerShell 7). Detectam os agentes presentes, aceitam `--agent`,
`--scope user`, `--dest`, `--dry-run` e `--uninstall`, são idempotentes por marcador
delimitado, e o desinstalar apaga o arquivo que o instalador criou se ele ficar vazio.

E uma honestidade que os dois dizem na primeira tela: **só o Claude Code tem mecanismo
nativo de skill.** Para Codex, Gemini CLI, Cursor e OpenCode o que se instala é a
pasta da skill mais um ponteiro no arquivo de contexto que aquele agente já lê. Funciona
— o agente lê o `SKILL.md` e segue —, mas não é a mesma coisa, e um instalador que
finge o contrário só consegue decepcionar na primeira vez que alguém olha.

O frontmatter do `SKILL.md` passou a conformar com a especificação estrita do
agentskills.io: só `name`, `description`, `license` e `metadata`, porque chave fora da
lista é erro no empacotamento. `compatibility` ficou de fora de propósito — o formato
dela não está documentado, e chutar o formato de uma chave de validação é como se
introduz o erro que só aparece no dia da publicação.

### Erros encontrados testando, não lendo

Esta é a seção que justifica a suite existir. Todos foram encontrados rodando contra
prosa portuguesa real ou contra documento real, nenhum lendo o código da skill.

**O pior erro da versão: relatório limpo porque nada foi lido.** Encontrado rodando a
suíte de dentro da pasta onde a skill mora, que é um repositório git que ignora aquela
pasta. A listagem sai do `git ls-files --cached --others --exclude-standard`, e num
caminho que o `.gitignore` de um repositório acima exclui isso devolve **zero
arquivo**. O coletor não leu nada, não achou nada, e o relatório sairia dizendo que
está tudo bem — que é o resultado mais perigoso que uma ferramenta de conformidade
pode produzir, porque ninguém desconfia de boa notícia. Vale para qualquer pasta
ignorada por um repositório de cima: skill instalada em `.claude/skills/`, subprojeto
ignorado, pasta de entrega.

Agora o coletor confere a listagem em vez de confiar nela: conta os arquivos de texto
no disco e compara. Zero pelo git com arquivos no disco derruba para a varredura de
diretório, com aviso alto no terminal e no `STATUS.md`. Mais da metade da árvore
escondida pelo `.gitignore` gera aviso sem derrubar — pode ser legítimo, e pode ser
código fora da auditoria. O fixture 17 congela o caso.

**`\b` não dispara antes de `_`, de novo.** `vinculo_responsavel_em` não casava com
`\bvinculo_responsavel\b` porque `_` é caractere de palavra. Já tinha acontecido na
0.3.0 com `data_nascimento`; desta vez a correção foi generalizada — `IDENTIFIER_SIGNALS`
aplica as fronteiras `LB`/`RB` e o corte de camelCase a todos os sinais que leem nome de
identificador, em vez de consertar um regex.

**`todo` é uma das palavras mais comuns do português.** O padrão `\bTODO\b` rodava
case-insensitive, e "Todo titular tem direito de acesso" numa política de privacidade
legítima virava marcador não preenchido. Terceira aparição da mesma família de erro,
depois de `unico` casando "único parágrafo" como provedor de verificação de idade e de
`responsavel` casando "responsável pelas decisões" como vínculo parental. `TODO`,
`FIXME` e `XXXX` agora só contam em caixa alta.

**`politica.html` não era texto legal.** O bucket `legal` conhecia `privacidade` e
`termos`, mas não um arquivo chamado só `politica.html` — que é a política de
privacidade em metade dos projetos brasileiros. Sem o bucket, os achados dele entravam
sem `declaration_only`, isto é, **a promessa era creditada como implementação**, que é
o erro mais grave que esta ferramenta pode cometer. Corrigido, com o cuidado de aceitar
só extensão de documento: `politica.ts` costuma ser regra de autorização, que é código
de verdade.

**Alargar o bucket legal quase criou um falso positivo em escala.** Com
`politica*.html` dentro, toda política escrita em Angular, Vue ou Handlebars passaria a
ter suas interpolações `{{ versao }}` lidas como buraco de modelo. Chaves duplas agora
só contam com vocabulário de preenchimento. O fixture 16 congela uma política Angular
real, com interpolação, pipe e binding `[class.active]`.

**A ferramenta ia se auditar de novo, por um caminho novo.** `RELATORIO-LGPD.md` já
estava fora da varredura desde a 0.3.0, mas `ROPA.md`, `RIPD.md` e `DPA-MINUTA*.md`
caem no bucket `legal` pelo nome — na execução seguinte o tool leria o próprio ROPA
como se fosse a política do projeto, creditando o próprio documento como declaração e
acusando as próprias marcas de pendência como R15.

**Trecho conferido por qualquer token era fraco onde importava.** Uma afirmação como
`argon2.hash(dto.senha)` contra uma linha que diz `bcrypt.hash(dto.senha, 10)` passava,
porque três dos quatro tokens estavam lá. A única palavra que carregava a afirmação —
e que estava errada — era a que não batia. Agora o token mais longo do trecho precisa
aparecer. Medido antes de adotar: nos dois documentos reais disponíveis produziu
exatamente os mesmos avisos que a regra anterior, e pegou a mutação.

**Linha de tabela destacada por linha em branco passava sem conferência.** A checagem
rastreava "já passei do separador?" e uma linha em branco no meio da seção resetava o
estado, então uma linha solta — exatamente o que um documento editado à mão produz —
era lida como cabeçalho de tabela nova e pulada. Agora o cabeçalho é reconhecido pela
estrutura: é a linha seguida do separador tracejado.

**`is_noise_line` escondia evidência legítima.** `export class SecurityIncident` era
tratado como ruído de import, e o `incident_register` perdia o registro de incidente
que estava ali.

**Padrão com acento nunca casa.** Depois que o coletor passou a dobrar acentos do
texto lido, qualquer padrão acentuado ficou impossível de casar — e eu mesmo introduzi
um ("não audite", em `suspicious_instruction`). Agora existe uma asserção em tempo de
import que recusa carregar o módulo se algum padrão tiver caractere não-ASCII.

**O plano de ação era acusado de ser o ataque.** `suspicious_instruction` marcava o
documento de planejamento do projeto auditado, que *descrevia* a mitigação de prompt
injection. Acusar a vítima de ser o atacante gasta a confiança do leitor rápido; o
sinal passou a rodar só em arquivo de código.


## 0.3.0 — correções da primeira execução real

Tudo nesta versão saiu de uma auditoria de verdade, num projeto NestJS + Angular de
90 arquivos. Nenhum item foi encontrado lendo o código da própria skill.

### O verificador aprovava citação inventada

Das 62 citações do relatório piloto, **duas apontavam para a linha errada** e o
`verify_report.py` aprovou as duas. Uma apontava para `const marginY = 50;`
afirmando ser onde o prompt é montado; a outra, para uma linha em branco. A checagem
só sabia confirmar que a linha existe.

- Linha vazia ou só com pontuação agora é **erro**, não aprovação.
- Nova categoria **CITAÇÕES SEM TRECHO**: lista as citações que não trouxeram um
  trecho entre crases ao lado e que, por isso, nenhuma checagem alcança. No relatório
  piloto eram 49 de 64 — ou seja, três em cada quatro afirmações passavam sem
  conferência de conteúdo.
- O template agora exige o trecho literal junto de cada citação.
- `--strict` passa a falhar também nessas.

### O verificador reclamava do que estava certo

A checagem de trecho pareava todo código entre crases da linha com toda citação da
linha, o que enchia de alarme falso qualquer linha de tabela ou frase com duas
citações.

- Uma citação só é confrontada com os trechos do seu próprio escopo: entre as
  citações vizinhas, dentro da sua célula quando é tabela, e dentro da sua frase.
- Basta **um** trecho corroborar, em vez de todos.

### Falso negativo num requisito inteiro

O `pii_in_log` não achava nada porque casava linha a linha, e uma chamada de logger
quase sempre se espalha por duas — `this.logger.error(` numa, o e-mail interpolado na
seguinte. O achado real do R10 estava lá e passou batido. Agora usa janela.

### Detecção de stack falhava no layout mais comum que existe

Um repositório com `api/` e `client/`, cada um com seu `package.json`, reportava
"stack não identificada" — e as notas de NestJS e TypeORM nunca eram carregadas. Os
manifestos passam a ser procurados até três níveis abaixo da raiz.

### O terceiro que importava passava batido

O `third_party_sdk` não conhecia `@google/generative-ai`, o único terceiro que
recebia dado no projeto auditado, enquanto marcava "Firebase" dentro de um comentário
de scaffolding. Agora cobre provedores de IA, pagamento e e-mail, ignora comentários,
e só roda em código ou manifesto de dependência — nunca em prosa.

### Ruído do léxico

- `sensitive_data_field` casava com **política** de privacidade por causa de
  `politic`, de opinião política: 10 das 12 ocorrências eram isso. Agora exige o
  sentido político (`opiniao_politica`, `filiacao_partidaria`).
- `@Controller('health')` virava dado de saúde.
- `hardcoded_secret` marcava anotação de tipo (`senha: string;`), referência de
  configuração (`process.env.DB_PASS`) e chamada de função (`getToken()`). E não
  marcava `DB_PASS=` — a alternância tinha `password` e `passwd`, nunca `pass`.
- Ocorrência em `.env.example` agora vem com `example_file: true`, para o relatório
  não tratar template e configuração real com a mesma gravidade.
- `retention_marker` casava com o `ttl` do rate limiter.
- Sinais de implementação (consentimento, auditoria, hash, cifra) deixaram de rodar
  em `.md`: documento de planejamento discute, não implementa.

### A ferramenta se auditava

`RELATORIO-LGPD.md` e `.lgpd-scan/` entravam na varredura seguinte, e o relatório
gerava achados que citavam o relatório anterior.

### Outros

- Teto por ocorrência deixou de marcar o sinal como truncado — "truncado" agora
  significa só que a cota do sinal acabou.
- Cota maior para os sinais de léxico: o inventário do R01 precisa de abrangência, e
  40 ocorrências cortavam justamente o que ele deve enumerar.
- Nova seção **Comece por aqui** no relatório, com os três primeiros passos. Surgiu
  escrevendo o relatório piloto: 2.600 palavras sem porta de entrada é uma parede.

## 0.2.0

- Correção de recall: DTOs, forms e serializers não caíam em bucket nenhum, então um
  `create-user.dto.ts` com cpf, nome e dataNascimento era invisível.
- `verify_report.py`: confere as citações do relatório contra os arquivos.
- Listagem via `git ls-files` (respeita `.gitignore`) e marca cada ocorrência como
  versionada ou não, que é o que decide a gravidade de segredo no repositório.

## 0.1.0

- Primeira versão: coletor, 12 requisitos, notas de Node e Spring, template do
  relatório.
