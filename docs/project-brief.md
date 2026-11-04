We want to describe the quality of deposited research code and how it varies
across disciplines and time. Quality means readability, maintainability,
implementation reliability, reproducibility and portability. Understandable code
is easier to check; fewer coordinated edits may reduce inconsistent corrections;
recorded environments and controlled randomness help others repeat computations.
These mechanisms motivate the study. Testing whether the attributes predict
correct research results is outside its current scope.

We measure selected indicators without executing deposited code:

| Attribute | Current measures | What they do not establish |
| --- | --- | --- |
| Readability | Parsed nesting; selected lintr formatting checks | Whether readers understand the analysis |
| Maintainability | Token duplication and function length | Whether repetition is harmful or changes remain consistent |
| Implementation reliability | Selected suspicious expressions; recognized assertions | Most logic/statistical errors or adequate checking |
| Reproducibility | Softverse environment records; flowR randomness/seed queries | Complete environments, effective seed control or successful reruns |
| Portability | flowR filesystem-path analysis using argument roles | Available inputs or the full work needed to run elsewhere |

These are partial, sometimes weak indicators of the larger attributes. We weight
deposits equally within each language, keep failures separate from zeros, and
avoid an aggregate score. The [measure dictionary](../src/not_to_code/metrics.json)
and [protocol](quality-profile.md) specify definitions and limits.

The results have two distinct scopes:

- The existing assessment covers **13,982 deposits across R, Python and Stata**.
  Among **6,118 completely measured R deposits**, median exact repeated-code
  coverage is **27.3%**, with the middle half between **10.7% and 48.5%**. Blocks
  must contain at least 50 tokens; coverage counts originals and copies.
- The unified **60-deposit R comparison run** has median repeated-code coverage of **35.7%
  among 50 complete deposits**. Absolute-path findings occur in **13/48**
  completely processed deposits; duplicate-argument candidates in **2/50**
  completely linted deposits. Supported extraction records locked R dependencies
  in **1/60**. Among **11** completely processed deposits with recognized
  stochastic calls, **4** lack a recognized seed-setting call with a supplied
  non-NULL expression. Another **39** complete deposits have no recognized
  stochastic calls and are outside that denominator.

These detection results do not establish failed reproduction. The pilot does not
replace the full-corpus results or establish a time trend. Discipline labels are
mostly "social science," and many subgroups are small. See the earlier
[validation record](validation.md) and the [release assessment archive](https://github.com/recite/not_to_code/releases).

The earlier repository contains five things worth preserving:

1. **The full assessment and coverage accounting.** Keep deposit identities,
   source ledgers, notebook/chunk boundaries and failure states. The comparison
   cohort excludes container-only R deposits; the revised pipeline can include
   them in future selections.
2. **Duplication sensitivity.** Keep within-file/between-file distinctions,
   identifier/literal-normalized candidates and 30/50/100-token thresholds.
   In the full R assessment, those thresholds yield median exact coverage of
   **40.3%, 27.3% and 12.9%**. The choice materially changes the answer. Preserve
   the detector and its brute-force reference tests until a replacement
   demonstrates parity; normalized matches are not semantic equivalence.
3. **Eligibility sensitivity and project context.** Keep results excluding
   uncertain vendor/generated/backup code, plus code size, file/routine counts
   and file concentration. These help interpret discipline/time differences.
   The unified report now includes this information.
4. **Provenance and regression tests.** Preserve source hashes, frozen inputs,
   tool versions, changed-input refusal, source locations and tests covering
   parsing failures, containers and clone overlaps.
5. **The original package-maintenance question.** The 2023 package-age script
   used the latest package update relative to inspection time. Preserve the
   question, but measure maintenance using information available at the deposit
   date. Distinguish maintenance from the age of the version actually used,
   which is often unknown. Older packages are not necessarily worse. Keep the
   original scripts and tables in Git history as exploratory work; their pooled
   lint totals are not a comparable quality benchmark.

The revised code combines the existing assessment with native R analysis under
one dictionary and aggregation path. It preserves duplication thresholds, paired
eligibility sensitivity, project context and provenance. All 3,480 retained
baseline measurement rows reproduce the earlier pilot values and denominators.
Weak lexical path guesses and trivial whitespace counts are excluded from the
profile; code outside functions and working-directory changes are context.

The next substantive priorities are better discipline metadata, broader environment
extraction and reviewed positive/negative examples of each measure. The current
instrument supports descriptive comparisons; it does not validate the larger
quality attributes. See [the current protocol](quality-profile.md).
