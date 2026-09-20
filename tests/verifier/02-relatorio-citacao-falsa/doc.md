# Relatório de Conformidade LGPD — fixture

## Achados

### R06 — Registro de consentimento · Não atendido · Severidade alta

Nada persiste o consentimento: `src/users/consent.service.ts:14` — `saveConsent(`.
E a entidade termina antes disso: `src/users/entities/user.entity.ts:340` — `@Column()`.

## Não verificável a partir do código

Nada.

## Limitações desta análise

Não constitui parecer jurídico.
