# DPA — Minuta de cláusulas de tratamento com operador

**Arts. 39, 42 a 45 e 46 da Lei 13.709/2018.** O operador deve realizar o tratamento
segundo as instruções do controlador, que verificará a observância. Responsabilidade
solidária nos termos dos arts. 42 a 45, e segurança pelo art. 46.

Escreva em `<repo>/DPA-MINUTA.md`. As regras comuns aos três artefatos estão em
`index.md`.

Leia isto antes de gerar: **este é o artefato de menor valor dos três, e o de maior
risco de uso indevido.** Um contrato é negociado entre duas partes com assessoria
jurídica; uma minuta gerada por ferramenta é ponto de partida para essa conversa, e
nada além. O que a skill acrescenta de real é o Anexo I e o Anexo II — as atividades
e as medidas técnicas levantadas do código —, porque é justamente o que costuma vir
em branco ou genérico. O corpo das cláusulas é modelo.

Diga isso no documento, em vez de entregar algo que pareça pronto para assinatura.
Uma minuta apresentada como contrato é pior que nenhuma minuta.

---

## Quando gerar

Quando o R12 encontrou terceiro tratando dado pessoal: provedor de IA, gateway de
pagamento, serviço de e-mail, armazenamento em nuvem, SDK de analytics. Um por
operador — as cláusulas mudam com o que o operador faz, e uma minuta única para cinco
fornecedores não serve para nenhum.

Se o R12 não encontrou nada, não gere: a minuta sem operador identificado é um
documento sem contraparte.

---

## Estrutura

````markdown
# Minuta de cláusulas de tratamento de dados pessoais

> **Minuta para revisão jurídica.** Documento gerado por ferramenta a partir da
> leitura do código-fonte, não revisado por advogado, não negociado com a
> contraparte. O corpo das cláusulas é modelo; os Anexos I e II foram levantados do
> repositório e trazem a evidência de cada item. Não assine sem revisão.

| | |
|---|---|
| **Controlador** | ⚠ A PREENCHER — razão social e CNPJ |
| **Operador** | {terceiro identificado no código, com citação} |
| **Objeto no sistema** | `{repositório}` · commit `{git.commit}` |
| **Data da minuta** | {DD/MM/AAAA} |

## 1. Definições e papéis

As partes reconhecem que, para os fins do art. 5º, VI e VII, o CONTROLADOR decide
sobre o tratamento e o OPERADOR o realiza em seu nome, conforme as instruções
documentadas no Anexo I.

⚠ A PREENCHER — a qualificação pode ser outra: dois controladores independentes, ou
operação conjunta. Quem define é a assessoria jurídica, olhando o contrato real, não
a ferramenta olhando o código.

## 2. Objeto, duração, natureza e finalidade

Conforme o Anexo I, que integra este instrumento.

## 3. Obrigações do operador

O OPERADOR compromete-se a:

a) tratar os dados pessoais exclusivamente conforme as instruções do CONTROLADOR,
comunicando-o imediatamente caso entenda que uma instrução viola a legislação
(art. 39);

b) manter os dados em sigilo, estendendo o dever a empregados e prepostos;

c) adotar as medidas de segurança do art. 46, no mínimo as do Anexo II;

d) não subcontratar suboperador sem autorização prévia e escrita do CONTROLADOR,
mantendo atualizada a relação do Anexo III e respondendo pelos atos do subcontratado;

e) auxiliar o CONTROLADOR no atendimento aos direitos do titular (art. 18) nos prazos
que permitam ao CONTROLADOR responder no prazo legal;

f) comunicar ao CONTROLADOR qualquer incidente de segurança **sem demora e em no
máximo 24 (vinte e quatro) horas** do conhecimento, com as informações do art. 6º da
Res. CD/ANPD nº 15/2024, de modo a viabilizar a comunicação do CONTROLADOR à ANPD e
aos titulares no prazo de 3 (três) dias úteis;

g) ao término do tratamento, eliminar os dados pessoais e as cópias existentes, salvo
as hipóteses do art. 16, comprovando a eliminação;

h) manter registro das operações que realizar (art. 37) e disponibilizá-lo ao
CONTROLADOR quando solicitado;

i) permitir e colaborar com auditoria ou demonstração documental da conformidade,
sem prejuízo do sigilo de terceiros.

## 4. Transferência internacional

O OPERADOR somente transferirá dados pessoais para fora do território nacional com
fundamento em uma das hipóteses do art. 33 e observadas as salvaguardas da
Res. CD/ANPD nº 19/2024, informando previamente o país de destino.

⚠ A PREENCHER — hipótese e instrumento aplicáveis. O código mostra o destino;
o fundamento é contratual.

Destinos identificados no repositório: {lista com evidência, ou "nenhum identificado"}

## 5. Responsabilidade

Nos termos dos arts. 42 a 45. ⚠ A PREENCHER — limitação de responsabilidade,
regresso e garantias são negociação entre as partes.

## 6. Vigência e disposições finais

⚠ A PREENCHER — prazo, foro, rescisão, comunicações.

---

## Anexo I — Atividades de tratamento pelo operador

Levantado do código-fonte.

| Item | Conteúdo | Evidência |
|---|---|---|
| Operador | Google (Gemini API) | `src/ai/ai.service.ts:41` — `new GoogleGenerativeAI(` |
| Natureza do tratamento | Envio de conteúdo do titular para geração de texto | `src/ai/ai.service.ts:58` — `await model.generateContent(` |
| Categorias de dados | Conteúdo submetido pelo titular; identificador de usuário | `src/ai/ai.service.ts:52` — `prompt` |
| Categorias de titulares | Usuários cadastrados | `src/users/user.entity.ts:14` — `export class Usuario` |
| Finalidade | ⚠ A PREENCHER PELO CONTROLADOR |
| Duração | ⚠ A PREENCHER — vigência contratual |
| Retenção pelo operador | ⚠ Não verificável em código — depende dos termos do fornecedor |

## Anexo II — Medidas técnicas de segurança

Do lado do controlador, o que o código mostra. Do lado do operador, o que o contrato
tem de exigir — e o código não sabe.

| Medida | No controlador | Evidência | Exigida do operador |
|---|---|---|---|
| Cifragem em trânsito | Implementada | `src/main.ts:18` — `app.use(helmet())` | Sim |
| Hash de senha | Implementada — bcrypt | `src/auth/auth.service.ts:34` — `await bcrypt.hash(senha, 10)` | N/A |
| Segredos fora do código | **Falha** | `docker-compose.yml:9` — credencial em arquivo rastreado | Sim |
| Registro de incidente | Ausente | Nenhuma entidade de incidente no repositório | Sim |
| Minimização em log | **Falha** | `src/users/users.service.ts:52` — `this.logger.log(` | Sim |

Uma falha do lado do controlador não é motivo para omitir a linha: é o que dá ao
leitor a lista do que precisa ser corrigido antes de a cláusula fazer sentido.

## Anexo III — Suboperadores autorizados

| Suboperador | Serviço | País | Evidência |
|---|---|---|---|
| {do código, quando houver} | | | |

⚠ A PREENCHER — a relação completa é do operador; o repositório só mostra o que esta
aplicação chama diretamente.

---

Documento gerado por ferramenta a partir do código-fonte, para revisão humana e
jurídica. Não constitui parecer jurídico, não foi negociado entre as partes e não
deve ser assinado como está.
````

---

## Regras específicas deste artefato

**As 24 horas da cláusula 3(f) não estão na lei — e é por isso que precisam estar no
contrato.** O prazo legal é de três dias úteis para o controlador comunicar a ANPD
(Res. 15/2024, art. 6º; em dobro para agente de pequeno porte). Se o operador avisa
no terceiro dia, o controlador já perdeu o prazo. A cláusula existe para dar folga
ao prazo de quem responde, e vale explicar isso ao desenvolvedor em uma linha em vez
de deixar parecer uma exigência inventada.

**Não gere cláusula que o código não sustenta.** A tentação é encher a minuta de
cláusulas de auditoria, certificação e SLA. Cada uma delas é negociação; nenhuma vem
do repositório. A minuta é curta de propósito.

**Os anexos são o produto.** Se você gerar este documento e os Anexos I e II vierem
genéricos, não gere: o corpo de cláusulas modelo está disponível em qualquer lugar, e
entregar só ele com o nome da ferramenta em cima é emprestar credibilidade técnica a
um texto que não tem nenhuma.

**Um operador por documento.** `DPA-MINUTA-google.md`, `DPA-MINUTA-stripe.md`. O
Anexo I descreve um tratamento concreto, e tratamento concreto não é plural.
