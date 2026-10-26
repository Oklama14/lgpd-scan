# Stack notes: front-end

Angular, React, Vue, Svelte, Next and Nuxt. Read this when `frameworks_detected` lists
any of them, or when the repository has `.html`, `.vue`, `.svelte` or `.tsx` screens
of its own — a monorepo with `api/` and `client/` needs both this and `node.md`.

The browser is where the data subject types their data, where the session lives, and
where third parties are reached directly, without the back-end sending anything. None
of that shows up in an entity or a controller, which is why a back-end-only reading of
a full-stack project misses whole findings.

## Forms are the inventory (R01, R02)

A field the form collects is collected, whatever the API does with it. Read the
templates next to the DTOs.

| Framework | Where the fields are |
|---|---|
| Angular | `formControlName="cpf"` in the `.html`; `this.fb.group({ nome: [...] })` or `new FormControl()` in the component |
| React | `name="email"` on inputs; `register('cpf')` (react-hook-form); zod or yup schemas, often in `schemas/` |
| Vue | `v-model="form.telefone"`; the `reactive({...})` that backs it |
| Svelte | `bind:value={telefone}` |

An input mask identifies the field when its name does not: `mask="000.000.000-00"` is
a CPF even in a field called `documento`. A field present in the form and absent from
the DTO is either discarded by the server (fine) or sent somewhere else — follow the
submit handler one level before deciding.

## The session in the browser (R08)

Signal: `web_storage_token`. A session token in `localStorage` or `sessionStorage` is
readable by every script on the page, so one XSS — or one compromised dependency —
takes the session with it. It is common practice in SPAs, which is why the finding is
a reading of two signals, not one:

- `web_storage_token` with no CSP on the page → `Parcial`, severity `Média`. Nothing
  limits what an injected script can do with the token.
- with a CSP on the page that restricts `script-src` → still worth one line, severity
  `Baixa`.

A CSP protects the page that carries it, so the question is which server delivers
`index.html`. It may live in four places, and the collector reads three: a `<meta
http-equiv="Content-Security-Policy">` in `index.html`, the hosting config
(`vercel.json`, `netlify.toml`, `nginx.conf`), and `helmet()` or a header set in the
API. The last one is the trap: when the SPA is served from Vercel or a CDN and the
API only answers JSON, `helmet()` on the API protects nothing in the browser — the
DevComply, which these notes were tested against, is exactly that case. A
Netlify-style `_headers` file has no extension and is not read — open it if it exists
before concluding there is no CSP.

The fix is an `HttpOnly`, `Secure`, `SameSite` cookie set by the API, which is a
back-end change too; say so, rather than presenting it as a one-line front-end edit.
To find which storage holds the token, read the HTTP interceptor (Angular
`HttpInterceptorFn`, an axios interceptor): it is where the `Authorization` header is
built.

A key in `environment.ts` matching `cloud_credential` is often a browser key that is
public by design — Firebase, Google Maps restricted by referrer. Whether it is
restricted is not in the code: report it under R09 with that caveat, as
`Não verificável` if nothing else points either way.

## Third parties the browser calls (R12, R16)

Signal: `third_party_web_resource` — Google Fonts, CDNs, maps, captcha, embedded
video. The subject's browser fetches the resource from the third party's server and
sends it their IP address, user agent and the page they are on. No back-end signal
sees this. Under the GDPR, a Munich court held in 2022 that loading Google Fonts from
Google's servers transmitted the visitor's IP without a legal basis; the same two
questions arise under the LGPD — legal basis (Art. 7) and international transfer
(Art. 33).

Usually severity `Baixa` — IP and user agent, no account data — and the fix is cheap:
serve the font from the project (`@fontsource/*`) and bundle the library instead of
loading it from a CDN. It rises when the resource is a tracker in disguise or loads on
pages where the subject is identified.

The collector reads style sheets for this signal only: `@import url(...)` in
`styles.scss` is the most common way Google Fonts gets in. A resource commented out in
`index.html` is not loaded and is not reported.

Tag managers and analytics (`gtag`, GTM, Meta Pixel) are `third_party_sdk`, and on the
front-end they often appear only in `index.html`, never in `package.json`.

## Cookies and consent (R06, R12)

Signal: `cookie_consent_ui` — a banner or a consent management platform. Its presence
starts the reading:

- Does the tracker wait for the choice? `gtag('consent', 'default', { analytics_storage:
  'denied' })` before `gtag('config', ...)`, or the script injected only after
  acceptance, is waiting. A `<script>` tag in `index.html` that loads unconditionally
  runs before anyone has chosen anything.
- A banner that only informs — "ao continuar navegando, você concorda" — is not
  consent.
- Where is the choice stored? Only in `localStorage` means the controller cannot
  demonstrate it later (Art. 8º, §2º puts that burden on the controller): `Parcial`
  under R06, saying what is missing.

Analytics in `index.html` with no `cookie_consent_ui` anywhere is the plain case:
the tracker runs before any choice, and the finding belongs under R12 with R06
mentioned.

The ANPD's guidance on cookies (2022) is the reference for what a valid banner offers;
cite it when the report recommends one.

A component named `cookie-*`, `privacy-*` or `termos-*` falls in the `legal` bucket by
its name, so its hits arrive as `declaration_only`. That is right for the policy
page and wrong for the component that records the choice — open it, and if it is the
implementation, credit it as such and say why in the report.

## What the front-end cannot prove

Validation in the browser is bypassed with one request. A required consent checkbox
with no column behind it in the API is R06 `Não atendido`; an age gate in the form
alone is self-declaration under R18 however it is styled. When the same rule exists in
both places, cite the server side as the evidence and the form as context.

## Frequent false positives on the front-end

- `localStorage.setItem('theme', …)`, language and layout preferences — not
  credentials; the signal only fires on keys named like one
- `.user-email`, `.cpf-mask` in a style sheet — class names; style files run no
  inventory signal
- `document.getElementById`, `document.querySelector` — DOM, not `documento`
- `{{ versao }}` and other interpolation in an Angular or Vue template — not an
  unfilled placeholder
- a planning document saying "tirar o token do localStorage" — intention, not code;
  these signals run on code only
- `dist/`, `build/`, `.angular/`, `.next/`, `.nuxt/` — build output, excluded
