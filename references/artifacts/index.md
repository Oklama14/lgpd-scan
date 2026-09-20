# Artefatos gerados

Quatro documentos que a skill pode gerar a partir do que apurou no código: o ROPA
(art. 37), o RIPD (art. 38), uma minuta de contrato com operador (arts. 39 e 46) e a
política de privacidade (art. 9º).

| Artefato | Arquivo | Base legal | Quando |
|---|---|---|---|
| ROPA — registro das operações | `ropa.md` | Art. 37 | Sempre que houver dado pessoal; é exigência permanente do controlador |
| RIPD — relatório de impacto | `ripd.md` | Art. 38 | Tratamento de risco elevado, ou quando a ANPD solicitar |
| DPA — cláusulas com operador | `dpa.md` | Art. 39, 42 a 45, 46 | Quando o R12 apontou terceiro tratando dado pessoal |
| Política de privacidade | `politica-privacidade.md` | Art. 9º | Quando não há política, ou a publicada não bate com o código |

Cada arquivo traz a estrutura, o que preencher em cada campo e o que **não** inventar.
Leia só o do artefato pedido.

---

## Quatro regras que valem para os três

**0. A política é a exceção da regra 2, e vale ler o arquivo dela antes.** Ela é
documento público, lido por titular, e não leva `arquivo:linha` — a evidência vai num
anexo separado. Em compensação ela tem uma restrição que os outros três não têm: só
promete o que o código entrega, e o verificador recusa o documento quando ela promete
automação que nenhum sinal sustenta.

**1. O artefato passa pelo verificador.** Gerar um ROPA é o que toda ferramenta
desta área faz. Gerar um ROPA cujas afirmações apontam para linhas de código que
existem é a diferença. Depois de escrever:

```bash
python3 scripts/verify_report.py <repo>/ROPA.md --repo <repo> --kind ropa
```

O verificador reconhece o tipo do documento pelo título ou pelo nome do arquivo, e
aplica a checagem que cabe a ele: no ROPA, cada linha da tabela de operações precisa
de evidência; no RIPD, cada risco; no DPA, os anexos técnicos. Nos três, marcador não
preenchido é erro — o documento que a ferramenta entrega não pode conter `[INSERIR
NOME]`, que é exatamente a falha que ela reporta como R15.

**2. Coluna de evidência, não de opinião.** Toda tabela destes documentos termina
numa coluna `Evidência` com `arquivo:linha` e o trecho entre crases. É o que
distingue um ROPA levantado do código de um ROPA respondido de memória — e é o que
permite que alguém o confira em seis meses, quando o código já mudou.

**3. O que o código não mostra vai marcado, não preenchido.** Finalidade, base legal
escolhida, prazo contratual de retenção, nome do encarregado, medidas
organizacionais: nada disso está no repositório. Use a marca

> `⚠ A PREENCHER PELO CONTROLADOR — não verificável em código`

no lugar do valor. Um ROPA com a base legal chutada é pior que um ROPA com a lacuna
visível: o primeiro será assinado como se fosse verdade.

**4. O documento gerado é declaração, não apuração.** Diga isso dentro do documento,
no rodapé, com estas palavras: gerado por ferramenta a partir do código, revisão
humana obrigatória, não constitui parecer jurídico. O ROPA é uma obrigação do
controlador — quem responde por ele é o controlador, e o documento precisa deixar
claro de onde veio.

## De onde vem cada coisa

O `candidates.json` já tem quase tudo o que os três precisam. A ordem econômica é:
rode a auditoria primeiro, gere o artefato depois, reaproveitando o inventário.

| Campo do artefato | Vem de |
|---|---|
| Categorias de dados pessoais | Inventário do R01 e R02 (sinais do léxico) |
| Titulares | Entidades onde os campos pessoais vivem |
| Destinatários e terceiros | R12 — `third_party_sdk`, `external_http_call` |
| Transferência internacional | R16 — `cloud_region`, host de API, provedor de IA |
| Retenção | R07 — `retention`, cron de expurgo, anotação `@lgpd: retencao=` |
| Medidas de segurança | R08 e R10 — hash de senha, TLS, criptografia, controle de acesso |
| Registro de incidente | R13 — entidade ou tabela de incidente |
| Base legal declarada | Anotação `@lgpd: base_legal=` quando existir; senão, a marca do item 3 |
| Direitos que a política pode prometer | R03, R04, R05 — as rotas que existem de fato |

Se a auditoria não foi feita, rode `scripts/collect.py` de todo modo: gerar qualquer
um dos três sem passar pelo coletor significa escrever de memória, e aí o documento
não vale mais que o formulário que ele deveria substituir.
