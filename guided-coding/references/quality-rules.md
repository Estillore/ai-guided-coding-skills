# Lean Quality Rules

These rules are applied only when the matching language or framework is present. Keep them short. Never list them all unless asked.

## TypeScript (when .ts / .tsx files or tsconfig is present)

- Treat the code as if `strict: true` is on.
- Prefer discriminated unions for different states instead of optional properties.
- Prefer `satisfies Type` over `as Type`.
- Prefer `unknown` + type narrowing over `any`.
- Use `import type { ... }` for type-only imports.
- Keep types as simple as possible. Add generics or advanced utility types only when they remove clear duplication that already exists in the project.

## React / Next.js (when React or Next.js is detected)

- Default to Server Components.
- Add `'use client'` only when the component truly needs browser APIs, event handlers, or client state.
- Fetch independent data in parallel (`Promise.all` or equivalent). Never create sequential waterfalls.
- Keep client components small.
- Prefer moving logic and data fetching to the server when it does not break the feature.
- Prefer native browser features or existing project utilities over new client-side libraries or complex state.

## Plain JavaScript

- Use only the Ponytail ladder.
- No additional rules.

## Switching between JavaScript and TypeScript

- Keep the same minimal file and function structure in both languages.
- The only differences should be the presence or absence of type annotations and the TypeScript rules above.
- A clean JavaScript implementation should convert to TypeScript with almost no structural changes.

## Vanilla PHP (when .php files are present)

- Start with `declare(strict_types=1);` whenever possible.
- Prefer typed parameters, return types, and typed properties.
- Prefer early returns and flat control flow over deep nesting.
- Reach for built-in PHP functions and the standard library before writing custom helpers.
- Prefer simple functions or small focused classes. Avoid large inheritance hierarchies or god classes unless the existing project already follows that style.
- Fail fast and explicitly. Throw exceptions or return clear error values. Never swallow errors silently.
- Keep each file focused on one clear responsibility. Do not introduce extra layers of abstraction.

## Database schema & queries

Treat schema and queries as one concern. The schema exists to make the current queries simple and correct.

**Schema**
- Smallest table that satisfies the *current* need (YAGNI). No speculative columns.
- Explicit primary key. Add foreign keys and indexes only for columns you actually query or join on.
- Prefer clear, readable DDL or the project’s existing migration style (Documentation-is-Truth).
- Avoid over-normalization and clever abstractions. Boring and obvious wins.
- Show the exact migration or `CREATE`/`ALTER` the human should type.

**Queries**
- Always use prepared statements or parameterized queries. Never concatenate user input into SQL.
- Prefer explicit column lists over `SELECT *`.
- Keep the first version of the query clear and readable. Optimize only after it works.
- Prefer simple JOINs + WHERE over deeply nested subqueries when both are correct.
- Put data access in a dedicated place (repository, query file, or data layer).
- Use transactions when multiple statements must succeed or fail together.

**Shared rules**
- Lazy ≠ negligent: keep real constraints (NOT NULL, unique, FK) and validation that protect data integrity.
- Schema is justified by real queries; queries stay simple because the schema is not over-engineered.
