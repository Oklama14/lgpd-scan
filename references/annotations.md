# Annotations in the audited code

Two vocabularies the collector reads out of the project's own source. Both are
applied mechanically by `collect.py`, not by agent discretion — a suppression that
depends on the agent remembering to honour it is a suppression that fails one day.

## Suppressing a false positive

```ts
@Column() genero: string; // lgpd-scan: ignore personal_data_field — gênero do produto, não da pessoa
```

The marker works on the line itself or on the line immediately above, in any comment
syntax (`//`, `#`, `--`, `<!--`). The signal name must be one the collector knows;
`*` suppresses every signal on that line.

**The reason is mandatory.** A marker without one is not honoured — it lands in
`suppression_rejected` with an instruction, so the developer finds out why nothing
happened instead of concluding the tool is broken. A suppression without
justification is exactly how compliance debt hides, and the half-line it costs to
write one is what separates "this is fine" from "I don't want to see this".

**Nothing disappears.** Suppressed hits go to `suppressed` in the JSON with the
reason, and the report shows them in their own section. In a compliance report, a
finding that vanishes silently is worse than noise: if someone suppressed a real gap,
the next reader has to be able to see that.

Two shapes the collector refuses, both on purpose:

| What the developer wrote | What happens |
|---|---|
| `lgpd-scan: ignore personal_data_field` | Rejected — no reason |
| `lgpd-scan: ignore campo_pessoal — motivo` | Rejected — unknown signal name |

## Declaring what the code cannot say

```ts
// @lgpd:pii=cpf @lgpd:basis=consentimento
@Column() cpf: string;

// @lgpd:retention=5anos
@Column() email: string;
```

Collected into `declared` and available to the agent as positive evidence: the
developer asserting a classification, a legal basis, a retention period.

This vocabulary is not ours. It is the one the other LGPD agent skills in
circulation already use, and reading the same format buys interoperability for free
— a schema annotated for those skills needs no second annotation for this one.

Treat a declaration as what it is: the developer's word, not something the tool
verified. Cite it as declaration in the report, and where the code contradicts it,
the contradiction is the finding — a field annotated `@lgpd:retention=5anos` in a
project with no purge routine at all is exactly the kind of gap worth naming.

## Signal names

The names accepted after `ignore` are the keys of `signals` in
`.lgpd-scan/candidates.json`. Running the collector once on the project prints them
all in the summary, which is the fastest way to find the right one.
