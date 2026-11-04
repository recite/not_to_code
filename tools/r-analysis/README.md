# Native R analysis with flowR and lintr

The unified assessment uses locked flowR 2.16.8 and lintr 3.4.0. flowR resolves
filesystem argument roles, recognized assertions and stochastic/seed calls;
lintr measures indentation, line length, duplicate arguments and NA comparisons.
Each feature has separate coverage. Neither tool executes deposited code.

Requires Node 22 or newer and R 4.6.0 (the version in `renv.lock`). Install the locked dependency tree and run:

```sh
npm ci --prefix tools/r-analysis --ignore-scripts
npm --prefix tools/r-analysis run check
npm --prefix tools/r-analysis test
Rscript --vanilla -e 'install.packages("renv", repos="https://cloud.r-project.org")'
Rscript --vanilla -e 'renv::restore(lockfile="tools/r-analysis/renv.lock", library="tools/r-analysis/library", prompt=FALSE)'
Rscript --vanilla tools/r-analysis/test-lint.R tools/r-analysis
node tools/r-analysis/analyze.mjs path/to/script.R > result.json
```

The CLI reads one UTF-8 R source file and emits JSON. Use extracted R source units
for notebooks/literate documents; this command does not extract containers or
translate coordinates back into their parent documents. The caller must retain
that mapping. The unified Python pipeline performs extraction and retains it in
`native.parquet`. Use `not-to-code assess --r-tools tools/r-analysis` to integrate
these measurements; see [the protocol](../../docs/quality-profile.md).

Each successful result records the source hash, lockfile hash, flowR and Node
versions, configuration, raw dependency query, call evidence and absolute-path results.
`feature_status` distinguishes path-query and call-query completion; a partial
result can retain successful call evidence when path analysis fails.
The pinned lockfile covers the grammar and transitive packages. The engine is
explicitly tree-sitter. Default project plugins are disabled; `source` and `load`
contents are not followed. Deposited R code is not executed. Cross-file bindings
are consequently outside this configuration's scope.

`processed` means the query finished, not complete detection. Keep the linter's
`totalUnknown`, certainty and locations alongside findings. Its `totalConsidered`
is an upstream rule counter, not a validated denominator of all I/O operations.
Dependency `value` fields can contain unresolved-expression text; do not treat
all of them as resolved paths. In particular, implicit `stdout` writes are not
filesystem destinations. Returned call coordinates are upstream coordinates,
not the existing scanner's literal-token coordinates.

The wrapper explicitly checks tree-sitter parse errors: the tested upstream
query returned empty results for `write.csv(x,` even with lax parsing disabled.
A parse failure has `results: null` and exits nonzero. Read failures, analysis
failures and CLI timeouts also exit nonzero. Each CLI analysis runs in a child
process with a 30-second timeout, 512 MiB V8 heap limit and 16 MiB output limit.
The heap limit is not a bound on total process memory. Direct module calls used
by the synthetic tests do not have the CLI's process limits.

The tests cover positional/named/reordered arguments, namespace-qualified R,
readr and Arrow calls, `save`/`saveRDS`, variables, `file.path`, Unicode/raw strings,
pipes, false positives in data arguments, local function redefinition, URLs,
unknown input, malformed syntax, source isolation and CLI failures. Passing
these diagnostic fixtures is not a corpus accuracy estimate.

Official API references:
[flowR analyzer](https://github.com/flowr-analysis/flowr/wiki/Analyzer),
[dependency query](https://github.com/flowr-analysis/flowr/wiki/%5BQuery%5D-Dependencies),
[engine configuration](https://github.com/flowr-analysis/flowr/wiki/Engines).
