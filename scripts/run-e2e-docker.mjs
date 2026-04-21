#!/usr/bin/env node

/**
 * Build Docker services, start the full stack, and run Playwright E2E tests.
 *
 * Script-specific flags (consumed here):
 *   --up-only, --down, --no-build, --no-teardown
 *
 * Everything else is forwarded verbatim to `npx playwright test`. So you can
 * pass test paths, --grep, --headed, --project=chromium, etc.:
 *
 *   node scripts/run-e2e-docker.mjs                                  # full run
 *   node scripts/run-e2e-docker.mjs tests/authenticated/tasks.spec.ts
 *   node scripts/run-e2e-docker.mjs --grep "login"
 *   node scripts/run-e2e-docker.mjs --headed --project=chromium tests/authenticated/events.spec.ts
 *   node scripts/run-e2e-docker.mjs --up-only
 *   node scripts/run-e2e-docker.mjs --down
 *   node scripts/run-e2e-docker.mjs --no-build
 *   node scripts/run-e2e-docker.mjs --no-teardown
 */

import { execSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import http from 'node:http';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const COMPOSE_FILE = resolve(REPO_ROOT, 'docker-compose.e2e.yml');
const PROJECT_NAME = 'wirksam-e2e';
const FRONTEND_PORT = 5555;
const BACKEND_PORT = 8787;

// ── Parse CLI args ───────────────────────────────────────────────────

const args = process.argv.slice(2);
let noBuild = false;
let noTeardown = false;
let upOnly = false;
let down = false;
/** Args forwarded verbatim to `npx playwright test`. */
const playwrightArgs = [];

const SCRIPT_FLAGS = new Set(['--up-only', '--down', '--no-build', '--no-teardown']);

for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (SCRIPT_FLAGS.has(arg)) {
        switch (arg) {
            case '--up-only':     upOnly = true; noTeardown = true; break;
            case '--down':        down = true; break;
            case '--no-build':    noBuild = true; break;
            case '--no-teardown': noTeardown = true; break;
        }
    } else {
        playwrightArgs.push(arg);
    }
}

// ── Helpers ──────────────────────────────────────────────────────────

function run(cmd, opts = {}) {
    console.log(`  $ ${cmd}`);
    execSync(cmd, { stdio: 'inherit', cwd: REPO_ROOT, ...opts });
}

function compose(subcmd) {
    run(`docker compose -p ${PROJECT_NAME} -f "${COMPOSE_FILE}" ${subcmd}`);
}

/** Run a command and return its exit code (don't throw on failure). */
function runForExitCode(cmd, opts = {}) {
    console.log(`  $ ${cmd}`);
    try {
        execSync(cmd, { stdio: 'inherit', cwd: REPO_ROOT, ...opts });
        return 0;
    } catch (e) {
        return e.status ?? 1;
    }
}

function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
}

/** Poll a URL until it returns 2xx. */
async function waitForUrl(url, label, { maxAttempts = 30, intervalMs = 5000 } = {}) {
    console.log(`==> Waiting for ${label} at ${url} ...`);
    for (let i = 1; i <= maxAttempts; i++) {
        const ok = await new Promise((resolve) => {
            const req = http.get(url, { timeout: 10_000 }, (res) => {
                res.resume(); // drain
                resolve(res.statusCode >= 200 && res.statusCode < 400);
            });
            req.on('error', () => resolve(false));
            req.on('timeout', () => { req.destroy(); resolve(false); });
        });

        if (ok) {
            console.log(`    ${label} ready (attempt ${i}/${maxAttempts})`);
            return;
        }
        if (i === maxAttempts) {
            throw new Error(`${label} failed to become ready after ${maxAttempts} attempts`);
        }
        console.log(`    Waiting... (attempt ${i}/${maxAttempts})`);
        await sleep(intervalMs);
    }
}

const LOGS_DIR = resolve(REPO_ROOT, 'e2e-logs');
const SERVICES_TO_LOG = ['db', 'prestart', 'backend', 'frontend', 'mailcatcher'];

function collectLogs() {
    try {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const runDir = resolve(LOGS_DIR, timestamp);
        mkdirSync(runDir, { recursive: true });

        console.log(`==> Collecting container logs to ${runDir} ...`);
        const composePrefix = `docker compose -p ${PROJECT_NAME} -f "${COMPOSE_FILE}"`;

        for (const svc of SERVICES_TO_LOG) {
            try {
                const logs = execSync(`${composePrefix} logs --no-color ${svc}`, {
                    encoding: 'utf8',
                    cwd: REPO_ROOT,
                    stdio: ['pipe', 'pipe', 'pipe'],
                    timeout: 15_000,
                });
                writeFileSync(resolve(runDir, `${svc}.log`), logs);
            } catch { /* service may not exist */ }
        }

        console.log(`    Logs saved to ${runDir}`);
    } catch (e) {
        console.log(`    Warning: failed to collect logs: ${e.message}`);
    }
}

function teardown() {
    collectLogs();
    try {
        console.log('==> Tearing down services...');
        run(`docker compose -p ${PROJECT_NAME} -f "${COMPOSE_FILE}" down --remove-orphans -v`);
    } catch { /* best-effort */ }
}

// ── Handle --down ────────────────────────────────────────────────────

if (down) {
    teardown();
    process.exit(0);
}

// ── Pre-flight checks ────────────────────────────────────────────────

const envFile = resolve(REPO_ROOT, '.env');
if (!existsSync(envFile)) {
    console.error('ERROR: .env file not found at project root.');
    console.error('Copy .env.example to .env and fill in at least the Auth0 values.');
    process.exit(1);
}

// ── Register cleanup ─────────────────────────────────────────────────

if (!noTeardown) {
    process.on('SIGINT', () => { teardown(); process.exit(130); });
    process.on('SIGTERM', () => { teardown(); process.exit(143); });
}

let failed = false;

try {
    // ── 1. Build images ──────────────────────────────────────────────

    if (!noBuild) {
        console.log('==> Building Docker images (this may take a while on first run) ...');
        compose('build');
    }

    // ── 2. Start services ────────────────────────────────────────────

    console.log('==> Starting services ...');
    compose('up -d');

    // Wait for PostgreSQL via Docker healthcheck
    console.log('==> Waiting for PostgreSQL ...');
    for (let i = 1; i <= 30; i++) {
        try {
            const out = execSync(
                `docker compose -p ${PROJECT_NAME} -f "${COMPOSE_FILE}" ps db --format "{{.Health}}"`,
                { encoding: 'utf8', cwd: REPO_ROOT, stdio: ['pipe', 'pipe', 'pipe'] },
            ).trim().replace(/"/g, '');
            if (out.toLowerCase().includes('healthy')) {
                console.log(`    PostgreSQL healthy (attempt ${i}/30)`);
                break;
            }
        } catch { /* container may not exist yet */ }
        if (i === 30) {
            compose('logs db --tail=30');
            throw new Error('PostgreSQL did not become healthy');
        }
        console.log(`    Waiting... (attempt ${i}/30)`);
        await sleep(3000);
    }

    await waitForUrl(`http://127.0.0.1:${BACKEND_PORT}/api/v1/healthz`, 'Backend', {
        maxAttempts: 40,
        intervalMs: 10_000,
    });

    await waitForUrl(`http://127.0.0.1:${FRONTEND_PORT}`, 'Frontend', {
        maxAttempts: 20,
        intervalMs: 5000,
    });

    console.log('==> All services ready');

    // ── 3. Run Playwright tests ──────────────────────────────────────

    if (upOnly) {
        console.log('\n==> Services running. Stop with: just e2e-down');
        console.log(`    Frontend: http://localhost:${FRONTEND_PORT}`);
        console.log(`    Backend:  http://localhost:${BACKEND_PORT}/api/v1`);
        console.log(`    Mailcatcher: http://localhost:1080`);
        process.exit(0);
    }

    const frontendDir = resolve(REPO_ROOT, 'frontend');
    const testEnv = {
        ...process.env,
        VITE_API_URL: `http://localhost:${BACKEND_PORT}/api/v1`,
        VITE_E2E_AUTH_BYPASS: 'true',
        MAILCATCHER_HOST: 'http://localhost:1080',
        // Prevent the HTML report server from blocking teardown
        PLAYWRIGHT_HTML_OPEN: 'never',
    };

    const quote = (s) => (/[\s"'`$|<>()&;*?!]/.test(s) ? `"${s.replace(/"/g, '\\"')}"` : s);
    const extraArgs = playwrightArgs.map(quote).join(' ');
    const cmd = extraArgs ? `npx playwright test ${extraArgs}` : 'npx playwright test';
    console.log(`\n==> Running Playwright tests ...`);
    const code = runForExitCode(cmd, { cwd: frontendDir, env: testEnv });
    if (code !== 0) failed = true;

    if (failed) {
        console.log('\n==> Tests FAILED');
    } else {
        console.log('\n==> All tests passed');
    }
} finally {
    if (!noTeardown && !upOnly) {
        teardown();
    } else {
        console.log('\n==> Services left running. Stop with: just e2e-down');
    }
    if (failed) process.exit(1);
}
