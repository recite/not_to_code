# not_to_code

Static evidence about the engineering quality of research code: properties
relevant to understanding, changing and relocating a project. Using the
[Softverse](https://github.com/recite/softverse) inventory, this tool measures
duplication, code structure, organization, formatting conventions, literal paths
and recorded environment evidence in **R, Python and Stata**.

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
uv run not-to-code assess --softverse-root ../softverse --output build/assessment --workers 4
uv run not-to-code report --input build/assessment --readme README.md
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
Extract the archive and open `assessment/report.html`, or regenerate it with
`not-to-code report --input assessment`.

Rerunning the same command resumes from deposit caches after checking source
hashes. Changed code, specifications, inputs or runtime versions require a fresh
output directory. Failed runs retain caches and do not produce a completed manifest.
The supplied `uv.lock` pins the dependency environment; each run records actual
versions and hashes independently.

## Measurements and outputs

| Dimension | Observations |
|---|---|
| Duplication / DRY | Exact 50-token match coverage; 30/100-token sensitivity; within-file, between-file and union coverage; additional identifier/literal-normalized coverage |
| Structure | Recognized control constructs, nesting, routine counts and code-line lengths |
| Organization | File counts and sizes, largest-file share, code outside routines |
| Formatting | Code lines over 100 characters, trailing whitespace, mixed indentation |
| Portability | Recognized literal absolute filesystem paths, other path-looking literals, working-directory changes |
| Environment | Recorded declarations, constraints, locks, bundled dependencies and interpreter-version evidence |

`metrics.json` in the package is the executable dictionary used by the report.
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
| `coverage.json`, `unit_coverage.json` | Recovery, exclusions and instrument coverage |
| `report.html`, `results.md` | Standalone report and generated README results |

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

Run `1d32aa37dbab`; 13,982 deposits. Equal-deposit medians among complete measurements.

| Language | Property | Median | Complete / eligible deposits |
|---|---|---:|---:|
| python | clone_exact_union_50 | 0.1428 | 789 / 954 |
| python | largest_file_share | 0.5123 | 789 / 954 |
| python | max_nesting | 3 | 695 / 954 |
| r | clone_exact_union_50 | 0.273 | 6124 / 6500 |
| r | largest_file_share | 0.6318 | 6124 / 6500 |
| r | max_nesting | 1 | 6145 / 6500 |
| stata | clone_exact_union_50 | 0.2169 | 7083 / 8956 |
| stata | largest_file_share | 0.8458 | 7083 / 8956 |
| stata | max_nesting | 1 | 6827 / 8956 |

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
CI checks Python 3.11 and 3.14 using the pinned Softverse source checkout.

The original R analysis and import-age tables are preserved in
[`historical/`](historical/README.md); they are not inputs to the new measurements.
