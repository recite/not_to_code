# Changelog

## 0.1.0

First exploratory release of a static engineering-quality profile for deposited
research code in R, Python and Stata, using Softverse inventory outputs.

- Defines the deposit-level estimand, source eligibility, denominators and
  measurement limits before reporting results.
- Measures exact token duplication at 30, 50 and 100 tokens, with separate
  identifier/literal-normalized coverage and within/between-file assessments.
- Reports code structure, organization, formatting, literal paths and recorded
  environment evidence, with inspectable source findings.
- Separates complete, partial, missing, inapplicable and unsupported measurements;
  includes a sensitivity that excludes uncertain source roles.
- Records input, source, instrument and output hashes; supports resumable scans
  and generates reports from verified tables.
- Includes the completed assessment of 13,982 deposits, documentation of a
  180-file diagnostic excerpt review, and automated tests.

Release assets include an installable wheel, source distribution, the assessment
archive and SHA-256 checksums. Extract the assessment archive and open
`assessment/report.html` to inspect the results. The archive contains measurement
tables and evidence excerpts; it does not contain the recovered source corpus or
per-deposit scan caches.

This release is exploratory. The properties have not been validated as measures
of human maintenance effort. They do not form an overall quality score or support
claims about the correctness of research estimates. Stata analysis is lexical;
units with embedded languages are withheld. Read coverage and source-role
sensitivities alongside the reported values.
