# R13–R17 — Resoluções da ANPD e anonimização

Cinco requisitos que vêm da regulamentação infralegal e do art. 12. Só a parte que
deixa rastro em código entra aqui; o resto pertence ao mundo dos contratos e das
políticas internas, e o relatório diz isso na seção de limitações.

Vocabulário de status e a distinção declaração × implementação estão em `index.md`.

---

## R13 — Registro de incidente de segurança
**Res. CD/ANPD nº 15, de 24/04/2024, art. 10** · sinais: `incident_register` ·
absência importa

O controlador precisa manter o registro do incidente **por no mínimo cinco anos**,
com data, circunstâncias, natureza dos dados, número de titulares afetados,
avaliação de risco, medidas adotadas e forma de comunicação.

A parte verificável é binária: existe uma tabela, um log dedicado ou um event store
de incidente, ou não existe. Procure entidade, migration ou serviço com esse nome.

Não confunda com log de aplicação. Log rotaciona, não é imutável e não foi feito
para ser prova — o próprio requisito fala de *registro*, que é outra coisa. Se o que
existe é só o logger do framework, isso é `Não atendido`, e vale dizer por quê.

Quando o registro existe, olhe se há retenção declarada. Cinco anos é o mínimo legal;
um registro que expira em noventa dias é `Parcial`, e o relatório deve dizer o prazo
que encontrou.

Severidade da lacuna: `Média`. Não expõe titular diretamente, mas impossibilita
cumprir o prazo do R14 no dia em que o incidente acontecer.

## R14 — Comunicação de incidente no prazo
**Res. CD/ANPD nº 15/2024, art. 6º e 9º** · sinais: `incident_notification`

O prazo é de **três dias úteis** a partir do conhecimento do incidente, tanto para a
ANPD quanto para o titular — **em dobro para agentes de pequeno porte**. A
comunicação tem conteúdo mínimo definido na resolução.

Em código isso aparece como serviço de notificação, template de comunicação, fila ou
job disparado por incidente. A ausência é o caso comum, e é honesto reportá-la como
lacuna de processo, não de código: um controlador pode cumprir o prazo por e-mail
manual. Diga isso — o achado é "não há nada que ajude a cumprir o prazo", não "o
prazo está sendo descumprido", que o código não tem como mostrar.

Se encontrar um prazo codificado, confira o número. Três dias **úteis** não é o mesmo
que setenta e duas horas, e essa confusão é frequente.

## R15 — Encarregado indicado e canal do titular
**Res. CD/ANPD nº 18/2024** · sinais: `dpo_contact`, `placeholder_unfilled`,
`dsar_flow`, `dsar_deadline` · absência importa

O encarregado tem de estar indicado e o canal de atendimento ao titular, disponível
e divulgado.

Aqui há um achado que aparece com frequência desconfortável: o canal existe no texto
da política e **nunca foi preenchido**. `DPO: [E-MAIL]`, `Responsável: [NOME]`,
`Atualizado em: TODO`. O sinal `placeholder_unfilled` procura exatamente isso, e só
roda em arquivo do bucket `legal`, porque `TODO` em código é outra conversa.

Esse caso é pior que a ausência simples: a política manda o titular procurar um canal
que não existe. Reporte como `Não atendido` com severidade `Média`, e cite a linha do
marcador.

Quando o contato existe, ele é uma declaração — o código não prova que alguém atende
aquela caixa. Credite o que encontrou e mande o resto para `Não verificável`.

O canal pode também estar construído: `dsar_flow` localiza um fluxo de pedido do
titular (entidade, rota ou fila de solicitações), e `dsar_deadline` um prazo
codificado. Um fluxo que registra o pedido e a data é evidência mais forte que um
e-mail na política. Confira o número do prazo: confirmação de existência e acesso
saem imediatamente em formato simplificado, ou em até quinze dias por declaração
clara e completa (art. 19, I e II).

## R16 — Salvaguarda de transferência internacional
**Res. CD/ANPD nº 19/2024** · sinais: `transfer_safeguard`, `cloud_region`,
`third_party_sdk`

Transferência internacional precisa de fundamento: cláusulas contratuais padrão,
cláusulas específicas, normas corporativas globais, ou decisão de adequação.

O código mostra **para onde** o dado vai — região do bucket, host da API, SDK de
terceiro, provedor de IA — e é isso que o R12 já levanta. O que este requisito
acrescenta é a pergunta da salvaguarda, que o código quase nunca responde.

Então o padrão de julgamento é: liste os destinos que encontrou com evidência, e
mande a existência da salvaguarda para `Não verificável`, dizendo explicitamente que
é pendência documental. Referência a cláusula-padrão no repositório é indício de que
alguém pensou no assunto, não prova de contrato assinado.

## R17 — Anonimização e pseudonimização
**Art. 12 da Lei 13.709/2018** · sinais: `anonymization` · absência importa

Dado anonimizado sai do alcance da lei — desde que a anonimização seja irreversível
por meios razoáveis. Pseudonimização não tem esse efeito, e confundir as duas é o
erro clássico.

Procure: rotina de anonimização, mascaramento, cofre de token, hash irreversível,
k-anonimato. E quando encontrar, leia: um "anonimizar" que só troca o nome por um id
sequencial guardado numa tabela de mapeamento é pseudonimização, e o relatório deve
dizer isso com essas palavras.

A ausência raramente é `Alta` por si. Ela ganha peso quando combinada com retenção
indefinida (R07): dado que fica para sempre e nunca é anonimizado é a pior das duas
lacunas somadas, e vale conectar as duas seções explicitamente.

---

## O que destes requisitos não é verificável em código

Praticamente toda a metade organizacional: se o encarregado nomeado de fato atende,
se há contrato com o operador, se o plano de resposta a incidente foi testado, se a
avaliação de risco aconteceu. Nada disso deixa rastro num repositório.

Isso não é motivo para omitir os requisitos — é motivo para o relatório distinguir
com clareza o que apurou do que apenas perguntou. Um requisito que aparece como
`Não verificável` com a razão escrita vale mais que um requisito ausente da lista.
