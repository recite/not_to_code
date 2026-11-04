# v0.2.0 release validation

The release candidate consolidates the measurement profile and native R tools.
It remains exploratory: detection accuracy, scientific correctness and successful
reproduction are not measured outcomes.

The implementation reviewed was `2cc6a501dfe88a633276e654d07d2214e49eb3d8`,
against `f59c0d24bf77f2e8666d98a30f3ed1a02cfa88ab`. The only change after the first
reviewed candidate was the Black security patch to 26.10.1. Subsequent additions
to this validation record do not change the measurement implementation.

## Verification

- Local source and independently installed wheel: Black, isort and flake8 passed;
  88 Python tests passed with no failures or skips on Python 3.13.2.
- Native tools: 31 Node tests passed with no failures or skips, plus R adapter
  checks. Runtime: Node 23.10.0, R 4.6.0, flowR 2.16.8 and lintr 3.4.0.
- A separate GPT-6 Astra reviewer cloned the candidate, verified its identity,
  reran the Python and native checks, and exercised real Python-to-native
  integration. It found no concrete correctness defects. Dependencies were
  shared with the local candidate; CI separately checked clean installation.
- CI passed Python 3.11 (88 tests), Python 3.14 (89 tests) and native R analysis.
  Python 3.14 adds a template-string case. The R job restores the locked library
  and runs the adapters without executing deposited configurations.
- Source and wheel builds passed strict Twine metadata checks. The wheel includes
  the dictionary and specification; the source archive includes native tool code
  and locks, excluding installed dependencies. README and changelog rendering,
  relative documentation links and report controls were checked.
- Targeted regression tests fail when the changed-source recovery protection or
  feature-specific analyzer coverage is removed, and pass with the repairs.
- Local Docker checks could not run because the Docker daemon was unavailable.
  Linux CI provides supported-version verification; no local Docker pass is claimed.

## Comparison assessment

A fresh v0.2.0 run uses the same selected 60 R deposits as the earlier pilot. Its
assessment fingerprint is
`c71865f5e63369ef73ae2be940504ac01ab2569f4f475e26029514cad6699b98`.
Every measurement row equals the previous unified run, including values, statuses
and denominators. This is a fixed comparison cohort, not a population sample.

Median exact repeated-token coverage is 35.7% among 50 complete deposits. Absolute
path findings occur in 13/48 complete deposits and duplicate-argument candidates
in 2/50. Among 11 completely processed deposits with recognized stochastic calls,
4 lack a recognized supplied non-NULL seed expression. Another 39 completely
processed deposits have no recognized stochastic call and are inapplicable to
that measure.

The release assessment archive contains the report, figures, measurements,
evidence, frozen definitions and manifests. It excludes restored source files
and execution caches. `release-metadata.json` identifies the publication commit,
CI run and artifact hashes. The earlier 13,982-deposit archive remains part of
v0.1.0 and is not relabeled as a v0.2.0 full-frame run.
