#!/usr/bin/env node
/**
 * scripts/update-stats.mjs
 *
 * Fetches live GitHub stats for the profile owner and rewrites the
 * "- GitHub Stats -" section of README.md in place, preserving the ASCII-art
 * banner: each stat is appended to an existing art row at the same bullet
 * column, so the art itself is never modified.
 *
 * Zero runtime dependencies — Node 18+ only (global fetch, node: built-ins).
 *
 * Usage:
 *   GITHUB_TOKEN=... node scripts/update-stats.mjs            # real data
 *   node scripts/update-stats.mjs --mock                      # sample data, no network
 *   node scripts/update-stats.mjs --no-lines                  # skip the slow repo-cloning line count
 *   node scripts/update-stats.mjs --svg-labels                # render labels as inline SVG images (colors show on GitHub)
 *   node scripts/update-stats.mjs --readme path/to/README.md  # custom README path
 *
 * Behavior:
 *   - Exits 0 and writes nothing when the stats are unchanged.
 *   - On any unrecoverable API error it exits 1 WITHOUT touching the README,
 *     so the last-known stats stay on the profile.
 *   - Without a token, REST-only stats still work (rate-limited); the
 *     "Contributed" and "Contributions (12mo)" rows are omitted.
 */

import { readFileSync, writeFileSync, statSync, mkdirSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const OWNER = 'Drakaniia';
const API = 'https://api.github.com';
const TOKEN = process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN ?? '';

const MOCK = process.argv.includes('--mock');
// Counting lines requires cloning every repo (~1-2 min on CI, slower on a slow
// connection). Pass --no-lines to skip it — the "Lines of Code" row is omitted.
const NO_LINES = process.argv.includes('--no-lines');
// GitHub strips the color attribute from <font>/<span> tags, so colored text
// renders white there. Pass --svg-labels to render each label as an inline
// SVG image (data: URI), which GitHub does render in color. Values stay text.
const SVG_LABELS = process.argv.includes('--svg-labels');
const README_PATH = process.argv.includes('--readme')
  ? process.argv[process.argv.indexOf('--readme') + 1]
  : 'README.md';

// ---------------------------------------------------------------------------
// Colors & formatting (mirror the existing README style)
// ---------------------------------------------------------------------------
const GREEN = '#00FF88';
const WHITE = '#FFFFFF';
const CYAN = '#00E5FF';
const ORANGE = '#FFAA00';

const fmt = (n) => (Number(n) ?? 0).toLocaleString('en-US');

// Monospace advance width at GitHub's 12px code font (~0.6em), used so the SVG
// label image occupies exactly the same width as the text it replaces.
const CHAR_W = 7.2;
const LINE_H = 14;

function svgLabelImage(label, color) {
  const w = Math.ceil(label.length * CHAR_W);
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${LINE_H}">` +
    `<text x="0" y="11" fill="${color}" font-family="monospace, sans-serif" font-size="12">${label}</text></svg>`;
  const src = 'data:image/svg+xml;base64,' + Buffer.from(svg, 'utf8').toString('base64');
  return `<img src="${src}" alt="${label}" width="${w}" height="${LINE_H}">`;
}

function statLine(label, value, labelColor = GREEN) {
  // Dots pad the label so every value starts at the same column (matches the
  // original 3 stat lines, where label + dots = 26 chars).
  const dots = '.'.repeat(Math.max(1, 26 - label.length));
  const labelHtml = SVG_LABELS ? svgLabelImage(label, labelColor) : `<font color="${labelColor}">${label}</font>`;
  return `. ${labelHtml}${dots} <font color="${WHITE}">${value}</font>`;
}

// ---------------------------------------------------------------------------
// GitHub API helpers (REST + GraphQL)
// ---------------------------------------------------------------------------
async function api(path, opts = {}) {
  const headers = { Accept: 'application/vnd.github+json', ...(opts.headers ?? {}) };
  if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub API ${res.status} for ${path}: ${body.slice(0, 300)}`);
  }
  return res;
}

async function fetchUser() {
  const res = await api(`/users/${OWNER}`);
  const u = await res.json();
  return { repos: u.public_repos, followers: u.followers };
}

async function fetchOwnedRepos() {
  const repos = [];
  for (let page = 1; page <= 10; page++) {
    const res = await api(`/users/${OWNER}/repos?per_page=100&page=${page}&type=owner`);
    const batch = await res.json();
    if (!Array.isArray(batch)) throw new Error(`Unexpected repos response: ${JSON.stringify(batch).slice(0, 200)}`);
    repos.push(...batch);
    if (batch.length < 100) break;
  }
  return repos;
}

// Forked repos contain other people's code — exclude them from the personal
// stats (stars, commits, lines, languages). The displayed repo count matches.
async function fetchNonForkRepos() {
  const repos = await fetchOwnedRepos();
  return repos.filter((r) => !r.fork);
}

// Commit count on the default branch: request 1 commit per page and read the
// Link header's rel="last" page number (== total when per_page=1).
async function fetchCommitCount(repo) {
  const res = await api(`/repos/${OWNER}/${repo}/commits?per_page=1`);
  const link = res.headers.get('link') ?? '';
  const m = link.match(/page=(\d+)>; rel="last"/);
  if (m) return Number(m[1]);
  const body = await res.json();
  return Array.isArray(body) && body.length > 0 ? 1 : 0;
}

async function fetchLanguages(repo) {
  const res = await api(`/repos/${OWNER}/${repo}/languages`);
  return res.json(); // { "TypeScript": 12345, ... }
}

// Distinct public repos (outside OWNER's own account) with commits authored by
// OWNER. Paginates the commits search API, capped at 10 pages / 1000 commits.
async function fetchContributedRepoCount() {
  if (!TOKEN) return null; // commits search requires authentication
  const distinct = new Set();
  for (let page = 1; page <= 10; page++) {
    const res = await api(`/search/commits?q=author:${OWNER}&per_page=100&page=${page}`, {
      headers: { Accept: 'application/vnd.github.cloak-preview+json' },
    });
    const data = await res.json();
    for (const item of data.items ?? []) {
      const repo = item.repository;
      if (repo?.owner?.login !== OWNER) distinct.add(repo.full_name);
    }
    const got = (data.items ?? []).length;
    if (got === 0 || got < 100 || page * 100 >= (data.total_count ?? 0)) break;
  }
  return distinct.size;
}

// Contribution count over the last 365 days (the contribution-graph total).
async function fetchContributions12mo() {
  if (!TOKEN) return null; // GraphQL requires authentication
  const query = `query { user(login: "${OWNER}") { contributionsCollection { contributionCalendar { totalContributions } } } }`;
  const res = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`GitHub GraphQL ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  if (data.errors) throw new Error(`GitHub GraphQL errors: ${JSON.stringify(data.errors)}`);
  return data.data?.user?.contributionsCollection?.contributionCalendar?.totalContributions ?? 0;
}

// ---------------------------------------------------------------------------
// Lines of code: shallow-clone each repo and count lines in the working tree.
// ---------------------------------------------------------------------------
const BINARY_EXT = new Set([
  'png', 'jpg', 'jpeg', 'gif', 'webp', 'ico', 'bmp', 'tif', 'tiff', 'avif', 'svg',
  'pdf', 'zip', 'gz', 'tar', '7z', 'rar', 'woff', 'woff2', 'ttf', 'otf', 'eot',
  'mp3', 'mp4', 'mov', 'avi', 'webm', 'mkv', 'wav', 'flac', 'ogg',
  'exe', 'dll', 'so', 'dylib', 'class', 'jar', 'pyc', 'o', 'a', 'wasm',
  'db', 'sqlite', 'sqlite3', 'lockb',
]);

function countLinesInWorkingTree(repo) {
  const dir = join(tmpdir(), `ghstats-${OWNER}-${repo}-${process.pid}`);
  mkdirSync(dir, { recursive: true });
  try {
    execFileSync(
      'git',
      ['clone', '--depth', '1', '--quiet', `https://github.com/${OWNER}/${repo}.git`, dir],
      { stdio: 'ignore', timeout: 300000 }
    );
    const files = execFileSync('git', ['-C', dir, 'ls-files', '-z'], { encoding: 'buffer' })
      .toString()
      .split('\0')
      .filter(Boolean);
    let total = 0;
    for (const f of files) {
      const base = f.split('/').pop() ?? '';
      if (base === 'node_modules' || f.includes('/node_modules/')) continue;
      const ext = base.includes('.') ? base.split('.').pop().toLowerCase() : '';
      if (BINARY_EXT.has(ext)) continue;
      let size;
      try {
        size = statSync(join(dir, f)).size;
      } catch {
        continue; // deleted / dangling symlink
      }
      if (size > 1024 * 1024) continue; // skip very large files
      let buf;
      try {
        buf = readFileSync(join(dir, f));
      } catch {
        continue;
      }
      if (buf.includes(0)) continue; // binary content
      const text = buf.toString('utf8');
      const pieces = text.split('\n');
      total += pieces.length - (pieces[pieces.length - 1] === '' ? 1 : 0);
    }
    return total;
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------------------
// Top languages (share of bytes across all owned repos)
// ---------------------------------------------------------------------------
function topLanguages(merged) {
  const entries = Object.entries(merged).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return 'None';
  const total = entries.reduce((s, [, bytes]) => s + bytes, 0);
  return entries
    .slice(0, 3)
    .map(([name, bytes]) => `${name} ${Math.round((bytes / total) * 100)}%`)
    .join(', ');
}

// ---------------------------------------------------------------------------
// README rewrite: replace the stats-section rows in place, preserving the art.
// ---------------------------------------------------------------------------
function markerDotColumn(line) {
  // The trailing ". " bullet that separates art from right-side text.
  const trimmed = line.trimEnd();
  let m = trimmed.match(/ +\. <font/);
  if (m) return m.index + m[0].lastIndexOf('.');
  m = trimmed.match(/ +\.( |$)/);
  if (m) return m.index + m[0].lastIndexOf('.');
  return -1;
}

// Art rows may be wrapped in <sub>...</sub> (the ascii-art tool's --small
// rendering, which displays ~30% smaller on GitHub). Keep the wrapper intact
// when rewriting a row's trailing text.
function unwrapSub(line) {
  const m = line.match(/^<sub>(.*)<\/sub>$/);
  return m ? { wrapped: true, inner: m[1] } : { wrapped: false, inner: line };
}

function updateReadme(statLines) {
  const raw = readFileSync(README_PATH, 'utf8');
  const crlf = raw.includes('\r\n');
  const endsWithNewline = raw.endsWith('\n');
  const lines = raw.split(/\r?\n/);
  if (endsWithNewline) lines.pop(); // drop the trailing empty element

  const headerIdx = lines.findIndex((l) => l.includes('- GitHub Stats -'));
  if (headerIdx === -1) throw new Error(`Could not find the "- GitHub Stats -" section in ${README_PATH}`);

  // Reference bullet column from the first existing stat row.
  const refDot = markerDotColumn(unwrapSub(lines[headerIdx + 1]).inner);
  if (refDot === -1) throw new Error('Could not locate the stats bullet column in README.md');

  // Sanity-check the rows we are about to rewrite: they must be art rows,
  // not markup or EOF.
  for (let i = 0; i < statLines.length; i++) {
    const line = lines[headerIdx + 1 + i];
    if (line === undefined || line.includes('</pre>') || !line.includes('@')) {
      throw new Error(
        `README structure changed — expected an art row at line ${headerIdx + 2 + i}; refusing to rewrite`
      );
    }
  }

  // Rewrite the stats rows (preserving any <sub> wrapper).
  for (let i = 0; i < statLines.length; i++) {
    const idx = headerIdx + 1 + i;
    const { wrapped, inner } = unwrapSub(lines[idx]);
    const dot = markerDotColumn(inner);
    const prefix = (dot === -1 ? inner.trimEnd() : inner.slice(0, dot)).trimEnd();
    const pad = ' '.repeat(Math.max(refDot - prefix.length, 1));
    lines[idx] = (wrapped ? '<sub>' : '') + prefix + pad + statLines[i] + (wrapped ? '</sub>' : '');
  }

  // Clear any stale stat rows left over from a previous run that rendered
  // more rows than this one (e.g. a token-less local run after CI).
  for (let i = statLines.length; i < statLines.length + 10; i++) {
    const idx = headerIdx + 1 + i;
    const line = lines[idx];
    if (line === undefined || line.includes('</pre>')) break;
    if (!line.includes('@') || (!line.includes('. <font') && !line.includes('. <img'))) continue;
    const { wrapped, inner } = unwrapSub(line);
    const dot = markerDotColumn(inner);
    const prefix = (dot === -1 ? inner.trimEnd() : inner.slice(0, dot)).trimEnd();
    lines[idx] = (wrapped ? '<sub>' : '') + prefix + ' '.repeat(Math.max(refDot - prefix.length, 1)) + '. ' + (wrapped ? '</sub>' : '');
  }

  const eol = crlf ? '\r\n' : '\n';
  const next = lines.join(eol) + (endsWithNewline ? eol : '');
  if (next === raw) return false;
  writeFileSync(README_PATH, next, 'utf8');
  return true;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  let stats;

  if (MOCK) {
    console.log('[update-stats] MOCK mode — using sample data, no network calls.');
    stats = {
      repos: 19,
      followers: 29,
      stars: 342,
      commits: 2116,
      contributed: 8,
      lines: 446276,
      languages: { TypeScript: 60, Rust: 25, 'C++': 15 },
      contributions12mo: 1234,
    };
  } else {
    if (!TOKEN) {
      console.warn(
        '[update-stats] No GITHUB_TOKEN set — using unauthenticated REST (rate-limited); ' +
          '"Contributed" and "Contributions (12mo)" rows will be omitted.'
      );
    }

    const [user, repos] = await Promise.all([fetchUser(), fetchNonForkRepos()]);
    const repoNames = repos.map((r) => r.name);

    const [commitCounts, langResults, contributed, contributions12mo] = await Promise.all([
      Promise.all(repoNames.map(fetchCommitCount)),
      Promise.all(repoNames.map(fetchLanguages)),
      fetchContributedRepoCount(),
      fetchContributions12mo(),
    ]);

    const merged = {};
    for (const langs of langResults) {
      for (const [name, bytes] of Object.entries(langs)) {
        merged[name] = (merged[name] ?? 0) + bytes;
      }
    }

    let linesOfCode = null;
    if (!NO_LINES) {
      linesOfCode = 0;
      for (const repo of repoNames) {
        try {
          linesOfCode += countLinesInWorkingTree(repo);
        } catch (err) {
          throw new Error(`Failed to count lines for ${OWNER}/${repo}: ${err.message}`);
        }
      }
    }

    stats = {
      repos: repos.length, // non-fork repos (user.repos includes the 4 forks)
      followers: user.followers,
      stars: repos.reduce((sum, r) => sum + (r.stargazers_count ?? 0), 0),
      commits: commitCounts.reduce((a, b) => a + b, 0),
      contributed,
      lines: linesOfCode,
      languages: merged,
      contributions12mo,
    };
  }

  const out = [];
  const push = (label, value, color) => out.push(statLine(label, value, color));

  push('Repos', fmt(stats.repos));
  if (stats.contributed != null) push('Contributed', fmt(stats.contributed));
  push('Stars', fmt(stats.stars), CYAN);
  push('Commits', fmt(stats.commits));
  push('Followers', fmt(stats.followers), ORANGE);
  if (stats.lines != null) push('Lines of Code', fmt(stats.lines));
  push('Top Languages', topLanguages(stats.languages));
  if (stats.contributions12mo != null) push('Contributions (12mo)', fmt(stats.contributions12mo));

  const changed = updateReadme(out);
  if (changed) {
    console.log(`[update-stats] Updated ${README_PATH} with ${out.length} stat rows.`);
  } else {
    console.log('[update-stats] Stats unchanged — README left as-is.');
  }
}

// Run only when executed directly (keeps the helpers importable for tests).
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error(`[update-stats] ${err.message}`);
    console.error('[update-stats] Aborted without modifying the README — last-known stats are kept.');
    process.exit(1);
  });
}

export { api, fetchUser, fetchOwnedRepos, fetchNonForkRepos, fetchCommitCount, fetchLanguages, countLinesInWorkingTree, topLanguages, statLine, fmt, updateReadme };
