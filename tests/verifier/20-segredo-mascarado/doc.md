# Relatório de Conformidade LGPD — fixture

## Achados

### R09 — Segredos fora do repositório · Não atendido · Severidade alta

A credencial está em arquivo rastreado: `docker-compose.yml:4` —
`POSTGRES_PASSWORD: ***`. O valor fica fora deste relatório de propósito; rotacione
antes de remover a linha, porque apagar a linha não apaga o histórico.

### R01 — Inventário · Não verificável

Não há schema neste recorte.

## Não verificável a partir do código

Todo o resto: este fixture é um recorte de infraestrutura.

## Limitações desta análise

Não constitui parecer jurídico.
