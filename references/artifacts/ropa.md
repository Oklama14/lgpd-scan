# ROPA — Registro das operações de tratamento

**Art. 37 da Lei 13.709/2018.** O controlador e o operador devem manter registro das
operações de tratamento que realizarem. Não é um documento opcional nem um entregável
de projeto: é obrigação permanente, e a ANPD pode pedi-lo.

Escreva em `<repo>/ROPA.md`. As regras comuns aos três artefatos estão em `index.md` —
leia antes.

Este é o artefato mais barato de gerar e o mais útil, porque o inventário do R01 já
é um ROPA mal formatado. Se a auditoria foi feita, isto é um passo de formatação, não
de descoberta.

---

## Estrutura

````markdown
# Registro das Operações de Tratamento de Dados Pessoais (ROPA)

| | |
|---|---|
| **Controlador** | ⚠ A PREENCHER PELO CONTROLADOR — razão social e CNPJ |
| **Encarregado (DPO)** | {contato encontrado, com citação, ou a marca de pendência} |
| **Sistema** | `{nome do repositório}` |
| **Commit** | `{git.commit}` |
| **Data do levantamento** | {DD/MM/AAAA} |
| **Origem** | Levantado do código-fonte por lgpd-scan {tool_version} · revisão humana obrigatória |

## 1. Operações de tratamento

Uma linha por operação. Operação é um verbo com finalidade — "cadastro de usuário",
"emissão de relatório", "envio de e-mail transacional" — não uma tabela.

| # | Operação | Finalidade | Base legal (art. 7º/11) | Categorias de titulares | Categorias de dados | Dados sensíveis | Retenção | Evidência |
|---|---|---|---|---|---|---|---|---|
| OP01 | Cadastro e autenticação de usuário | Permitir o acesso à plataforma | ⚠ A PREENCHER — provável art. 7º, V (execução de contrato) | Usuários cadastrados | Nome, e-mail, senha (hash) | Não | ⚠ Não verificável em código | `src/users/user.entity.ts:20` — `@Column() email: string` |
| OP02 | Geração de relatório por IA | Produzir o relatório contratado | ⚠ A PREENCHER | Usuários cadastrados | Conteúdo submetido pelo titular | Verificar | ⚠ Não verificável | `src/ai/ai.service.ts:41` — `new GoogleGenerativeAI(` |

## 2. Dados pessoais por entidade

| Entidade / tabela | Campo | Natureza | Onde |
|---|---|---|---|
| `usuarios` | `email` | Dado pessoal | `src/users/user.entity.ts:20` — `@Column() email: string` |
| `pacientes` | `cid` | **Sensível** — saúde (art. 11) | `db/migration/V3__pac.sql:14` — `cid varchar(10)` |

## 3. Compartilhamento e operadores

| Destinatário | O que recebe | Finalidade | País / região | Salvaguarda (Res. 19/2024) | Evidência |
|---|---|---|---|---|---|
| Google (Gemini API) | Conteúdo submetido para geração | Processamento do relatório | EUA | ⚠ A PREENCHER — pendência documental | `src/ai/ai.service.ts:41` — `new GoogleGenerativeAI(` |
| {provedor de e-mail} | E-mail do titular | Envio transacional | | ⚠ A PREENCHER | |

Terceiro que aparece no código mas cuja finalidade não é dedutível entra com a
finalidade marcada, não com um palpite.

## 4. Medidas de segurança implementadas

Só o que está no código, cada uma com evidência. As organizacionais vão na seção 6.

| Medida | Estado | Evidência |
|---|---|---|
| Senha com hash forte | Implementada | `src/auth/auth.service.ts:34` — `await bcrypt.hash(senha, 10)` |
| Transporte cifrado (TLS) | ⚠ Não verificável no repositório | — |
| Controle de acesso por papel | Ausente | Nenhum guard de papel nas rotas de `src/users/` |
| Registro de incidente (art. 10, Res. 15/2024) | Ausente | Nenhuma entidade, migration ou serviço de incidente |

## 5. Retenção e eliminação

| Dado / entidade | Prazo | Gatilho de eliminação | Evidência |
|---|---|---|---|
| `usuarios` | ⚠ A PREENCHER — indefinido no código | Nenhum | Nenhuma coluna de expurgo nem rotina agendada |

Retenção indefinida é achado, não lacuna de documento: registre-a assim, com estas
palavras, porque é o que o art. 15 alcança.

## 6. O que este registro não apura

Este ROPA foi levantado do código-fonte. Ele mostra o tratamento **implementado**.
Ficam fora do alcance da leitura de código, e continuam obrigatórios:

- a base legal de cada operação, que é decisão do controlador e não está no código
- contratos com operadores e suboperadores, e as salvaguardas de transferência
- prazos de retenção definidos por obrigação legal ou contratual
- medidas organizacionais: treinamento, política interna, segurança física
- tratamento que aconteça fora deste repositório — planilha, sistema legado, exportação manual

Documento gerado por ferramenta a partir do código-fonte, para revisão humana. Não
constitui atestado de conformidade nem parecer jurídico. A responsabilidade pelo
registro é do controlador.
````

---

## Como preencher cada campo

**Operação, não tabela.** O erro mais comum é transcrever o schema: uma linha por
tabela, com a tabela no lugar da finalidade. O art. 37 pede as *operações*, e uma
operação atravessa várias tabelas. Tire as operações das rotas e dos serviços — um
controller de cadastro é uma operação, um job de e-mail é outra —, depois amarre as
tabelas a elas.

**Base legal quase sempre fica marcada.** Escolher entre consentimento, execução de
contrato e legítimo interesse é decisão jurídica com consequência prática, e o código
raramente decide. Duas exceções, e só elas: existe registro de consentimento
persistido (R06), aí art. 7º, I é indício forte e você cita a coluna; ou existe
anotação `@lgpd: base_legal=` e você cita a declaração do desenvolvedor como
declaração. Fora disso, use a marca de pendência. Um ROPA com base legal chutada será
assinado como se fosse verdade.

**Dado sensível fica em coluna própria.** Art. 11 tem regime diferente do art. 7º, e
misturar as duas naturezas na mesma célula esconde exatamente o que precisa aparecer.
Em dúvida sobre um campo, escreva `Verificar` e diga por quê — melhor que um `Não`
errado.

**Titular é categoria, não pessoa.** "Usuários cadastrados", "clientes pessoa
física", "menores de dezesseis anos" quando o R19 encontrou a faixa. Se o produto
alcança menor, essa categoria entra aqui — é ela que puxa o ECA Digital.

**Uma linha sem evidência é uma linha que você inventou.** O verificador reclama de
cada linha da tabela de operações que não carregue `arquivo:linha`, e está certo. Se
você sabe que a operação existe mas não achou onde, a linha vai com a evidência
marcada como não localizada, e isso aparece no documento.

## Quando o repositório não é tudo

Um ROPA gerado de um repositório cobre o tratamento daquele repositório. Se a empresa
tem outros sistemas, este documento é um capítulo, e vale dizê-lo na primeira linha da
seção 6. Entregar como se fosse o ROPA da organização é o tipo de erro que só aparece
numa fiscalização.
