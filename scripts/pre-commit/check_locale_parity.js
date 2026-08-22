#!/usr/bin/env node

/**
 * Fails when the locale trees under frontend/src/locales/ have drifted apart.
 *
 * CLAUDE.md requires every user-facing string to exist in both `en` and `de`.
 * The sibling `sort_locales.js` hook only sorts keys — it never compares the
 * trees, so a key added to one locale and forgotten in the other shipped to
 * production and rendered as the raw dotted path for those users.
 *
 * Checks, in order of how loudly they break at runtime:
 *
 *   1. file parity        a namespace file present in one locale, missing in another
 *   2. key parity         a key present in one locale, missing in another
 *   3. type mismatch      object in one locale, string in the other — this breaks
 *                         vue-i18n outright rather than falling back
 *   4. empty value        a key that exists but renders as nothing
 *   5. placeholder drift  `{count}` in en but not de — the number silently vanishes
 *   6. plural branch drift  "a | b" vs "a" — vue-i18n picks a branch that isn't
 *                         there, so the wrong text (or none) is shown
 *
 * Deliberately dependency-free so it can run as a `language: node` pre-commit
 * hook with no install step, matching `sort_locales.js`.
 *
 * Usage:  node scripts/pre-commit/check_locale_parity.js
 * Exit:   0 = locales agree, 1 = drift found (details on stdout)
 */

const fs = require("fs");
const path = require("path");

const LOCALES_DIR = path.join(__dirname, "../../frontend/src/locales");

/** Flatten a nested locale object into a Map of dotted path -> leaf value. */
function flatten(obj, prefix = "", out = new Map()) {
    for (const [key, value] of Object.entries(obj)) {
        const dotted = prefix ? `${prefix}.${key}` : key;
        if (value !== null && typeof value === "object" && !Array.isArray(value)) {
            flatten(value, dotted, out);
        } else {
            out.set(dotted, value);
        }
    }
    return out;
}

/** Describe a leaf's type the way vue-i18n cares about it. */
function typeOf(value) {
    if (Array.isArray(value)) return "array";
    if (value === null) return "null";
    return typeof value;
}

/**
 * Named interpolation placeholders, e.g. `{count}`.
 *
 * vue-i18n also supports literal `{'@'}` escapes; those carry quotes and are
 * not identifiers, so the `\w+` bound below skips them rather than reporting a
 * phantom placeholder.
 */
function placeholders(value) {
    const found = new Set();
    if (typeof value !== "string") return found;
    for (const match of value.matchAll(/\{\s*(\w+)\s*\}/g)) {
        found.add(match[1]);
    }
    return found;
}

/** Number of pluralization branches, split on the vue-i18n `|` separator. */
function pluralBranches(value) {
    if (typeof value !== "string") return 1;
    return value.split("|").length;
}

/**
 * Locale sub-directories, with the reference locale first.
 *
 * Differences are reported relative to the first entry, so `en` leads when it
 * exists: it is the source language here, and "de is missing {count}" is a far
 * more actionable message than the alphabetical accident of the reverse.
 */
function readLocales() {
    const found = fs
        .readdirSync(LOCALES_DIR, { withFileTypes: true })
        .filter((entry) => entry.isDirectory())
        .map((entry) => entry.name)
        .sort();
    return found.includes("en") ? ["en", ...found.filter((l) => l !== "en")] : found;
}

function jsonFilesIn(locale) {
    return fs
        .readdirSync(path.join(LOCALES_DIR, locale))
        .filter((name) => name.endsWith(".json"))
        .sort();
}

function main() {
    const locales = readLocales();

    if (locales.length < 2) {
        console.log(
            `Only ${locales.length} locale directory found in ${LOCALES_DIR} — nothing to compare.`,
        );
        return 0;
    }

    const problems = [];

    // ── 1. File parity ────────────────────────────────────────────────────
    const filesByLocale = new Map(locales.map((l) => [l, new Set(jsonFilesIn(l))]));
    const allFiles = new Set([...filesByLocale.values()].flatMap((s) => [...s]));

    for (const file of [...allFiles].sort()) {
        const missingIn = locales.filter((l) => !filesByLocale.get(l).has(file));
        if (missingIn.length) {
            problems.push({
                kind: "missing file",
                detail: `${file} is missing from: ${missingIn.join(", ")}`,
            });
        }
    }

    // Only compare files that every locale actually has; a missing file is
    // already reported above and would otherwise produce hundreds of
    // "missing key" lines that all share one root cause.
    const sharedFiles = [...allFiles]
        .filter((file) => locales.every((l) => filesByLocale.get(l).has(file)))
        .sort();

    for (const file of sharedFiles) {
        const trees = new Map();
        for (const locale of locales) {
            const raw = fs.readFileSync(path.join(LOCALES_DIR, locale, file), "utf8");
            let parsed;
            try {
                parsed = JSON.parse(raw);
            } catch (error) {
                problems.push({
                    kind: "invalid JSON",
                    detail: `${locale}/${file}: ${error.message}`,
                });
                continue;
            }
            trees.set(locale, flatten(parsed));
        }
        if (trees.size !== locales.length) continue;

        const allKeys = new Set([...trees.values()].flatMap((t) => [...t.keys()]));

        for (const key of [...allKeys].sort()) {
            // ── 2. Key parity ─────────────────────────────────────────────
            const missingIn = locales.filter((l) => !trees.get(l).has(key));
            if (missingIn.length) {
                // Distinguish a genuinely absent key from a STRUCTURAL mismatch:
                // if a locale has no leaf at `key` but does have keys beneath
                // `key.`, then that locale nests an object where the other holds
                // a string. Flattening makes both look like ordinary missing
                // keys, but vue-i18n breaks outright on this rather than falling
                // back, so it deserves its own diagnosis.
                const nestedIn = missingIn.filter((l) =>
                    [...trees.get(l).keys()].some((k) => k.startsWith(`${key}.`)),
                );
                if (nestedIn.length) {
                    const leafIn = locales.filter((l) => trees.get(l).has(key));
                    problems.push({
                        kind: "structural mismatch",
                        detail:
                            `${file} :: ${key} — string in ${leafIn.join(", ")}, ` +
                            `nested object in ${nestedIn.join(", ")}`,
                        hint: "vue-i18n fails on this at runtime; it does not fall back",
                    });
                    continue;
                }
                for (const locale of missingIn) {
                    const present = locales.find((l) => trees.get(l).has(key));
                    problems.push({
                        kind: "missing key",
                        locale,
                        detail: `${locale}/${file} :: ${key}`,
                        hint: `present in ${present} as ${JSON.stringify(trees.get(present).get(key))}`,
                    });
                }
                continue;
            }

            const values = new Map(locales.map((l) => [l, trees.get(l).get(key)]));
            const [reference, ...others] = locales;
            const refValue = values.get(reference);

            // ── 3. Type mismatch ──────────────────────────────────────────
            for (const locale of others) {
                if (typeOf(values.get(locale)) !== typeOf(refValue)) {
                    problems.push({
                        kind: "type mismatch",
                        detail:
                            `${file} :: ${key} — ${reference} is ${typeOf(refValue)}, ` +
                            `${locale} is ${typeOf(values.get(locale))}`,
                    });
                }
            }

            // ── 4. Empty value ────────────────────────────────────────────
            for (const locale of locales) {
                const value = values.get(locale);
                if (typeof value === "string" && value.trim() === "") {
                    problems.push({
                        kind: "empty value",
                        locale,
                        detail: `${locale}/${file} :: ${key}`,
                    });
                }
            }

            // ── 5. Placeholder drift ──────────────────────────────────────
            const refPlaceholders = placeholders(refValue);
            for (const locale of others) {
                const mine = placeholders(values.get(locale));
                const missing = [...refPlaceholders].filter((p) => !mine.has(p));
                const extra = [...mine].filter((p) => !refPlaceholders.has(p));
                if (missing.length || extra.length) {
                    const parts = [];
                    if (missing.length) parts.push(`missing {${missing.join("}, {")}}`);
                    if (extra.length) parts.push(`unexpected {${extra.join("}, {")}}`);
                    problems.push({
                        kind: "placeholder mismatch",
                        detail: `${file} :: ${key} — ${locale} ${parts.join("; ")} (vs ${reference})`,
                    });
                }
            }

            // ── 6. Plural branch drift ────────────────────────────────────
            const refBranches = pluralBranches(refValue);
            for (const locale of others) {
                const mine = pluralBranches(values.get(locale));
                if (mine !== refBranches) {
                    problems.push({
                        kind: "plural branch mismatch",
                        detail:
                            `${file} :: ${key} — ${reference} has ${refBranches} branch(es), ` +
                            `${locale} has ${mine}`,
                    });
                }
            }
        }
    }

    // ── Report ────────────────────────────────────────────────────────────
    if (problems.length === 0) {
        const keyCount = sharedFiles.reduce((total, file) => {
            const raw = fs.readFileSync(path.join(LOCALES_DIR, locales[0], file), "utf8");
            return total + flatten(JSON.parse(raw)).size;
        }, 0);
        console.log(
            `Locale parity OK — ${locales.join("/")} agree across ` +
                `${sharedFiles.length} files and ${keyCount} keys.`,
        );
        return 0;
    }

    const byKind = new Map();
    for (const problem of problems) {
        if (!byKind.has(problem.kind)) byKind.set(problem.kind, []);
        byKind.get(problem.kind).push(problem);
    }

    console.error(`Locale parity check FAILED — ${problems.length} problem(s):\n`);
    for (const [kind, items] of byKind) {
        console.error(`  ${kind} (${items.length}):`);
        for (const item of items) {
            console.error(`    ${item.detail}`);
            if (item.hint) console.error(`      ${item.hint}`);
        }
        console.error("");
    }
    console.error(
        "Add the missing keys to the locale files listed above, then re-run.\n" +
            "Both frontend/src/locales/en/ and frontend/src/locales/de/ must define every key.",
    );
    return 1;
}

process.exit(main());
