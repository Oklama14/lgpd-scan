# RIPD — Relatório de Impacto à Proteção de Dados Pessoais

**Art. 38 da Lei 13.709/2018.** A ANPD pode determinar ao controlador que elabore
relatório de impacto, inclusive de dados sensíveis, referente às suas operações de
tratamento. O art. 5º, XVII define o conteúdo: descrição dos tipos de dado, a
metodologia de coleta e de garantia da segurança, e a análise do controlador quanto a
medidas, salvaguardas e mecanismos de mitigação de risco.

Escreva em `<repo>/RIPD.md`. As regras comuns aos três artefatos estão em `index.md`.

Este é o artefato mais difícil de gerar com honestidade, porque a maior parte dele é
análise de risco — e o código não avalia risco, ele mostra controles. O que se pode
fazer bem é o inverso do que as ferramentas costumam fazer: preencher com precisão a
parte dos controles, e deixar a avaliação visivelmente pendente em vez de gerar
parágrafos de risco genérico que ninguém leu.

---

## Antes de escrever: o RIPD é exigível aqui?

Não há lista fechada na lei. Os gatilhos de risco elevado que a prática consolidou, e
que dão para checar no código:

| Gatilho | Sinal |
|---|---|
| Dado sensível em escala | Campos do art. 11 no inventário (R02) |
| Titular menor de idade | `minor_flag`, `parental_link`, produto de consumo (R18–R21) |
| Decisão automatizada ou perfilamento | `ad_targeting`, scoring, provedor de IA sobre dado pessoal |
| Monitoramento em larga escala | Geolocalização, rastreamento, telemetria por usuário |
| Transferência internacional sem decisão de adequação | `cloud_region`, host de API fora do país (R16) |
| Tecnologia nova aplicada a dado pessoal | Provedor de IA recebendo conteúdo do titular |

Se nenhum gatilho aparece, diga isso: um RIPD que conclui "risco baixo, sem gatilho
identificado" em meia página é um documento melhor que um de trinta páginas escrito
por precaução. Se o pedido veio da ANPD, o relatório é obrigatório de todo modo, e o
escopo é o que ela pediu.

---

## Estrutura

````markdown
# Relatório de Impacto à Proteção de Dados Pessoais (RIPD)

| | |
|---|---|
| **Controlador** | ⚠ A PREENCHER PELO CONTROLADOR |
| **Encarregado (DPO)** | {contato com citação, ou marca de pendência} |
| **Sistema** | `{repositório}` · commit `{git.commit}` |
| **Data** | {DD/MM/AAAA} · **Versão** | 1.0 |
| **Motivo da elaboração** | {gatilho identificado, ou determinação da ANPD} |
| **Origem** | Levantado do código-fonte por lgpd-scan {tool_version} · revisão humana obrigatória |

## 1. Descrição do tratamento

**Natureza.** {O que o sistema faz com dado pessoal, em dois parágrafos de prosa.
Sem lista — esta seção é lida por quem não abriu o código.}

**Escopo.** {Quais dados, de quantas categorias de titular, por quais operações.
Remeta ao ROPA quando ele existir, em vez de repeti-lo.}

**Contexto.** {Relação com o titular — cliente, usuário gratuito, menor —, e se o
titular tem escolha real sobre o tratamento.}

**Finalidades.** {Uma linha por finalidade. Finalidade não deduzível do código entra
marcada.}

## 2. Tipos de dado tratados

| Categoria | Campos | Sensível (art. 11) | Evidência |
|---|---|---|---|
| Identificação | nome, e-mail | Não | `src/users/user.entity.ts:20` — `@Column() email: string` |
| Autenticação | senha | Não — mas risco alto se exposta | `src/users/user.entity.ts:26` — `@Column() senha: string` |

## 3. Metodologia de coleta

| Ponto de coleta | Como | Dado coletado | Evidência |
|---|---|---|---|
| Formulário de cadastro | `POST /auth/register` | Nome, e-mail, senha | `src/auth/auth.controller.ts:18` — `@Post('register')` |
| Upload de documento | multipart | Conteúdo do arquivo | `src/files/files.controller.ts:22` — `@UseInterceptors(FileInterceptor` |

## 4. Medidas de segurança e salvaguardas

Art. 5º, XVII pede a metodologia de garantia da segurança. Aqui o código responde
bem, então esta é a seção com mais substância — e cada linha carrega evidência.

| Medida | Estado | Evidência |
|---|---|---|
| Hash de senha | Implementada — bcrypt | `src/auth/auth.service.ts:34` — `await bcrypt.hash(senha, 10)` |
| Segredo fora do repositório | **Falha** — credencial versionada | `docker-compose.yml:9` — credencial de banco em arquivo rastreado |
| Minimização em log | **Falha** — e-mail em log de aplicação | `src/users/users.service.ts:52` — `this.logger.log(` |

## 5. Riscos identificados

Um risco por subseção. Probabilidade e impacto são **avaliação**, não apuração: se
não há base para estimar, escreva `A avaliar pelo controlador` em vez de um número
inventado.

### RISCO 01 — Credencial de banco exposta no repositório

**Descrição.** {O que pode acontecer com o titular, não com o sistema. "Acesso
indevido à base inteira de titulares" é o risco; "vazamento de senha" é o meio.}

**Titulares afetados.** {Categoria e ordem de grandeza, se o código permitir dizer.}

**Evidência.** `docker-compose.yml:9` — credencial de banco em arquivo rastreado pelo git

**Probabilidade.** Alta — o arquivo está no histórico e permanece válido após a remoção

**Impacto.** Alto — acesso irrestrito a todos os dados pessoais da base

**Medida de mitigação.** Rotacionar a credencial, mover para variável de ambiente,
limpar o histórico. A remoção do arquivo sem rotação não mitiga nada.

**Risco residual.** ⚠ A avaliar pelo controlador após a mitigação

## 6. Direitos dos titulares

| Direito (art. 18) | Implementado | Evidência |
|---|---|---|
| Acesso / portabilidade | Sim | `src/users/users.controller.ts:41` — `@Get('me/export')` |
| Eliminação | Não | Nenhuma rota de exclusão de conta no repositório |
| Correção | Parcial | `src/users/users.controller.ts:33` — `@Patch('me')` — não cobre todos os campos |

## 7. Consulta a titulares ou representantes

⚠ A PREENCHER PELO CONTROLADOR — o art. 38 não exige, mas a consulta, quando houve,
é o que sustenta a análise de proporcionalidade. Não verificável em código.

## 8. Conclusão

{Dois parágrafos: os riscos que precisam de decisão antes de continuar, e os que
podem ser tratados no curso normal. Se a conclusão depende de informação que não
está no código, diga de qual.}

| | |
|---|---|
| **Elaborado por** | lgpd-scan {tool_version}, a partir do código-fonte |
| **Revisado por** | ⚠ A PREENCHER — encarregado |
| **Aprovado por** | ⚠ A PREENCHER — controlador |
| **Data da revisão** | ⚠ A PREENCHER |

## 9. Limitações

Este relatório foi levantado do código-fonte e mostra os controles **implementados**.
A avaliação de risco, a proporcionalidade do tratamento e a decisão sobre risco
residual são do controlador e do encarregado — nenhuma delas está no repositório, e
as marcas de pendência acima não são omissão, são o limite honesto da apuração.

Não constitui atestado de conformidade nem parecer jurídico.
````

---

## Como não estragar este documento

**Risco é sobre o titular.** "Indisponibilidade do serviço" é risco de negócio e não
pertence a um RIPD. "Acesso indevido ao histórico de saúde de cem mil pacientes" é
risco ao titular. Toda vez que a frase do risco tiver o sistema como sujeito,
reescreva com o titular.

**Não gere probabilidade e impacto.** É a tentação central deste artefato: a tabela
pede dois valores, e inventá-los custa duas palavras. Um "Média/Média" sem base
transforma um relatório de impacto em teatro — e, pior, num teatro que alguém vai
assinar. Probabilidade só sai do código quando o próprio código a determina: uma
credencial em arquivo rastreado tem probabilidade alta porque o histórico do git é
público para quem tem acesso ao repositório, e isso é fato, não estimativa.

**Um risco real vale mais que oito genéricos.** "Ausência de política de senha forte"
copiado de um modelo, sem citação, enfraquece os riscos que você apurou de verdade:
o leitor que descobre um item genérico passa a duvidar dos outros. Só entra risco com
evidência; o resto vai para a seção 9, dito como suspeita não confirmada.

**Remeta ao ROPA, não o copie.** Se o ROPA existe, a seção 2 pode ser uma referência
de uma linha. Dois documentos que repetem o inventário divergem na primeira
atualização, e aí nenhum dos dois é confiável.
