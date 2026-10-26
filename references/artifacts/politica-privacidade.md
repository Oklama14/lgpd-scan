# Política de privacidade gerada a partir do código

**Art. 9º da Lei 13.709/2018.** O titular tem direito ao acesso facilitado às
informações sobre o tratamento: finalidade específica, forma e duração, identificação
do controlador, uso compartilhado, responsabilidades dos agentes e seus direitos do
art. 18.

Escreva em `<repo>/POLITICA-PRIVACIDADE.md`. As regras comuns aos artefatos estão em
`index.md`.

---

## Por que este artefato é diferente dos outros três

Toda ferramenta desta área gera política a partir de questionário: o desenvolvedor
responde "coletamos e-mail e telefone" e sai um texto. O texto fica bonito e não tem
relação nenhuma com o sistema — é a mesma inversão que esta skill existe para
desfazer, só que produzindo o problema em vez de detectá-lo.

Aqui a política sai do **inventário**. A seção "dados que tratamos" é a tabela do R01
reescrita em português de gente, e por construção ela não pode omitir um campo que
existe nem inventar um que não existe.

E há uma segunda regra, que é a parte que importa:

> **A política só promete o que o código entrega.**

Se não há rota de exclusão de conta, a política **não** diz "você pode excluir sua
conta a qualquer momento". Ela diz que a exclusão é feita mediante pedido ao
encarregado — o que é legítimo pela LGPD, é verdade, e é o que o sistema faz. Uma
política que promete um botão que não existe não é um texto ruim: é a própria
não conformidade, documentada e publicada pelo controlador, e é o achado que o R15 e
a reconciliação política × código levantam em auditoria.

O verificador aplica isso: `--kind politica` roda o coletor no repositório e recusa o
documento quando ele promete automação que nenhum sinal sustenta.

## O anexo de evidência vai separado

A política é documento público, lido por titular. Ela não leva `arquivo:linha` — seria
absurdo, e expõe a estrutura interna do sistema sem necessidade.

Então escreva **dois** arquivos:

| Arquivo | Para quem | Conteúdo |
|---|---|---|
| `POLITICA-PRIVACIDADE.md` | o titular | o texto, limpo, sem citação |
| `.lgpd-scan/politica-evidencia.md` | o encarregado e a auditoria | cada afirmação da política e a linha de código que a sustenta |

O anexo é o que torna a política conferível daqui a seis meses, quando alguém
perguntar de onde saiu a frase "não compartilhamos seus dados com terceiros para fins
publicitários". Ele passa pelo verificador como qualquer outro documento.

---

## Estrutura da política

````markdown
<!-- lgpd-scan:generated {tool_version} {AAAA-MM-DD} -->
# Política de Privacidade — {nome do produto}

**Última atualização:** {DD/MM/AAAA} · **Versão:** {1.0}

## 1. Quem trata os seus dados

⚠ A PREENCHER PELO CONTROLADOR — razão social, CNPJ e endereço.

**Encarregado (DPO):** {contato encontrado no código, ou a marca de pendência}

## 2. Quais dados tratamos

Tratamos os dados abaixo, que são os que o sistema efetivamente coleta e armazena:

| Dado | Quando é coletado | Para quê |
|---|---|---|
| Nome | No cadastro | Identificar você na plataforma |
| E-mail | No cadastro | Login, comunicação sobre o serviço |
| Senha | No cadastro | Autenticação — guardada apenas como hash, nunca em texto |

{Uma linha por campo do inventário do R01. Nada além dele: se um campo não existe no
código, ele não entra aqui, e se existe, ele não pode ficar de fora.}

**Dados sensíveis (art. 11).** {Liste, ou diga que não tratamos.}

## 3. Para que usamos

{Uma finalidade por operação encontrada. Finalidade não dedutível do código entra
marcada — e a marca fica visível no texto até o controlador preencher, de propósito.}

## 4. Com base em quê

⚠ A PREENCHER PELO CONTROLADOR — a base legal de cada finalidade (art. 7º e art. 11)
é decisão do controlador e não está no código.

## 5. Com quem compartilhamos

{Terceiros do R12, com o que recebem e por quê. Se não há nenhum, diga isso — é uma
afirmação forte e verificável.}

**Transferência internacional.** {Destinos do R16, ou a ausência deles.}

## 6. Por quanto tempo guardamos

{Prazos do R07. Se não há prazo definido no sistema, a política não pode inventar um:
escreva a marca de pendência.}

## 7. Seus direitos

Você pode, a qualquer momento:

- **Confirmar e acessar** os seus dados {— na tela de perfil | mediante pedido ao encarregado}
- **Corrigir** dados incompletos ou desatualizados {— na tela de perfil | mediante pedido}
- **Exportar** os seus dados em formato legível {— pelo botão de exportação | mediante pedido}
- **Excluir** a sua conta e os dados associados {— nas configurações | mediante pedido ao encarregado}
- **Revogar o consentimento**, quando o tratamento se basear nele
- **Peticionar** perante a ANPD

{O trecho entre chaves é escolhido pelo que o código tem. Automação só entra quando
existe a rota.}

**Prazo de resposta:** 15 dias, contados do pedido (art. 19, II).

## 8. Segurança

{Só as medidas que existem, em linguagem de titular: "sua senha é guardada como hash
e não pode ser lida nem por nós" sai de `bcrypt.hash`. Nada de "adotamos as melhores
práticas do mercado", que não significa nada e não é verificável.}

## 9. Alterações e contato

{Como a política é versionada e como falar com o encarregado.}

---

Documento gerado a partir do código-fonte por lgpd-scan {tool_version} em
{DD/MM/AAAA}. Ele descreve o que o sistema faz hoje; revisão jurídica antes da
publicação é obrigatória, e nenhuma ferramenta substitui essa revisão.
````

---

## A tabela de promessas

O verificador cruza o que a política afirma com o que o coletor achou. Escreva
sabendo disso — não é armadilha, é a regra do artefato.

| Se a política promete | Precisa existir | Se não existe |
|---|---|---|
| exclusão de conta pelo próprio titular | `delete_route` ou `delete_route_alt` | reescreva como pedido ao encarregado |
| exportação / portabilidade automática | `export_route` | idem |
| correção pelo próprio titular | `update_route` | idem |
| criptografia dos dados | `encryption_at_rest` ou `password_hash_strong` | não afirme |
| anonimização | `anonymization` | não afirme |
| verificação de idade | `age_verification_provider` | não afirme — e veja o R18 |
| canal do encarregado | `dpo_contact` preenchido | marca de pendência, nunca `[E-MAIL]` |

**Promessa mediada não é promessa automática.** "Você pode solicitar a exclusão pelo
canal do encarregado" é verdadeiro mesmo sem rota, porque o atendimento manual é
legítimo — a lei exige o direito, não o botão. O verificador reconhece as duas formas
e só reclama da primeira sem lastro.

## Autocontaminação: a próxima auditoria precisa saber

A política gerada fica no repositório, no bucket `legal`, e a auditoria seguinte a
lerá como "a política publicada do projeto". Se ela for tratada como declaração
independente, a reconciliação política × código vira circular: a ferramenta confere o
texto que ela mesma escreveu a partir daquele código e conclui, sem surpresa, que
batem.

Por isso o cabeçalho traz `<!-- lgpd-scan:generated -->`. O coletor marca as
ocorrências desse arquivo com `generated_by_tool: true`, e o relatório precisa dizer,
na seção de reconciliação, que a política foi gerada por esta ferramenta e que a
concordância entre as duas não é evidência independente. **Não apague o marcador.**

Se o controlador reescrever a política à mão depois, aí sim ela volta a ser declaração
independente — e a pessoa que reescreveu tira o marcador junto, que é exatamente o
sinal certo.
