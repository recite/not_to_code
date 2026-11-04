import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeRandomness } from './randomness.mjs';

test('finds qualified, bare and aliased random calls with source locations', async () => {
  const r = await analyzeRandomness('f <- rnorm\nx <- f(2)\nstats::runif(1)\nsample(1:4)');
  assert.equal(r.status, 'processed');
  assert.equal(r.calls.filter(c => c.kind === 'stochastic').length, 3);
  assert.ok(r.calls.every(c => c.location[0] > 0));
});

test('strings, comments and shadowed functions are not random calls', async () => {
  const r = await analyzeRandomness('# rnorm(1)\nx <- "set.seed(1)"\nrnorm <- function(n) n\nrnorm(1)');
  assert.deepEqual(r.calls, []);
});

test('seed arguments use R argument matching and distinguish NULL and expressions', async () => {
  const r = await analyzeRandomness('set.seed(kind="Mersenne-Twister", seed=123)\nset.seed(NULL)\nset.seed(x)\nparallel::clusterSetRNGStream(iseed=7, cl=cl)\nwithr::with_seed(3, rnorm(1))');
  assert.equal(r.status, 'processed');
  assert.deepEqual(r.calls.filter(c => c.kind === 'seed').map(c => c.seed_value).sort(),
    ['literal_number', 'literal_number', 'literal_number', 'null', 'unresolved_expression']);
});

test('RNG configuration alone is not a seed and absent stream seed is explicit', async () => {
  const r = await analyzeRandomness('RNGkind("Mersenne-Twister")\nparallel::clusterSetRNGStream(cl)');
  assert.equal(r.calls.filter(c => c.kind === 'seed')[0].seed_value, 'missing');
  assert.equal(r.calls.filter(c => c.kind === 'rng_configuration').length, 1);
});

test('invalid syntax is missing measurement; deposited code is not executed', async () => {
  assert.equal((await analyzeRandomness('x <- (')).status, 'parse_failed');
  const r = await analyzeRandomness('rnorm(1)\nsource("/missing.R")\nstop("do not execute")');
  assert.equal(r.status, 'processed');
  assert.equal(r.calls.length, 1);
});
