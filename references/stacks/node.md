# Stack notes: Node / TypeScript

Where each thing lives in an Express, NestJS, Prisma, TypeORM, Sequelize or Mongoose
project, and which collector signals routinely mislead in this stack.

## Finding the schema (R01, R02)

| ORM | Where the truth is | Watch for |
|---|---|---|
| TypeORM | `*.entity.ts` with `@Column`, plus `migrations/` | Entities and migrations drift apart. When `synchronize: true` is on in dev, the entity is the truth; in production with `migrationsRun`, the migrations are. Read both and report the mismatch if there is one |
| Prisma | `prisma/schema.prisma` | Single file, reliable. `@map` renames the column, so the DB name differs from the field name |
| Sequelize | `models/*.js` plus `migrations/` | `paranoid: true` means soft delete — directly relevant to R03 |
| Mongoose | `*.schema.ts` / `models/*.ts` | Schemaless writes are possible; a field can exist in the collection and nowhere in the code |
| Drizzle | `schema.ts` with `pgTable` | Types are inferred, so grep for the table builder |

Column decorators carry information beyond the name. `@Column({ select: false })` in
TypeORM means the field is not returned by default — that is a real minimisation
control and worth crediting in R08 or R10. `@Exclude()` from `class-transformer`
does the same at the serialisation layer.

## Finding the routes (R03, R04, R05)

**NestJS.** Decorators: `@Get @Post @Put @Patch @Delete` on methods, `@Controller('path')`
on the class. The class decorator is what gives a route its meaning, and it is
usually far above the method — always read up to the top of the class before deciding
what `@Delete(':id')` deletes.

Two NestJS patterns matter for privacy. A route reading the id from the JWT
(`@Request() req` then `req.user.userId`) is scoped to the subject; a route reading it
from `@Param('id')` without an ownership check is an IDOR and belongs in the report.
And `@UseGuards(JwtAuthGuard)` at class level protects every method below it — absence
of the decorator on a method does not mean the route is public.

**Express.** `router.get/post/put/patch/delete`, or `app.*`. Mount points in
`app.use('/users', router)` change the effective path, so the file alone does not tell
you the URL.

## Password hashing and secrets (R08, R09)

`bcrypt` and `bcryptjs` are both fine — `bcryptjs` is common in Alpine images where
the native build fails. Check the salt rounds; below 10 is worth a note.

Look for `crypto.createHash('md5')` and `crypto.createHash('sha1')` used on passwords
specifically. The same call on a file checksum is not a finding, so read what is being
hashed before reporting it.

Config comes from `process.env` via `dotenv` or `@nestjs/config`. Three places leak
secrets in practice: `docker-compose.yml` with literal values, a committed `.env`
(check `.gitignore`), and a fallback default in code — `process.env.JWT_SECRET || 'dev'`
is a production vulnerability wearing a convenience costume.

## Logs (R10)

`console.log` left in controllers is the usual culprit, especially around auth where
it prints the token or the whole user. Structured loggers — `winston`, `pino`, Nest's
`LoggingInterceptor` — often log the full request body, which means every field posted
to a signup form lands in the log.

## Third parties (R12)

Read `package.json` dependencies, not just imports: `@sentry/*`, `firebase`, `analytics`,
`posthog`, `mixpanel`, `@google-analytics/*`, `nodemailer` with an external SMTP,
`aws-sdk` / `@aws-sdk/*` with a region, `stripe`, `twilio`.

On the frontend side, check `index.html` and any script tags for tag managers and
pixels that never appear in `package.json`.

## Frequent false positives in this stack

- `export class` / `export const` — the word `export` is not a data export route
- `document.getElementById`, `document.querySelector` — DOM, not `documento`
- `HealthModule`, `HealthController`, `/health` — liveness probe, not health data
- `Delete` in a generic CRUD service used only for non-personal entities
- `deleted_at` on an entity that has nothing to do with people
- `mail` matching inside `mailer`, `email-template`, `sendmail`
