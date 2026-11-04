# Selecting an existing R analyzer

Assessed 2026-10-31. Use flowR for the first R argument-role and dependency
experiment. The implementation is [tools/r-analysis](../tools/r-analysis/README.md).
It does not replace released corpus measurements. Python work is deferred.

| Tool | Relevant capability | Decision for this step |
|---|---|---|
| [flowR](https://github.com/flowr-analysis/flowr) | Dependency extraction, argument roles, value tracking, path findings with unknown counts | Preferred; installed 2.16.8 and tested locally. |
| [lintr](https://lintr.r-lib.org/reference/absolute_path_linter.html) | Mature configurable R lint rules; absolute-looking string detection | Useful broad-literal comparator, not an argument-role substitute. |
| [Jarl](https://jarl.etiennebacher.com/dev/) | R lint rules, CLI/JSON output and container support | Candidate for later lint measurement; reviewed documentation, not benchmarked. |
| [CodeDepends](https://mirror.niser.ac.in/cran/web/packages/CodeDepends/vignettes/intro.html) | Code dependencies and customizable function handlers | Its documented file/non-file distinction uses path existence on the analysis machine, which does not fit our portability target without additional work. |
| [codetools](https://stat.ethz.ch/R-manual/R-devel/library/codetools/help/findGlobals.html) | Approximate global-function/variable analysis | Useful lower-level dependency information, not a ready filesystem-argument analyzer. |
| [rstatic](https://github.com/nick-ulle/rstatic) | AST/control/dataflow infrastructure | Maintainer marks it in hibernation and directs users to flowR. |
| [scilintr](https://mirrors.ibiblio.org/CRAN/web/packages/scilintr/index.html) | Scientific-analysis pattern warnings | Different target; its stated preference for recall over precision requires independent validation before prevalence claims. |

The selection favors reuse of an existing analyzer over building a signature
registry locally. GitHub inspection used `gh`; other sources are official project
or package documentation. Only flowR and lintr were executed locally.

## Local evidence

flowR 2.16.8 passed 25 wrapper regression tests on Node 23.10.0. In particular,
`write.csv("/tmp/data", "relative.csv")` produces a dependency on `relative.csv`
and no absolute-path linter finding. `write.csv(x, file="/tmp/a")` recognizes
`/tmp/a`. Named arguments before unnamed arguments, namespace calls, native
pipes, variables, `file.path`, Unicode escapes and raw strings also passed.
A locally redefined `read.csv` did not acquire a filesystem read dependency.
These examples support a pilot, not a general binding-resolution guarantee.

Installed lintr 3.4.0 flagged the absolute-looking string in each of three cases:
`write.csv("/tmp/data", "relative.csv")`, `write.csv(x, "/tmp/out.csv")`, and
`write.csv(x, file="/tmp/out.csv")`. This is expected for its broad literal rule;
it cannot distinguish the first case's data argument for our narrower target.

Two flowR output details matter. `read.csv(unknown)` includes unresolved text
in dependency output, while the path linter reports one unknown. Also,
`save("/tmp/a")` produces a `stdout` dependency despite R requiring `file`;
the path linter correctly retains an unknown rather than an absolute finding.
Therefore the adapter preserves both query outputs without treating every
returned dependency value as a known filesystem path.

Malformed `write.csv(x,` returned empty upstream query results, even with lax
parsing disabled. The wrapper checks the parser's error flag first and returns
`parse_failed`, not a successful zero. The source-isolation test confirms that
an existing sourced file containing an extra finding is not analyzed.

## Next validation

Evaluate independently annotated complete R units from Softverse, retain their
source and container mappings, and record failures, unknowns and runtime. Check
cross-file cases separately: this initial configuration deliberately does not
follow sourced files. Define the new call-based metric and its denominator before
integrating it into deposit summaries. Do not compare raw finding counts with the
old literal metric as though both measured the same target.
