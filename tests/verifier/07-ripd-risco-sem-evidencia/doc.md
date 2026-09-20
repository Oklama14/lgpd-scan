# Relatório de Impacto à Proteção de Dados Pessoais (RIPD)

## 1. Descrição do tratamento

O sistema mantém cadastro de usuários com nome, e-mail, CPF e data de nascimento.

## 4. Medidas de segurança e salvaguardas

| Medida | Estado | Evidência |
|---|---|---|
| CPF em texto claro | **Falha** | `src/users/entities/user.entity.ts:6` — `@Column() cpf: string;` |

## 5. Riscos identificados

### RISCO 01 — CPF armazenado sem cifragem

**Evidência.** `src/users/entities/user.entity.ts:6` — `@Column() cpf: string;`

**Impacto.** Alto.

### RISCO 02 — Ausência de política de senha forte

**Impacto.** Médio.

## 9. Limitações

A avaliação de risco residual é do controlador.
