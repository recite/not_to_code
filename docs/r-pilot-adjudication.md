# AI diagnostic adjudication

This compares [review A](r-pilot-review-a.md) and [review B](r-pilot-review-b.md).
Both reviewed the same eight development units and four holdout units without
access to analyzer findings or aggregate attributes. These are selected diagnostic
examples, not independent human labels or a population accuracy sample.

The two development defect candidates are supported by both reviewers:

- `b89e4dfffeca56c79ce33c026a8f1c3d`, line 218: `m100` is used after a workspace
  reset, with no definition in the inspected script and a nearby `d100` model.
  Retain as a high-confidence execution-defect candidate; intended model and
  original runtime still require verification.
- `e740de4897575cc79924d9dbb5c02fa9`, lines 120–129: numeric coordinates enter a
  helper whose hash-vector lookup uses numeric positions, not character keys.
  Retain as a high-confidence candidate for incorrect anonymization or failure,
  conditional on the expected numeric input types. Actual data were not inspected.

The reviewers differ on how strongly to classify contextual issues. Preserve
these as uncertain; disagreement is not resolved by majority voting. On holdout
unit `8ed9919200e05ad9982c4d8af6cab539`, reviewer A identifies a basename-only
invocation path-extraction failure while B finds no high-confidence defect.
This is an invocation-dependent candidate, not a confirmed defect in the actual
workflow. Date aggregation, optimization-input ordering, score recoding and
sample-deletion choices also require external context.

The three-line literate chunk begins at original line 379. An object used there
cannot be classified as undefined merely because its definition is outside the
chunk. This illustrates why per-unit detection scope must accompany results.

No rule was added to fit these holdout observations. The two supported development
candidates are not covered by the selected lintr correctness rules. The first
pilot therefore does not exhaust plausible defect mechanisms. Before estimating
any relationship between structure and correctness, qualified human reviewers
must adjudicate independent outcomes with the relevant data and project context.

Automated results and reviewer judgments remain separate. Absence of a warning
or of an identified defect is not proof of correctness. No reported paper result
has been shown wrong by this diagnostic exercise.
