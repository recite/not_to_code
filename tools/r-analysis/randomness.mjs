import { FlowrAnalyzerBuilder } from '@eagleoutice/flowr';
import { RFunctionCall } from '@eagleoutice/flowr/r-bridge/lang-4.x/ast/model/nodes/r-function-call.js';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const version = require('@eagleoutice/flowr/package.json').version;
export const catalog = [
  ['stochastic', 'base', ['sample', 'sample.int']],
  ['stochastic', 'stats', ['rbeta', 'rbinom', 'rcauchy', 'rchisq', 'rexp', 'rf',
    'rgamma', 'rgeom', 'rhyper', 'rlnorm', 'rlogis', 'rmultinom', 'rnbinom',
    'rnorm', 'rpois', 'rsignrank', 'rt', 'runif', 'rweibull', 'rwilcox']],
  ['seed', 'base', ['set.seed']],
  ['seed', 'withr', ['with_seed', 'local_seed']],
  ['seed', 'parallel', ['clusterSetRNGStream']],
  ['rng_configuration', 'base', ['RNGkind', 'RNGversion']],
];
const formals = {
  'set.seed': ['seed', 'kind', 'normal.kind', 'sample.kind'],
  with_seed: ['seed', 'code', '.rng_kind', '.rng_normal_kind', '.rng_sample_kind'],
  local_seed: ['seed', '.local_envir', '.rng_kind', '.rng_normal_kind', '.rng_sample_kind'],
  clusterSetRNGStream: ['cl', 'iseed'],
};

function seedValue(node, name) {
  const matched = RFunctionCall.matchArgsToParams(node.arguments, formals[name]);
  const value = matched.get(name === 'clusterSetRNGStream' ? 'iseed' : 'seed')?.value;
  if (!value) return 'missing';
  if (value.type === 'RSymbol' && value.content === 'NULL') return 'null';
  if (value.type === 'RNumber' && !value.content.complexNumber
      && Number.isFinite(value.content.num)) return 'literal_number';
  return 'unresolved_expression';
}

export function randomnessQueries() {
  return catalog.flatMap(([kind, namespace, names]) => names.map(name => ({
    type: 'call-context', callName: name, callNameExact: true,
    callTargetNamespace: namespace, includeAliases: true, kind, subkind: name,
  })));
}

export async function collectCalls(analyzer, native) {
  const { idMap } = await analyzer.normalize();
  const calls = [];
  for (const [kind, group] of Object.entries(native['call-context'].kinds)) {
    for (const [name, found] of Object.entries(group.subkinds)) {
      for (const hit of found) {
        const node = idMap.get(hit.id);
        calls.push({ kind, name, node_id: hit.id, location: node?.location,
          expression: node?.info.fullLexeme,
          ...(kind === 'seed' ? { seed_value: seedValue(node, name) } : {}),
        });
      }
    }
  }
  return calls;
}

export async function analyzeRandomness(source) {
  const analyzer = await new FlowrAnalyzerBuilder(false).setEngine('tree-sitter')
    .configure('engine.tree-sitter.lax', false)
    .configure('ignoreSourceCalls', true).configure('ignoreLoadCalls', true).build();
  const record = { tool: 'flowR', version, node: process.version, catalog };
  try {
    analyzer.addRequest({ request: 'text', content: source });
    if ((await analyzer.parse()).files.some(f => f.parsed.rootNode.hasError)) {
      return { ...record, status: 'parse_failed', calls: [] };
    }
    const native = await analyzer.query(randomnessQueries());
    const calls = await collectCalls(analyzer, native);
    return { ...record, status: 'processed', calls, native };
  } finally {
    analyzer.close();
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const result = await analyzeRandomness(readFileSync(0, 'utf8'));
    console.log(JSON.stringify(result));
    if (result.status !== 'processed') process.exitCode = 1;
  } catch (error) {
    console.log(JSON.stringify({ tool: 'flowR', version, status: 'analysis_failed', error: error.message, calls: [] }));
    process.exitCode = 1;
  }
}
