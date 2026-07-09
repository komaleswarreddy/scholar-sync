#!/usr/bin/env node
/**
 * End-to-end verification for the notebook-creation-latency / missing-skeleton
 * fixes applied on 2026-07-06.
 *
 * Two kinds of checks:
 *   1. LIVE — hits the running backend (localhost:8000) and frontend
 *      (localhost:3000) and reports reachability + latency. Only unauthenticated
 *      routes are hit here: Clerk JWT verification is configured in this env
 *      (real JWKS check), so a script can't forge a session without real
 *      credentials — authenticated flows (create notebook, open notebook,
 *      chat) must still be manually re-tested in the browser.
 *   2. STATIC — asserts the actual source fixes are present in the files
 *      (not just "trust me"): the print()-encoding guard, the usage dict/object
 *      guard, the TutorModeLanding navigation reorder, and the notebook
 *      workspace skeleton wiring.
 *
 * Usage: node scripts/verify_latency_fixes.js
 * Exit code 0 = all checks passed, 1 = at least one failed.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000';
const FRONTEND = process.env.FRONTEND_URL || 'http://localhost:3000';

let failures = 0;
const results = [];

function record(name, pass, detail) {
  results.push({ name, pass, detail });
  const icon = pass ? 'PASS' : 'FAIL';
  console.log(`[${icon}] ${name}${detail ? ' - ' + detail : ''}`);
  if (!pass) failures += 1;
}

function readFile(relPath) {
  return fs.readFileSync(path.join(ROOT, relPath), 'utf8');
}

async function timedFetch(url, opts = {}) {
  const start = Date.now();
  try {
    const res = await fetch(url, { ...opts, signal: AbortSignal.timeout(10000) });
    return { ok: res.ok, status: res.status, ms: Date.now() - start };
  } catch (err) {
    return { ok: false, status: 0, ms: Date.now() - start, error: String(err) };
  }
}

async function runLiveChecks() {
  console.log('\n=== LIVE checks ===');

  const backendDocs = await timedFetch(`${BACKEND}/api/docs`);
  record(
    'Backend reachable (/api/docs)',
    backendDocs.ok,
    `status=${backendDocs.status} latency=${backendDocs.ms}ms`,
  );

  const backendHealth = await timedFetch(`${BACKEND}/api/v1/health`);
  // 401/404 still prove the server is alive and routing requests (this route
  // may require auth or have a different path) — only a network-level
  // failure (status 0) counts as truly unreachable.
  record(
    'Backend health endpoint reachable (routing works)',
    backendHealth.status > 0,
    `status=${backendHealth.status} latency=${backendHealth.ms}ms`,
  );

  const frontend = await timedFetch(FRONTEND);
  record(
    'Frontend reachable (/)',
    frontend.ok,
    `status=${frontend.status} latency=${frontend.ms}ms`,
  );

  // Repeat backend /api/docs 3x to sanity check there's no gross per-request
  // slowness (e.g. a stale zombie process re-introduced, DB pool exhaustion).
  const samples = [];
  for (let i = 0; i < 3; i += 1) {
    const r = await timedFetch(`${BACKEND}/api/docs`);
    samples.push(r.ms);
  }
  const maxSample = Math.max(...samples);
  record(
    'Backend latency stable across 3 requests',
    maxSample < 3000,
    `samples=[${samples.join(', ')}]ms`,
  );
}

function runStaticChecks() {
  console.log('\n=== STATIC checks (source-level assertions) ===');

  // 1. print() UnicodeEncodeError guard (main.py)
  const mainPy = readFile('apps/api/main.py');
  record(
    'main.py: sys.stdout/stderr forced to UTF-8 before first print',
    /sys\.stdout\.reconfigure\(encoding="utf-8"/.test(mainPy),
  );
  record(
    'main.py: flushed_print catches UnicodeEncodeError',
    /except UnicodeEncodeError:/.test(mainPy) && /_original_print\(\*safe_args/.test(mainPy),
  );

  // 2. usage dict-vs-object guard (openai_client.py)
  const openaiClient = readFile('packages/core/llm/openai_client.py');
  record(
    'openai_client.py: stream_generate handles dict-shaped usage',
    /isinstance\(chunk_usage, dict\)/.test(openaiClient),
  );
  record(
    'openai_client.py: generate() handles dict-shaped usage',
    /isinstance\(raw_usage, dict\)/.test(openaiClient),
  );

  // 3. TutorModeLanding navigation reorder (router.push before awaited work)
  const tutorLanding = readFile('apps/web/src/components/tutor/TutorModeLanding.tsx');
  const pushIdx = tutorLanding.indexOf('router.push(`/notebook/${slug}`)');
  const invalidateIdx = tutorLanding.indexOf('invalidateQueries({ queryKey: notebookKeys.lists()');
  const toastIdx = tutorLanding.lastIndexOf('showToast(');
  record(
    'TutorModeLanding: router.push happens before cache invalidation',
    pushIdx !== -1 && invalidateIdx !== -1 && pushIdx < invalidateIdx,
    `push@${pushIdx} invalidate@${invalidateIdx}`,
  );
  record(
    'TutorModeLanding: router.push happens before the toast call',
    pushIdx !== -1 && toastIdx !== -1 && pushIdx < toastIdx,
    `push@${pushIdx} toast@${toastIdx}`,
  );
  record(
    'TutorModeLanding: toast/invalidation are fire-and-forget (not awaited)',
    !/await showToast\(/.test(tutorLanding.slice(tutorLanding.indexOf('handlePrepareReady'), tutorLanding.indexOf('handlePrepareHardFail'))),
  );

  // 4. Notebook workspace skeleton wired into the page
  const notebookPage = readFile('apps/web/src/app/notebook/[slug]/page.tsx');
  record(
    'notebook/[slug]/page.tsx imports NotebookWorkspaceSkeleton',
    /import\s*\{\s*NotebookWorkspaceSkeleton\s*\}\s*from\s*'@\/components\/skeleton'/.test(notebookPage),
  );
  record(
    'notebook/[slug]/page.tsx renders skeleton (not bare text) while loading',
    /<NotebookWorkspaceSkeleton \/>/.test(notebookPage) && !/Loading notebook\.\.\./.test(notebookPage),
  );
  record(
    'NotebookWorkspaceSkeleton component file exists',
    fs.existsSync(path.join(ROOT, 'apps/web/src/components/skeleton/NotebookWorkspaceSkeleton.tsx')),
  );
  const skeletonIndex = readFile('apps/web/src/components/skeleton/index.ts');
  record(
    'NotebookWorkspaceSkeleton exported from skeleton barrel',
    /export \{ NotebookWorkspaceSkeleton \} from '\.\/NotebookWorkspaceSkeleton'/.test(skeletonIndex),
  );
}

async function main() {
  runStaticChecks();
  await runLiveChecks();

  console.log('\n=== Summary ===');
  const passed = results.filter((r) => r.pass).length;
  console.log(`${passed}/${results.length} checks passed.`);
  if (failures > 0) {
    console.log(`${failures} check(s) FAILED — see [FAIL] lines above.`);
    console.log(
      '\nNote: authenticated flows (create notebook, open existing notebook, chat) ' +
        'require a real Clerk session and cannot be scripted headlessly here — ' +
        'please re-verify those manually in the browser.',
    );
    process.exit(1);
  } else {
    console.log(
      '\nAll scripted checks passed. Authenticated flows (create notebook, open ' +
        'existing notebook, chat) still need a manual browser pass since Clerk ' +
        'JWT verification is enabled in this environment.',
    );
    process.exit(0);
  }
}

main();
