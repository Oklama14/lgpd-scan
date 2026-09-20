# Minuta de cláusulas de tratamento de dados pessoais

> **Minuta para revisão jurídica.** Não assine sem revisão juridica.

## 3. Obrigações do operador

O OPERADOR compromete-se a tratar os dados conforme as instruções do CONTROLADOR.

## Anexo I — Atividades de tratamento pelo operador

| Item | Conteúdo | Evidência |
|---|---|---|
| Operador | Provedor de e-mail transacional | Integração de envio de e-mail |
| Categorias de titulares | Usuários cadastrados | `src/users/entities/user.entity.ts:2` — `export class User` |

## Anexo II — Medidas técnicas de segurança

| Medida | No controlador | Evidência | Exigida do operador |
|---|---|---|---|
| Cifragem em trânsito | Implementada | `src/users/users.service.ts:1` — `export class UsersService` | Sim |
