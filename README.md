# Not to Code: Static Analysis of Research Code

Static evidence about the engineering quality of research code: properties
relevant to understanding, changing and relocating a project. Using the
[Softverse](https://github.com/recite/softverse) inventory, this tool measures
duplication, code structure and recorded environment evidence in **R, Python
and Stata**, with native R linting and call analysis through lintr and flowR.

Use the profile to describe a collection or identify code for closer inspection.
The measurements have not been validated against human maintenance effort and do
not establish whether estimates are correct. They remain separate observations,
without an overall quality score. The estimand is the
**equal-deposit distribution within each language** in the recovered, pinned
journal-collection frame. Read [the measurement specification](measurement.md)
for definitions, denominators, exclusions and limitations.

## Install and run

Requires Python 3.11+ and a Softverse checkout with extractor version 2.4.0. The
adapter is tested against commit `38fdba9b255127b896ab68bf37871b92e729fd0c`.
The recorded runtime matters for language parsing; this assessment used Python
3.13.2, pinned in `.python-version`.

Download the wheel from [GitHub Releases](https://github.com/recite/not_to_code/releases)
and install it in a virtual environment:

```sh
python -m pip install ./not_to_code-*.whl
not-to-code --help
```

To reproduce the assessment from a source checkout, run from the repository root:

```sh
uv sync --locked --group dev
uv run not-to-code assess --softverse-root ../softverse --output build/assessment-v2 --workers 4
uv run not-to-code report --input build/assessment-v2
```

For a pilot, add `--limit-deposits 100` and use a different output directory.
Without `--workers`, assessment uses one process. Source is read, never executed.
No paid APIs or network calls are used during assessment.

Required Softverse inputs:

- `build/tally/files.parquet`, including local source paths and SHA-256 hashes;
- `build/tally/declared_dependencies.parquet` and `environment_signals.parquet`;
- `data/frame/frame.csv` and the corresponding recovered source files.

These inputs come from the [Softverse recovery and inventory workflow](https://github.com/recite/softverse).
Installing this package does not download the source corpus. The first release
also includes an assessment archive containing the completed tables and report,
so inspecting those results does not require recovering or scanning the corpus.
Extract the archive and open `assessment/report.html`. Regenerating historical
reports requires their original instrument; version 2 uses a new schema.

Rerunning the same command resumes from deposit caches after checking source
hashes. Changed code, specifications, inputs or runtime versions require a fresh
output directory. Failed runs retain caches and do not produce a completed manifest.
The supplied `uv.lock` pins the dependency environment; each run records actual
versions and hashes independently.

## Measurements and outputs

| Dimension | Observations |
|---|---|
| Duplication / DRY | Exact 50-token match coverage; 30/100-token sensitivity; within-file, between-file and union coverage; additional identifier/literal-normalized coverage |
| Readability / maintainability | Nesting and function length; native R indentation/line-length findings; Python/Stata long-line convention |
| Implementation reliability | R duplicate-argument and NA-comparison candidates; recognized assertions |
| Reproducibility | Recorded declarations, constraints, locks and interpreter versions; conditional R seed-call gap |
| Portability | R absolute filesystem paths resolved in call context by flowR |
| Context | Code size, file concentration, routine/control counts, code outside routines, working-directory changes and bundled dependencies |

`metrics.json` is the single executable dictionary; every run freezes it as
`dictionary.json` for reporting.
Rates retain numerators, denominators and coverage status. Zero, partial, missing,
unsupported and inapplicable are distinct. Primary and exclude-uncertain variants
are both produced; Softverse's deduplication flag is deliberately not an exclusion.

The output directory contains:

| File | Contents |
|---|---|
| `manifest.json` | Input, instrument, specification and output hashes; versions; completion status |
| `ledger.parquet` | Every inventoried file in the selected frame, eligibility and read status |
| `units.parquet` | Source-unit metrics and token/structure coverage, including cells and chunks |
| `findings.parquet` | Rule, source coordinates and inspectable evidence |
| `clones.parquet` | Unions of matching token spans; these are not clone-family counts |
| `metrics.parquet` | Deposit × language × sensitivity × metric values and denominators |
| `summary.parquet`, `summary.csv` | Equal-deposit quartiles and prevalence, with complete/partial populations separate |
| `coverage.json` | Recovery, exclusions and instrument coverage |
| `native.parquet` | R analyzer results, feature coverage and source-unit coordinates |
| `dictionary.json`, `metadata.json`, `environment.json` | Frozen definitions, grouping metadata and environment evidence |
| `by-*.csv`, `paired-sensitivity.csv` | Collection/discipline/time distributions and paired eligibility comparisons |
| `report-manifest.json` | Report inputs, renderer and generated-output hashes |
| `report.html`, `results.md` | Standalone report and generated README results |

## R quality profile

The unified profile organizes indicators around **readability, maintainability,
implementation reliability, reproducibility and portability**. Each measure has
an explicit rationale and interpretive limits. Its current purpose is to describe
distributions and variation across collections and deposit years; testing whether
structure predicts correctness is a separate future question.

From a source checkout or extracted source distribution, use Node 22+ and the
R version recorded in `tools/r-analysis/renv.lock` (currently 4.6.0). Restore the
locked R analyzers into their own library:

```sh
npm ci --prefix tools/r-analysis --ignore-scripts
Rscript --vanilla -e 'install.packages("renv", repos="https://cloud.r-project.org")'
Rscript --vanilla -e 'renv::restore(lockfile="tools/r-analysis/renv.lock", library="tools/r-analysis/library", prompt=FALSE)'
uv run not-to-code assess --softverse-root ../softverse --output build/profile-v2 --language r --r-tools tools/r-analysis --recover-release --limit-deposits 60 --workers 4
```

Open `build/profile-v2/report.html` for distributions, both eligibility variants,
paired sensitivity and collection/time comparisons. The single registry assigns
measures to indicators, evidence, context or sensitivity. Weak path guesses and
trivial whitespace counts are excluded from the profile. Omit `--language` for
all supported languages; omit `--r-tools` to mark native R measures as not run.
See the [profile protocol](docs/quality-profile.md) for exact coverage and limits.
Version 2 requires a fresh output directory; the historical full-frame results
below remain results of the earlier instrument.

## Interpretation

Repeated code can be justified. Nesting is a structural observation, not measured
human difficulty. Long lines are convention findings, not bugs. Paths may be
intentional. Recorded environment evidence does not establish reproducibility.

Uncertain vendor/generated/backup classifications are retained in the primary
candidate-code population. Consequently, it is not an author-written-code census.
Notebook and literate chunks have separate token boundaries. Unattributed
container failures prevent complete claims for known languages in that deposit.
Stata is a lexical approximation; units containing embedded languages are withheld.
Python 2 syntax can retain tokens while failing Python 3 structural analysis.
There is no cross-language ranking or sampling interval claiming generality beyond
this recovered frame.

See [validation](docs/validation.md) for tests, diagnostic excerpt review and its
limits, and [related work](docs/related-work.md) for the project's contribution.

## Results

`clone_exact_union_50` is the proportion of tokens covered by exact repeated
sequences of at least 50 tokens, counting both originals and copies.
`largest_file_share` is the largest file's share of measured code lines.
`max_nesting` is the greatest recognized control nesting depth in the deposit.
Duplication coverage and largest-file share are proportions; nesting is a count.
Read each language separately. Complete measurements cover different subsets of
deposits, and repetition is not necessarily a refactoring opportunity.

<!-- results:start -->

Run `db2f4b774418`; 13,982 deposits. Equal-deposit medians among complete measurements.

| Language | Property | Median | Complete / eligible deposits |
|---|---|---:|---:|
| python | clone_exact_union_50 | 0.1449 | 779 / 947 |
| python | largest_file_share | 0.5098 | 779 / 947 |
| python | max_nesting | 3.5 | 688 / 947 |
| r | clone_exact_union_50 | 0.273 | 6118 / 6500 |
| r | largest_file_share | 0.6318 | 6118 / 6500 |
| r | max_nesting | 1 | 6139 / 6500 |
| stata | clone_exact_union_50 | 0.2169 | 7081 / 8956 |
| stata | largest_file_share | 0.8452 | 7081 / 8956 |
| stata | max_nesting | 1 | 6825 / 8956 |

<!-- results:end -->

## Development

```sh
uv sync --locked --group dev
make check PYTHON=.venv/bin/python
make ci-docker
```

`make check` runs Black, isort, flake8 and pytest. `make ci-docker` builds and tests
the installed package in the standard `python:3.14-slim` image, with both repositories
mounted read-only. `SOFTVERSE_ROOT` can point tests at another supported checkout.
CI checks Python 3.11 and 3.14 using the pinned Softverse source checkout, plus
`make check-r` with locked native dependencies. The Python wheel contains the
assessment package; the source distribution also includes `tools/r-analysis`.

### Code layout

The tool is written in Python and analyses R, Python and Stata. Code that is
specific to one analysed language is in one place:

| Path | Holds |
| --- | --- |
| `src/not_to_code/languages/r.py`, `python.py`, `stata.py` | Each language's tokens, control-flow structure, and path and working-directory rules, behind the same five functions |
| `src/not_to_code/languages/r_native.py` | Calls lintr and flowR and turns their output into deposit metrics |
| `tools/r-analysis/` | The R and Node programs that `r_native.py` runs |
| the rest of `src/not_to_code/` | Shared by all languages: source extraction, duplication, the metric dictionary, aggregation, storage and reports |
