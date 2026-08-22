# Locale files (vue-i18n)

Message values are **not** plain strings — vue-i18n compiles them, and three
characters are syntax. Getting one wrong does not fall back gracefully: the
whole page dies inside the error boundary with `Message compilation error`, at
runtime, only on the screen that renders that key.

## Characters that must be escaped

| Char | vue-i18n reads it as | Write instead |
|------|----------------------|---------------|
| `@`  | linked message (`@:other.key`) | `{'@'}` |
| `\|` | plural separator | `{'\|'}` |
| `{`  | interpolation slot | `{'{'}` |

The escape is *literal interpolation*: `{'…'}` emits the quoted text verbatim.

```jsonc
// wrong — dies with "Invalid linked format"
"emailsPlaceholder": "anna@example.com, ben@example.com"
// right
"emailsPlaceholder": "anna{'@'}example.com, ben{'@'}example.com"
```

This one is easy to miss because the key looks harmless in review and no test
touches it until something renders that exact component. If you add a message
containing a literal email address, URL with `@`, or a table-ish string with
pipes, escape it.

## Pluralisation

Plural forms are pipe-separated and chosen by the count passed as the third
argument to `t()`:

```jsonc
"count": "no people | 1 person | {count} people"
```

```ts
t('duties.events.members.count', { count: n }, n)
//                                             ^ required, or you always get form 0
```

Two forms mean `singular | plural`; three mean `zero | singular | plural`.

## Both locales, always

`en/` and `de/` must contain exactly the same key set. A pre-commit hook
(`scripts/pre-commit/check_locale_parity.js`, also run by `just check-locales`)
fails the commit on any asymmetry — including a key present in one file with a
nested object in the other.

German is a real translation, not a copy of the English. Prefer the informal
"du" form and plain wording; avoid technical jargon in user-facing strings.

## Formatting is automated

A pre-commit hook sorts these files alphabetically and rewrites them. Do not
hand-order keys or fight the sort — just add the key and let the hook place it.

## Checking your work

Locale parity is enforced automatically, but nothing checks that a key you
referenced actually *exists*. A missing key renders as the raw key path, silently.
To sweep for literal `t('…')` calls with no matching entry:

```bash
node scripts/pre-commit/check_locale_parity.js   # en/de symmetry
just check-locales                               # same, via the justfile
```

Two keys are known-missing and pre-date the current work
(`dashboard.home.calendar.filters.events`, `duties.tasks.createView.eventDateHint`).
