import { FlowrAnalyzerBuilder } from '@eagleoutice/flowr';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { randomnessQueries, collectCalls } from './randomness.mjs';

const require = createRequire(import.meta.url);
const version = require('@eagleoutice/flowr/package.json').version;
const config = {
  engine: 'tree-sitter',
  defaultPlugins: false,
  ignoreSourceCalls: true,
  ignoreLoadCalls: true,
};

export async function analyze(source) {
  const record = {
    tool: 'flowR', version, node: process.version, config,
    source_sha256: createHash('sha256').update(source).digest('hex'),
    lock_sha256: createHash('sha256').update(readFileSync(new URL('package-lock.json', import.meta.url))).digest('hex'),
  };
  const analyzer = await new FlowrAnalyzerBuilder(false)
    .setEngine('tree-sitter')
    .configure('engine.tree-sitter.lax', false)
    .configure('ignoreSourceCalls', true)
    .configure('ignoreLoadCalls', true)
    .build();
  try {
    // A request object prevents source text beginning with file:// being read as a file.
    analyzer.addRequest({ request: 'text', content: source });
    const parsed = await analyzer.parse();
    if (parsed.files.some(file => file.parsed.rootNode.hasError)) {
      return { ...record, status: 'parse_failed', results: null };
    }
    const results = await analyzer.query([
      { type: 'dependencies' },
      { type: 'call-context', callName: 'stopifnot', callNameExact: true, callTargetNamespace: 'base', includeAliases: true, kind: 'assertion', subkind: 'stopifnot' },
      ...randomnessQueries(),
      { type: 'linter', rules: ['absolute-file-paths'] },
    ]);
    const pathRule = results.linter?.results?.['absolute-file-paths'];
    const feature_status = {
      paths: Array.isArray(pathRule?.results) ? 'processed' : 'analysis_failed',
      calls: results['call-context']?.kinds ? 'processed' : 'analysis_failed',
    };
    const status = Object.values(feature_status).every(s => s === 'processed') ? 'processed' : 'partial';
    return { ...record, status, feature_status, results,
      calls: feature_status.calls === 'processed' ? await collectCalls(analyzer, results) : [] };
  } finally {
    analyzer.close();
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv[2] === '--worker') {
    try {
      const result = await analyze(readFileSync(0, 'utf8'));
      console.log(JSON.stringify(result));
      if (result.status !== 'processed') process.exitCode = 1;
    } catch (error) {
      console.log(JSON.stringify({ tool: 'flowR', version, status: 'analysis_failed', error: error.message, results: null }));
      process.exitCode = 1;
    }
  } else if (process.argv.length !== 3) {
    console.error('Usage: node analyze.mjs script.R');
    process.exitCode = 2;
  } else {
    try {
      const source = readFileSync(process.argv[2], 'utf8');
      const child = spawnSync(process.execPath, ['--max-old-space-size=512', fileURLToPath(import.meta.url), '--worker'], {
        input: source, encoding: 'utf8', timeout: 30000, maxBuffer: 16 * 1024 * 1024,
      });
      if (child.error || child.signal || !child.stdout.trim()) {
        console.log(JSON.stringify({ tool: 'flowR', version, status: child.error?.code === 'ETIMEDOUT' ? 'timeout' : 'analysis_failed', error: child.error?.message ?? child.signal ?? 'No result', results: null }));
        process.exitCode = 1;
      } else {
        process.stdout.write(child.stdout);
        process.exitCode = child.status;
      }
    } catch (error) {
      console.log(JSON.stringify({ tool: 'flowR', version, status: 'read_failed', error: error.message, results: null }));
      process.exitCode = 1;
    }
  }
}
