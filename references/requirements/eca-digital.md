# R18–R21 — ECA Digital, Lei nº 15.211/2025

Em vigor desde **17 de março de 2026**, com a exigência de verificação de idade em
duas etapas: imediata para lojas de aplicativos, e desde agosto de 2026 para os
demais setores.

Estes quatro requisitos são, junto com o R09, os mais verificáveis em código de toda
a lista — porque a lei não pede "cuidado com menores" em abstrato, ela proíbe
mecanismos específicos e exige outros. Uma proibição concreta é exatamente o tipo de
coisa que se lê num arquivo.

**Antes de avaliar, decida se o grupo se aplica.** Uma ferramenta interna B2B não
tem menor entre os titulares, e nesse caso os quatro saem como `Não se aplica` com a
razão escrita. Rede social, jogo, produto educacional, e-commerce aberto, qualquer
serviço que não exclua menores: aplica-se. Não decida isso só pelo código — a
ausência de sinal de idade pode significar tanto "não trata menores" quanto "trata e
não verifica", e essas duas conclusões são opostas.

Vocabulário de status e a distinção declaração × implementação estão em `index.md`.

---

## R18 — Verificação de idade sem autodeclaração
**Lei 15.211/2025** · sinais: `age_self_declaration`, `age_verification_provider` ·
absência do provedor importa

A lei exige mecanismo confiável de verificação de idade e **veda expressamente a
autodeclaração**.

Isso inverte o sinal de leitura em relação a todo o resto da auditoria. Em geral,
encontrar um campo é neutro e a ausência é o achado. Aqui, encontrar um campo de data
de nascimento ou uma caixa "confirmo que tenho 18 anos", **sem** nada que verifique,
é evidência direta de não conformidade. O controle que o projeto acha que tem é
justamente o que a lei recusa.

O par de sinais é o que permite distinguir os dois casos:

| `age_self_declaration` | `age_verification_provider` | Leitura |
|---|---|---|
| presente | ausente | Autodeclaração pura — `Não atendido`, severidade `Alta` |
| presente | presente | Coleta e verifica — leia o fluxo para confirmar que a verificação bloqueia |
| ausente | ausente | Nenhum tratamento de idade — confirme se o grupo se aplica |
| ausente | presente | Verificação sem coleta declarada — provável integração; leia |

Provedores que contam como verificação: integração de documento com prova de vida,
serviços de identidade (gov.br como provedor de login, Serpro, Idwall, Unico,
BigDataCorp, CAF, ClearSale), ou verificação por terceiro especializado. Um `if
(idade >= 18)` sobre um campo que o próprio usuário digitou não conta, e é esse o
ponto do requisito.

Cuidado com um falso positivo específico: `unico` é palavra comum em português. O
padrão só casa com o nome do produto (`unico_check`, `@unico/`), nunca com "único
parágrafo" — mas se a stack for outra, confirme lendo.

## R19 — Vinculação a responsável legal
**Lei 15.211/2025** · sinais: `parental_link`, `minor_flag` · absência importa

Em rede social, conta de menor de dezesseis anos deve estar vinculada à conta de um
dos responsáveis legais.

Em código isso é uma relação: coluna de responsável, conta supervisionada, fluxo de
convite ou aceite do responsável. Procure a relação, não a palavra — `responsavel`
sozinho quase sempre é "responsável pela decisão" em texto de política, e o padrão
exige qualificador (`responsavel_id`, `responsavel_legal`, `vinculo_responsavel`)
por causa disso.

Se `minor_flag` aparece e `parental_link` não, o sistema sabe que tem menor e não tem
o vínculo — `Não atendido`, severidade `Alta`. Se nenhum dos dois aparece num produto
que claramente alcança menores, a lacuna é mais funda: o sistema não distingue a
faixa etária, então não tem como aplicar nenhuma das quatro regras deste grupo.

## R20 — Configuração padrão mais protetiva
**Lei 15.211/2025** · sinais: `default_privacy_open`, `minor_flag`

A configuração padrão deve estar no nível mais protetivo de privacidade, alinhada à
faixa etária e aos riscos.

O achado aqui é o **default permissivo**: `isPublic: true`, `visibility: 'public'`,
`searchable: true` como valor padrão de coluna ou de formulário. Um perfil que nasce
público é o oposto do que a lei pede, e a evidência é o próprio default no schema.

Dois cuidados. Primeiro, confirme que o campo é sobre pessoa: um projeto ou um
produto público não tem relação com privacidade de titular, e é um falso positivo
comum. Segundo, se existir `minor_flag`, veja se o default varia por faixa — a lei
pede alinhamento à idade, e um default único para todos, mesmo restritivo, é
`Parcial`.

## R21 — Perfilamento publicitário direcionado a menores
**Lei 15.211/2025** · sinais: `ad_targeting`, `minor_flag`, `third_party_sdk`

A lei proíbe técnicas de perfilamento para direcionar publicidade comercial a
crianças e adolescentes.

O sinal procura SDK e parâmetro de anúncio: AdMob, AdSense, DoubleClick, público
personalizado, remarketing, lookalike, anúncio por interesse. A presença sozinha não
é o achado — um adulto pode receber publicidade segmentada legalmente. O achado é a
**combinação**: SDK de perfilamento num produto que trata menor, sem nada que
segregue os dois casos.

Então a leitura é sempre cruzada. Se há `ad_targeting` e há `minor_flag`, procure a
exclusão: alguma condição que desative a segmentação para a faixa protegida. Se não
houver, `Não atendido` com severidade `Alta` — é proibição expressa, não
recomendação. Se há `ad_targeting` e nenhum sinal de menor, o requisito depende de a
resposta do R18/R19 dizer que menores não são alcançados; sem isso, fica
`Não verificável` e o relatório explica a dependência.

---

## Por que este grupo vale a leitura cuidadosa

Os outros dezessete requisitos vêm de uma lei de 2018, com sete anos de prática
acumulada. Estes quatro vêm de uma lei que entrou em vigor há poucos meses, e a
maior parte do mercado ainda não olhou para eles. É onde um relatório tem mais chance
de dizer ao desenvolvedor algo que ele não sabia — e também onde um erro seu tem mais
chance de passar sem contestação, o que é razão para ser mais conservador com a
confiança declarada, não menos.
