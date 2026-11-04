import assert from 'node:assert/strict';
import { test } from 'node:test';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { analyze } from './analyze.mjs';

const positives = [
  'write.csv(x, "/tmp/a")',
  'write.csv(file="/tmp/a", x=x)',
  'write.csv(file="/tmp/a", x)',
  'write.csv(x, fi="/tmp/a")',
  'utils::write.csv(x, "/tmp/a")',
  'readr::write_csv(x, "/tmp/a")',
  'arrow::write_parquet(x, sink="/tmp/a")',
  'save(x, file="/tmp/a")',
  'saveRDS(x, "/tmp/a")',
  'p <- "/tmp/a"; write.csv(x,p)',
  'read.csv(file.path("/tmp", "a"))',
  'read.csv("\\u{002f}tmp/a")',
  'read.csv(r"(/tmp/a)")',
  'x |> write.csv("/tmp/a")',
  'write.csv(\n x,\n file="/tmp/a"\n)',
];
for (const source of positives) {
  test(source, async () => {
    const result = await analyze(source);
    assert.equal(result.status, 'processed');
    const paths = result.results.linter.results['absolute-file-paths'];
    assert.deepEqual(paths.results.map(x => x.filePath), ['/tmp/a']);
    assert.equal(paths['.meta'].totalUnknown, 0);
  });
}
for (const source of [
  'write.csv("/tmp/data", "relative.csv")',
  'write.csv(x="/tmp/data", file="relative.csv")',
  'read.csv <- function(x) x; read.csv("/tmp/a")',
  'read.csv("https://example.org/a")',
]) {
  test(`no absolute filesystem finding: ${source}`, async () => {
    const result = await analyze(source);
    assert.equal(result.status, 'processed');
    assert.deepEqual(result.results.linter.results['absolute-file-paths'].results, []);
  });
}
test('unresolved inputs remain explicit', async () => {
  const result = await analyze('read.csv(unknown)');
  assert.equal(result.results.linter.results['absolute-file-paths']['.meta'].totalUnknown, 1);
});
test('missing required destination is not a resolved path', async () => {
  const result = await analyze('save("/tmp/a")');
  assert.equal(result.results.linter.results['absolute-file-paths']['.meta'].totalUnknown, 1);
});
test('malformed source cannot become a clean result', async () => {
  const result = await analyze('write.csv(x,');
  assert.equal(result.status, 'parse_failed');
  assert.equal(result.results, null);
});
test('sourced files are not followed', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'ntc-flowr-'));
  try {
    const path = join(dir, 'external.R');
    writeFileSync(path, 'write.csv(x, "/tmp/should-not-appear")');
    const result = await analyze(`source(${JSON.stringify(path)})`);
    assert.equal(result.status, 'processed');
    assert.ok(!JSON.stringify(result.results).includes('should-not-appear'));
  } finally { rmSync(dir, { recursive: true }); }
});
test('CLI returns JSON and nonzero exit for parse and read failures', () => {
  const cli = fileURLToPath(new URL('analyze.mjs', import.meta.url));
  const child = spawnSync(process.execPath, [cli, '--worker'], { input: 'read.csv(', encoding: 'utf8' });
  assert.equal(child.status, 1);
  assert.equal(JSON.parse(child.stdout).status, 'parse_failed');
  const missing = spawnSync(process.execPath, [cli, '/nonexistent/ntc-missing.R'], { encoding: 'utf8' });
  assert.equal(missing.status, 1);
  assert.equal(JSON.parse(missing.stdout).status, 'read_failed');
});
test('CLI reads a source file and records provenance and call coordinates', () => {
  const dir = mkdtempSync(join(tmpdir(), 'ntc-flowr-cli-'));
  try {
    const path = join(dir, 'input.R');
    writeFileSync(path, '# comment\nwrite.csv(x, file="/tmp/a")\n');
    const child = spawnSync(process.execPath, [fileURLToPath(new URL('analyze.mjs', import.meta.url)), path], { encoding: 'utf8' });
    assert.equal(child.status, 0, child.stderr);
    const result = JSON.parse(child.stdout);
    assert.equal(result.status, 'processed');
    assert.equal(result.version, '2.16.8');
    assert.match(result.source_sha256, /^[a-f0-9]{64}$/);
    assert.match(result.lock_sha256, /^[a-f0-9]{64}$/);
    const finding = result.results.linter.results['absolute-file-paths'].results[0];
    assert.equal(finding.filePath, '/tmp/a');
    assert.equal(finding.loc[0], 2);
  } finally { rmSync(dir, { recursive: true }); }
});

test('combined analysis keeps assertions, seed expressions and stochastic calls separate', async () => {
  const result = await analyze('stopifnot(x > 0)\nset.seed(1)\nrnorm(2)');
  assert.deepEqual(result.feature_status, { paths: 'processed', calls: 'processed' });
  assert.equal(result.calls.filter(c => c.kind === 'assertion').length, 1);
  assert.equal(result.calls.filter(c => c.kind === 'seed')[0].seed_value, 'literal_number');
  assert.equal(result.calls.filter(c => c.kind === 'stochastic').length, 1);
});
