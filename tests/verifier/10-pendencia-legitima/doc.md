# Registro das Operações de Tratamento de Dados Pessoais (ROPA)

| | |
|---|---|
| **Controlador** | ⚠ A PREENCHER PELO CONTROLADOR — razão social e CNPJ |
| **Encarregado (DPO)** | ⚠ A PREENCHER — não verificável em código |

## 1. Operações de tratamento

| # | Operação | Base legal | Retenção | Evidência |
|---|---|---|---|---|
| OP01 | Cadastro de usuário | ⚠ A PREENCHER PELO CONTROLADOR | ⚠ Não verificável em código | `src/users/entities/user.entity.ts:4` — `email: string;` |
| OP02 | Exclusão a pedido do titular | ⚠ A PREENCHER | ⚠ A avaliar pelo controlador | `src/users/users.controller.ts:5` — `@Delete('me')` |

## 2. Dados pessoais por entidade

| Entidade | Campo | Onde |
|---|---|---|
| `usuarios` | `cpf` | `src/users/entities/user.entity.ts:6` — `@Column() cpf: string;` |

## 4. Medidas de segurança

| Medida | Estado | Evidência |
|---|---|---|
| Registro de incidente | Ausente | Nenhuma entidade de incidente |

## 5. Retenção e eliminação

| Dado | Prazo | Evidência |
|---|---|---|
| `usuarios` | ⚠ A PREENCHER — indefinido no código | Nenhuma rotina de expurgo |

## 6. O que este registro não apura

Base legal, contratos, prazos contratuais.
