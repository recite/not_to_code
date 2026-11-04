# Historical R attribute pilot

This records the earlier development pilot. Its commands have been retired in
version 2; use [the unified assessment](quality-profile.md) for new work. Existing
outputs and diagnostic reviews remain historical evidence.

The pilot supplies measurements for a descriptive study of readability,
maintainability, implementation reliability, reproducibility and portability.
These attributes have explicit mechanisms linking them to inspection, consistent
changes and repeated computation. Their distributions and variation across
collections and deposit years are the current target; predicting correctness is
outside scope. See [the quality-profile protocol](quality-profile.md).

Run from a source checkout after restoring the R environment and installing the
locked Node dependencies:

```sh
Rscript --vanilla -e 'renv::restore(project="tools/r-analysis", prompt=FALSE)'
npm ci --prefix tools/r-analysis --ignore-scripts
not-to-code r-pilot --softverse-root ../softverse --tools-root tools/r-analysis --output build/r-pilot --deposits 60 --workers 4
```

The R adapter checks R and dependency versions against `renv.lock`. Select the
restored R library using `R_LIBS` if it is not the active library. No deposited
configuration is loaded. The default selection seed is `r-profile-v1`. Selection
is deterministic among in-frame deposits with eligible inventoried R scripts;
container-only deposits are not yet in this pilot selection frame. All eligible
R units in selected deposits are processed, including extracted cells/chunks.
This narrower frame must be retained in any pilot interpretation.

Missing originals can be reconstructed from the local Softverse release contents
only if the reconstructed bytes exactly match the inventoried SHA-256. The
manifest lists restored hashes. Files that cannot be recovered remain failures.
No missing deposit is replaced by an easier case.

Selected deposits sharing an exact R/container source hash stay in the same
phase. Components are assigned to development until at least half the requested
sample is assigned, then to holdout. Actual phase sizes can differ from 30/30.
The holdout is diagnostic, not an independent population accuracy evaluation.

The separate outputs include the selection, inventory ledger, native analyzer
records, execution statuses, mapped findings, existing baseline measurements,
semantic attributes, rule summaries, HTML report and full-source review packets.
The dictionary explains each family. A completed run means processing attempts
finished; it does not imply successful measurements for every unit.

## Attributes

- Implementation candidates: missing-value comparisons and duplicate arguments.
- Mixed robustness/efficiency advice: sequence construction, length tests and
  vector logic. Retain individual messages; these are not uniformly defects.
- Readability conventions: indentation and 100-character line limit. The naming
  rule is omitted because lintr tags it as executing code. Inline suppression
  comments are honored and are a detection limitation.
- Duplication and structure: retain the existing measured properties and
  primary/exclude-uncertain sensitivity; no inference of inconsistent repairs.
- Reproduction dependencies: retain flowR raw dependency records, call locations,
  absolute-path findings and unknown counts. These are not literal-token counts.
- Explicit checks: flowR call-context matches for base `stopifnot`; their presence
  does not establish sufficient assertions or executed checks.

The baseline environment indicators retain their original Softverse inventory
scope. Parsing errors, tool errors, timeouts and unresolved values remain
separate from absence of findings. Source files are not executed, and source/load
contents are not followed. Cross-file and cross-cell dependencies are unmeasured.
Native evidence is retained even when an upstream linter returns an error object
inside an otherwise successful query response.

## Review and interpretation

Two independent AI reviews use full-source packets without aggregate metric
values or analyzer findings. Reviews must retain unit IDs, source locations,
mechanisms, uncertainties and missing context. They are diagnostic judgments,
not human labels. Development reviews may inform rule selection; holdout findings
must not be used for tuning and then presented as independent validation.

The first review batch is eight fixed development units. It is not a review of
all 60 deposits or a precision/recall estimate. Subsequent human adjudication
should separate definite implementation defects, plausible risks, conventions,
and intentional behavior. Reproduction outcomes require a separate isolated
execution protocol, distinguishing execution success, matching outputs and
repair effort. Testing the structural hypothesis requires independent outcomes
and adjustment for size/task complexity, not agreement among code metrics.

## Verification

```sh
make check PYTHON=.venv/bin/python
npm --prefix tools/r-analysis run check
npm --prefix tools/r-analysis test
Rscript --vanilla tools/r-analysis/test-lint.R tools/r-analysis
make ci-docker
```

The CLI is available in the installed Python package, but R/Node tooling is an
explicit external checkout supplied by `--tools-root`. Runtime limits are 35
seconds per external analyzer invocation; flowR uses a 512 MiB V8 heap limit.
This is not a total RSS memory bound. Real corpus completion and diagnostic
review outcomes must be reported separately from automated test results.
