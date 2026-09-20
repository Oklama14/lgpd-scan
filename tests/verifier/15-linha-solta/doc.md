# Registro das Operações de Tratamento de Dados Pessoais (ROPA)

## 1. Operações de tratamento

| # | Operação | Base legal | Evidência |
|---|---|---|---|
| OP01 | Cadastro de usuário | ⚠ A PREENCHER | `src/users/entities/user.entity.ts:4` — `email: string;` |
| OP02 | Exclusão pelo titular | ⚠ A PREENCHER | `src/users/users.controller.ts:5` — `@Delete('me')` |
| OP03 | Correção pelo titular | ⚠ A PREENCHER | `src/users/users.controller.ts:4` — `@Patch('me')` |

| OP04 | Integração com CRM externo | Legítimo interesse | Sincronização noturna |

## 4. Medidas de segurança

| Medida | Estado | Evidência |
|---|---|---|
| Registro de incidente | Ausente | Nenhuma entidade de incidente |

## 5. Retenção e eliminação

| Dado | Prazo | Evidência |
|---|---|---|
| `usuarios` | ⚠ A PREENCHER | Nenhuma rotina de expurgo |

## 6. O que este registro não apura

Base legal e contratos.
