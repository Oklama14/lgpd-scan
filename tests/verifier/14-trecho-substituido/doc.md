# Relatório de Conformidade LGPD — fixture

## Achados

### R03 — Direito de eliminação · Atendido

A rota de exclusão da própria conta existe:
`src/users/users.controller.ts:5` — `@Delete('me') removerContaDoTitular(@Request() req)`.

## Não verificável a partir do código

Nada.

## Limitações desta análise

Não constitui parecer jurídico.
