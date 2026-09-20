# Stack notes: Java / Spring

Where each thing lives in a Spring Boot project with JPA/Hibernate, and which
collector signals routinely mislead in this stack.

## Finding the schema (R01, R02)

The entity is `@Entity` on a class, usually with `@Table(name = "...")`, and fields
carrying `@Column`. Read the annotations, not only the field names — `@Column(name =
"num_doc")` means the database column and the Java field have different names, and
the report should cite whichever the reader will search for.

Migrations live in one of two places:

- **Flyway** — `src/main/resources/db/migration/V1__*.sql`, plain SQL, easy to read
- **Liquibase** — `db/changelog/*.xml` or `*.yaml`, more indirection to follow

`spring.jpa.hibernate.ddl-auto` in `application.yml` decides whether the entity or the
migration is the source of truth. `update` or `create` means Hibernate is writing the
schema; `validate` or `none` means the migrations are. This matters because the two
drift, and the report should audit the one that actually runs in production.

Annotations worth crediting when present: `@Convert(converter = ...)` implementing an
`AttributeConverter` that encrypts a column, and `@JsonIgnore` keeping a field out of
API responses.

## Finding the routes (R03, R04, R05)

`@RestController` or `@Controller` on the class, `@RequestMapping("/users")` giving the
base path, then `@GetMapping @PostMapping @PutMapping @PatchMapping @DeleteMapping` on
methods. As in Nest, the class-level annotation is what gives a method its meaning, so
read to the top of the class.

Scoping to the authenticated subject looks like `@AuthenticationPrincipal`,
`SecurityContextHolder.getContext().getAuthentication()`, or a `Principal` parameter. A
`@DeleteMapping("/{id}")` that takes the id straight from the path with no ownership
check is an IDOR — report it under the requirement it undermines.

Also check for Spring Data REST (`@RepositoryRestResource`), which exposes full CRUD
over entities without anyone writing a controller. It is easy to miss and often
exposes more than intended.

## Password hashing and security config (R08)

The security configuration is a `@Configuration` class, historically extending
`WebSecurityConfigurerAdapter`, now declaring a `SecurityFilterChain` bean. Inside it:

- `BCryptPasswordEncoder` or `Argon2PasswordEncoder` — fine
- `NoOpPasswordEncoder` — plaintext passwords, high severity, always report
- `MessageDigest.getInstance("MD5"|"SHA-1")` applied to a password — high severity
- `.csrf().disable()` combined with cookie-based auth — worth a note
- `permitAll()` on a matcher that covers personal data endpoints — read carefully

## Secrets (R09)

`application.properties` and `application.yml` are the usual leak, especially
`spring.datasource.password=` with a literal value, committed alongside the code.
Profile-specific files (`application-prod.yml`) are worth opening even when the
default file is clean.

`@Value("${db.password:changeme}")` embeds a default in the source — the fallback after
the colon is a hardcoded secret.

## Records of processing (R11)

Spring gives you real options here, so their absence is more notable than in other
stacks: Hibernate Envers (`@Audited`), JPA auditing (`@CreatedBy`, `@LastModifiedBy`,
`@EntityListeners(AuditingEntityListener.class)`), or an explicit audit table. Spring
Boot Actuator's `httptrace` endpoint is not an audit trail — it is an in-memory ring
buffer.

## Third parties (R12)

Read `pom.xml` or `build.gradle` dependencies, and the outbound HTTP clients:
`RestTemplate`, `WebClient`, `FeignClient` (`@FeignClient(url = ...)`). Check
`application.yml` for external hosts, AWS regions, and SDK configuration.

## Frequent false positives in this stack

- `/actuator/health`, `HealthIndicator`, `HealthContributor` — not health data
- `@DeleteMapping` on an admin CRUD for reference data
- `getDocument`, `DocumentService` — document management, not `documento` as ID
- `Cipher.getInstance` in a test fixture or a utility never wired up
- `spring.datasource.password=${DB_PASSWORD}` — that is a reference, not a secret
- `@Column(name = "genero")` on a product catalogue meaning genre, not gender
