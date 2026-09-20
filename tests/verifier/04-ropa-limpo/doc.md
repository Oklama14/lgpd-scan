# Registro das Operações de Tratamento de Dados Pessoais (ROPA)

| | |
|---|---|
| **Controlador** | ⚠ A PREENCHER PELO CONTROLADOR — razão social e CNPJ |

## 1. Operações de tratamento

| # | Operação | Finalidade | Base legal | Titulares | Dados | Sensíveis | Retenção | Evidência |
|---|---|---|---|---|---|---|---|---|
| OP01 | Cadastro de usuário | Acesso à plataforma | ⚠ A PREENCHER | Usuários cadastrados | Nome, e-mail, CPF | Não | ⚠ Não verificável | `src/users/entities/user.entity.ts:4` — `@Column({ unique: true }) email: string;` |
| OP02 | Autoatendimento do titular | Acesso e correção | ⚠ A PREENCHER | Usuários cadastrados | Cadastro completo | Não | ⚠ Não verificável | `src/users/users.controller.ts:3` — `@Get('me')` |

## 2. Dados pessoais por entidade

| Entidade | Campo | Natureza | Onde |
|---|---|---|---|
| `usuarios` | `cpf` | Dado pessoal | `src/users/entities/user.entity.ts:6` — `@Column() cpf: string;` |
| `usuarios` | `data_nascimento` | Dado pessoal | `src/users/entities/user.entity.ts:5` — `dataNascimento: Date;` |

## 3. Compartilhamento e operadores

| Destinatário | O que recebe | País | Salvaguarda | Evidência |
|---|---|---|---|---|
| Nenhum identificado | — | — | — | Nenhuma chamada a terceiro no repositório |

## 4. Medidas de segurança implementadas

| Medida | Estado | Evidência |
|---|---|---|
| Registro de incidente | Ausente | Nenhuma entidade de incidente no repositório |

## 5. Retenção e eliminação

| Dado | Prazo | Gatilho | Evidência |
|---|---|---|---|
| `usuarios` | ⚠ A PREENCHER — indefinido no código | Nenhum | Nenhuma rotina de expurgo |

## 6. O que este registro não apura

Base legal, contratos e prazos contratuais. Não constitui parecer jurídico.
