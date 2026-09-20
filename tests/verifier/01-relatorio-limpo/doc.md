# Relatório de Conformidade LGPD — fixture

| | |
|---|---|
| **Ferramenta** | lgpd-scan |

## Resumo

O sistema trata nome, e-mail, CPF e telefone de usuários cadastrados.

## Dados pessoais encontrados

| Tabela | Campo | Natureza | Onde |
|---|---|---|---|
| `usuarios` | `cpf` | Dado pessoal | `src/users/entities/user.entity.ts:6` — `@Column() cpf: string;` |

## Achados

### R03 — Direito de eliminação · Atendido

A rota existe: `src/users/users.controller.ts:5` — `@Delete('me')`.

### R04 — Direito de acesso · Parcial · Severidade média

Há leitura do próprio cadastro em `src/users/users.controller.ts:3` — `@Get('me')`,
mas nenhuma exportação em formato interoperável.

## Não verificável a partir do código

Contrato com operadores.

## Limitações desta análise

Esta análise lê o código-fonte. Não constitui parecer jurídico.
