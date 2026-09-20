# Relatório de Conformidade LGPD — fixture

## Achados

### R10 — Minimização em logs · Parcial · Severidade média

O log interpola o objeto inteiro: `src/users/users.service.ts:1` —
`export class UsersService` é onde o serviço vive, e a interpolação usa
`${dto.email}` dentro de um template literal.

O padrão do guard é `if (!user) { throw new Error(); }`, e o corpo fica assim:

```ts
const msg = `usuario ${user.email} atualizado`;
if (ok) { logger.log(msg); }
```

## Não verificável a partir do código

Retenção de log no provedor.

## Limitações desta análise

Não constitui parecer jurídico.
