# Registro das Operações de Tratamento de Dados Pessoais (ROPA)

## 1. Operações de tratamento

| # | Operação | Finalidade | Base legal | Titulares | Dados | Evidência |
|---|---|---|---|---|---|---|
| OP01 | Cadastro de usuário | Acesso | ⚠ A PREENCHER | Usuários | Nome, e-mail | `src/users/entities/user.entity.ts:4` — `email: string;` |
| OP02 | Envio de newsletter por e-mail | Marketing | Consentimento | Usuários | E-mail | Fluxo de marketing |

## 4. Medidas de segurança

| Medida | Estado | Evidência |
|---|---|---|
| Hash de senha | Implementada | `src/users/users.service.ts:1` — `export class UsersService` |

## 5. Retenção e eliminação

| Dado | Prazo | Evidência |
|---|---|---|
| `usuarios` | ⚠ A PREENCHER | Nenhuma rotina de expurgo |
| `usuarios.cpf` | ⚠ A PREENCHER | `src/users/entities/user.entity.ts:6` — `@Column() cpf: string;` |

## 6. O que este registro não apura

Base legal e contratos.
