# Relatório de Conformidade LGPD — fixture

## Resumo

Cadastro com nome, e-mail e CPF. As lacunas maiores são consentimento e retenção.

## Achados

### R01 — Inventário de dados pessoais · Atendido

- `src/users/entities/user.entity.ts:4` — `@Column({ unique: true }) email: string;`
- `src/users/dto/create-user.dto.ts:3` — `@IsEmail() email: string;`

### R02 — Dados sensíveis · Nao atendido · Severidade baixa

Nenhum campo do art. 11 no schema; busca por saude, biometria, origem racial e opiniao politica nao retornou nada.

### R03 — Direito de eliminação · Atendido

- `src/users/users.controller.ts:5` — `@Delete('me')`

### R04 — Direito de acesso e portabilidade · Parcial · Severidade media

- `src/users/users.controller.ts:3` — `@Get('me')`

### R05 — Direito de correção · Atendido

- `src/users/users.controller.ts:4` — `@Patch('me')`

### R06 — Registro de consentimento · Nao atendido · Severidade alta

Nenhuma coluna de aceite, versao de politica ou data de consentimento na entidade nem no DTO.

### R07 — Retenção e expurgo · Nao atendido · Severidade media

Nenhuma coluna de expurgo, TTL ou rotina agendada no repositorio.

### R08 — Segurança de credenciais · Atendido

- `src/users/users.service.ts:3` — `await bcrypt.hash(dto.senha, 10)`

### R09 — Segredos fora do repositório · Atendido

- `package.json:1` — `{`

### R10 — Minimização em logs · Nao verificavel

Nao ha chamada de logger no recorte deste repositorio.

### R11 — Registro das operações · Nao atendido · Severidade baixa

Nenhum registro de operacoes versionado.

### R12 — Compartilhamento com terceiros · Nao atendido · Severidade baixa

Nenhuma dependencia de terceiro que receba dado pessoal no package.json.

### R13 — Registro de incidente · Nao atendido · Severidade media

Nenhuma entidade, migration ou servico de incidente.

### R14 — Comunicação de incidente · Nao atendido · Severidade media

Nenhum servico de notificacao de incidente.

### R15 — Encarregado e canal · Nao atendido · Severidade media

Nenhum contato de encarregado no repositorio.

### R16 — Transferência internacional · Nao verificavel

Nenhum destino internacional identificado; a salvaguarda e pendencia documental.

### R17 — Anonimização · Nao atendido · Severidade baixa

Nenhuma rotina de anonimizacao ou mascaramento.

### R18 — Verificação de idade · Nao se aplica

Ferramenta interna B2B: nao ha menor entre os titulares.

### R19 — Responsável legal · Nao se aplica

Ver R18.

### R20 — Configuração padrão · Nao se aplica

Ver R18.

### R21 — Perfilamento para menores · Nao se aplica

Ver R18.


## Não verificável a partir do código

Contrato com operadores e canal do encarregado.

## Limitações desta análise

Esta análise lê o código-fonte. Não constitui parecer jurídico.
