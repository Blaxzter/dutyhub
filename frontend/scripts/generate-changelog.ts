/**
 * Pre-processes changelog markdown files into JSON per locale.
 *
 * Reads:   src/changelog/{en,de}/*.md
 * Writes:  src/changelog/generated/{en,de}.json
 *
 * Each JSON file contains a sorted array of:
 *   { title, version, date, html }
 *
 * Image paths (./images/...) are left as-is — the component resolves
 * them via Vite's import.meta.glob at runtime.
 *
 * Run: pnpm generate-changelog
 */

import { readFileSync, writeFileSync, readdirSync, mkdirSync, existsSync } from 'node:fs'
import { join, resolve } from 'node:path'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, linkify: true })

const CHANGELOG_DIR = resolve(import.meta.dirname, '../src/changelog')
const OUTPUT_DIR = join(CHANGELOG_DIR, 'generated')
const LOCALES = ['en', 'de']

interface ChangelogEntry {
  title: string
  version: string
  date: string
  html: string
}

function parseFrontmatter(raw: string): { meta: Record<string, string>; content: string } {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/)
  if (!match) return { meta: {}, content: raw }
  const meta: Record<string, string> = {}
  for (const line of match[1].split('\n')) {
    const idx = line.indexOf(':')
    if (idx > 0) {
      meta[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
    }
  }
  return { meta, content: match[2] }
}

function processLocale(locale: string): ChangelogEntry[] {
  const dir = join(CHANGELOG_DIR, locale)
  if (!existsSync(dir)) return []

  const files = readdirSync(dir).filter((f) => f.endsWith('.md')).sort()
  const entries: ChangelogEntry[] = []

  for (const file of files) {
    const raw = readFileSync(join(dir, file), 'utf-8')
    const { meta, content } = parseFrontmatter(raw)
    if (!meta.title || !meta.version || !meta.date) {
      console.warn(`  Skipping ${locale}/${file}: missing frontmatter fields`)
      continue
    }
    entries.push({
      title: meta.title,
      version: meta.version,
      date: meta.date,
      html: md.render(content),
    })
  }

  // Sort newest first
  entries.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  return entries
}

// Ensure output directory exists
mkdirSync(OUTPUT_DIR, { recursive: true })

for (const locale of LOCALES) {
  const entries = processLocale(locale)
  const outPath = join(OUTPUT_DIR, `${locale}.json`)
  writeFileSync(outPath, JSON.stringify(entries, null, 2))
  console.log(`${locale}: ${entries.length} entries → ${outPath}`)
}

console.log('Done.')
