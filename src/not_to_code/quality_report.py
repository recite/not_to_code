"""A concise report of indicators, context, sensitivity and measurement coverage."""

import html

from .report import summarize

STYLE = """
:root {color-scheme:light; font-family:system-ui,-apple-system,sans-serif;
color:#182733;background:#f5f6f7}
body {margin:0} main {max-width:1050px;margin:auto;padding:38px 26px 60px}
h1 {font-size:36px;line-height:1.15;margin:10px 0 18px;letter-spacing:-.8px}
h2 {font-size:23px;margin:38px 0 12px} h3 {font-size:18px;margin:0 0 10px}
p,li {line-height:1.6} p {max-width:88ch} a {color:#075b72}
.eyebrow {font-size:13px;letter-spacing:1.2px;text-transform:uppercase;
font-weight:650;color:#3d5768}
.lede {font-size:19px;max-width:75ch}.note,small {color:#435563;font-size:14px}
.cards {display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:25px 0}
.card,section {background:white;border:1px solid #d6dfe4;border-radius:9px;padding:20px}
.card strong {display:block;font-size:31px;color:#075b72;margin-bottom:8px}
.card p {margin:0}.card small {display:block;margin-top:10px}
section {margin:18px 0} section h2 {margin-top:0} figure {margin:20px 0}
img {width:100%;height:auto} figcaption {font-size:14px;line-height:1.5;color:#435563}
.scroll {overflow-x:auto} table {border-collapse:collapse;width:100%;font-size:14px}
th,td {padding:10px 8px;text-align:left;border-bottom:1px solid #e0e5e8;
vertical-align:top}
th {font-weight:650} td.num,th.num {text-align:right;white-space:nowrap}
details {margin:12px 0} summary {cursor:pointer;color:#075b72;line-height:1.5}
.methods {border-left:3px solid #c7d7df;padding-left:15px;margin:12px 0}
.methods p {font-size:14px;margin:5px 0}.badge {font-size:12px;color:#435563}
select {max-width:100%;font:inherit;padding:7px;background:white;
border:1px solid #aab9c3;
border-radius:4px}
[hidden] {display:none!important}
footer {border-top:1px solid #c9d4dc;margin-top:30px;padding-top:15px}
@media(max-width:650px) {main {padding:22px 16px} h1 {font-size:29px}
.cards {grid-template-columns:1fr} section {padding:14px}}
@media print {body {background:white} main {padding:0}
section,.card {break-inside:avoid} details,select {display:none} a {color:inherit}}
"""


def esc(value):
    return html.escape(str(value))


def number(value):
    return "—" if value is None else f"{value:,.1f}".removesuffix(".0")


def scaled(value, spec):
    return value * 100 if value is not None and spec["unit"] == "proportion" else value


def table(headers, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f"<th>{esc(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def charts(output, rows, language, variant):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = [
        r
        for r in rows
        if r["language"] == language
        and r["variant"] == variant
        and r["status"] == "complete"
        and r["value"] is not None
    ]
    metrics = (
        "clone_exact_union_50",
        "max_nesting",
        "median_routine_lines",
        "code_lines",
    )
    labels = (
        "Repeated code: threshold sensitivity",
        "Maximum nesting",
        "Typical function length",
        "Project size (context)",
    )
    units = (
        "Tokens in repeated blocks (%)",
        "Levels",
        "Code lines per function",
        "Code lines",
    )
    with plt.rc_context(
        {
            "font.size": 10,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    ):
        fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.5), layout="constrained")
        for ax, metric, label, unit in zip(axes.flat, metrics, labels, units):
            names = (
                [f"clone_exact_union_{t}" for t in (30, 50, 100)]
                if metric.startswith("clone")
                else [metric]
            )
            for name, color in zip(names, ("#075b72", "#515e68", "#939393")):
                values = sorted(
                    r["value"] * (100 if name.startswith("clone") else 1)
                    for r in rows
                    if r["metric"] == name
                )
                if values:
                    ax.step(
                        [values[0]] + values,
                        [0] + [100 * (i + 1) / len(values) for i in range(len(values))],
                        where="post",
                        color=color,
                        label=(
                            f'{name.rsplit("_", 1)[-1]} tokens; n={len(values)}'
                            if len(names) > 1
                            else None
                        ),
                    )
                    if len(names) == 1:
                        ax.text(
                            0.97,
                            0.07,
                            f"n={len(values)}; zeros={values.count(0)}",
                            ha="right",
                            transform=ax.transAxes,
                        )
                elif len(names) == 1:
                    ax.text(
                        0.5,
                        0.5,
                        "No complete measurements",
                        ha="center",
                        transform=ax.transAxes,
                    )
            if len(names) > 1 and ax.lines:
                ax.legend(loc="lower right", frameon=False, fontsize=9)
                ax.set_xlim(0, 100)
            else:
                ax.set_xlim(left=0)
            ax.set(
                title=label,
                xlabel=unit,
                ylabel="Deposits at or below (%)",
                ylim=(0, 102),
                yticks=[0, 25, 50, 75, 100],
            )
            ax.grid(axis="y", color="#e0e5e8", linewidth=0.6)
        stem = f"distributions-{language}-{variant}"
        fig.savefig(output / f"{stem}.svg")
        fig.savefig(output / f"{stem}.pdf")
        plt.close(fig)
    return stem


def metric_table(entries, registry):
    cells = []
    for r in entries:
        spec = registry[r["metric"]]
        label = spec["label"]
        unit = "%" if spec["unit"] == "proportion" else spec["unit"]
        if spec["unit"] != "binary":
            label += f" ({unit})"
        if not r["n"]:
            value, spread = "Not measured", "—"
        elif spec["unit"] == "binary":
            value = (
                f'{round(r["prevalence"] * r["n"])}/{r["n"]} '
                f'({number(r["prevalence"] * 100)}%)'
            )
            spread = "—"
        else:
            value = number(scaled(r["median"], spec))
            spread = (
                f'{number(scaled(r["q25"], spec))}–{number(scaled(r["q75"], spec))}'
            )
        cells.append(
            (
                label,
                value,
                spread,
                f'{r["n"]}/{r["deposits"]}',
                r["partial"],
                r["missing"] + r["unsupported"] + r["not_measured"],
                r["inapplicable"],
            )
        )
    return table(
        [
            "Measure",
            "Median or prevalence",
            "Middle 50%",
            "Measured / eligible",
            "Partial",
            "Missing / not run",
            "Inapplicable",
        ],
        cells,
    )


def render(output, rows, aggregates, sensitivity, registry, manifest):
    languages = sorted({r["language"] for r in rows})
    body = (
        '<main><div class="eyebrow">Research code quality · version '
        "2</div><h1>Code that is easier to inspect, change, and "
        "rerun</h1>"
    )
    body += (
        '<p class="lede">Readability, maintainability, implementation '
        "reliability, reproducibility and portability motivate these "
        "indicators. Context and sensitivity results help interpret "
        "them. There is no aggregate score.</p>"
    )
    subset = (
        manifest["deposit_limit"] is not None
        or manifest["deposit_list_hash"] is not None
    )
    scope = (
        "This is a selected subset, not a full-frame estimate."
        if subset
        else "Results describe the recovered frame."
    )
    body += (
        f'<p>{manifest["deposits"]:,} selected deposits. {scope} '
        "Each deposit has equal weight within its language. Correctness "
        "and successful reproduction are not measured outcomes.</p>"
    )
    body += (
        '<p><label for="variant">Code eligibility: </label><select '
        'id="variant"><option value="primary">Primary: include '
        "uncertain files</option><option "
        'value="exclude_uncertain">Exclude uncertain '
        "vendor/generated/backup files</option></select></p>"
    )
    body += (
        '<p class="note">Complete means every eligible unit was '
        "processed. It does not establish detection accuracy. Partial, "
        "missing, not-run and inapplicable measurements are excluded "
        "from primary distributions. Environment rows describe "
        "supported inventory evidence, independently of source-code "
        "eligibility.</p>"
    )
    for language in languages:
        body += f"<h2>{esc(language.upper())}</h2>"
        for variant in ("primary", "exclude_uncertain"):
            hidden = " hidden" if variant != "primary" else ""
            body += f'<div data-variant="{variant}"{hidden}>'
            selected = [
                r
                for r in aggregates
                if r["language"] == language
                and r["variant"] == variant
                and r["population"]
                == (
                    "inventory_only"
                    if registry[r["metric"]]["coverage"] == "environment"
                    and r["inventory_only"]
                    else "complete"
                )
            ]
            if not selected:
                body += (
                    "<p>No eligible language measurements under this variant.</p></div>"
                )
                continue
            stem = charts(output, rows, language, variant)
            body += (
                f'<figure><img src="{stem}.svg" alt="Cumulative distributions '
                'of duplication, nesting, function length and code size.">'
                "<figcaption>Complete deposit measurements only. The vertical "
                "axis is the percentage at or below a value. Clone thresholds "
                "share the same axes and count originals and copies. No routines "
                "means function length is inapplicable. These are descriptive "
                "distributions without population confidence intervals. "
                f'<a href="{stem}.pdf">Figure PDF</a>.</figcaption></figure>'
            )
            for attribute in (
                "Readability",
                "Maintainability",
                "Implementation reliability",
                "Reproducibility",
                "Portability",
            ):
                core = [
                    r
                    for r in selected
                    if registry[r["metric"]]["attribute"] == attribute
                    and registry[r["metric"]]["role"] in {"indicator", "evidence"}
                ]
                if not core:
                    continue
                body += f"<section><h3>{attribute}</h3>" + metric_table(core, registry)
                body += "<details><summary>Rationale, definition and limits</summary>"
                for r in core:
                    spec = registry[r["metric"]]
                    body += f'<div class="methods"><b>{esc(spec["label"])}</b>'
                    for key in ("rationale", "definition", "limit"):
                        body += f"<p>{esc(spec[key])}</p>"
                    body += "</div>"
                body += "</details></section>"
            body += (
                "<details><summary>Project context: size, organization and "
                "bundled software</summary><p>These are descriptive covariates,"
                " not penalties. Top-level scripts and large files can be "
                "appropriate for their tasks.</p>"
            )
            body += (
                metric_table(
                    [r for r in selected if registry[r["metric"]]["role"] == "context"],
                    registry,
                )
                + "</details>"
            )
            body += (
                "<details><summary>All duplication sensitivities: thresholds, "
                "scope and normalized matches</summary>"
            )
            body += metric_table(
                [r for r in selected if registry[r["metric"]]["role"] == "sensitivity"],
                registry,
            )
            body += (
                '<p class="note">Within- and between-file coverage can overlap;'
                " do not add them. Normalized additional coverage is a broad "
                "structural match, not semantic equivalence or evidence of an "
                "inconsistent edit.</p></details>"
            )
            body += (
                "<details><summary>Exploratory collection, discipline and time "
                'comparisons</summary><p class="note">The table shows '
                "repeated-code share at 50 tokens. Groups with fewer than five "
                "complete deposits retain counts but no displayed estimate. "
                "Five is a display rule, not evidence of adequate precision. "
                "Discipline labels are often broad; dates are deposit dates, "
                "not code-authoring dates.</p>"
            )
            for group in ("period", "collection", "discipline"):
                grouped = [
                    r
                    for r in summarize(rows, group)
                    if r["language"] == language
                    and r["variant"] == variant
                    and r["metric"] == "clone_exact_union_50"
                    and r["population"] == "complete"
                ]
                body += table(
                    [
                        group.replace("_", " ").capitalize(),
                        "Selected",
                        "Complete",
                        "Median repeated code (%)",
                    ],
                    [
                        (
                            r["group"],
                            r["deposits"],
                            r["n"],
                            (
                                number(r["median"] * 100)
                                if r["n"] >= 5
                                else "Too few deposits"
                            ),
                        )
                        for r in grouped
                    ],
                )
            body += "</details></div>"
        paired = next(
            (
                r
                for r in sensitivity
                if r["language"] == language and r["metric"] == "clone_exact_union_50"
            ),
            None,
        )
        if paired:
            body += "<section><h3>Eligibility sensitivity on the same deposits</h3>"
            body += table(
                [
                    "Paired complete deposits",
                    "Primary median (%)",
                    "Excluding uncertain median (%)",
                    "Median within-deposit change (percentage points)",
                ],
                [
                    (
                        paired["paired_deposits"],
                        number(
                            scaled(paired["primary_median"], {"unit": "proportion"})
                        ),
                        number(
                            scaled(
                                paired["exclude_uncertain_median"],
                                {"unit": "proportion"},
                            )
                        ),
                        number(scaled(paired["median_change"], {"unit": "proportion"})),
                    )
                ],
            )
            body += (
                '<p class="note">Only deposits completely measured under both '
                "variants enter this comparison. The selector above shows each "
                "variant’s own eligible population, whose membership and "
                "coverage can differ.</p></section>"
            )
    body += (
        "<h2>Interpretation and evidence</h2><p>Environment flags "
        "record supported declarations, constraints, locked "
        "dependencies and interpreter versions. Unobserved evidence "
        "does not establish absent documentation; bundled metadata may "
        "describe a dependency rather than the execution environment. "
        "Filename evidence is separately retained in "
        "environment.json.</p>"
    )
    body += (
        "<p>Randomness results are conditional on recognized stochastic"
        " calls and complete flowR processing. A supplied seed "
        "expression anywhere in a deposit does not establish a fixed "
        "value or control of every random operation. NULL and omitted "
        "seed arguments do not count as supplied. Package-specific "
        "stochastic APIs and cross-file execution order remain "
        "incompletely covered.</p>"
    )
    body += (
        '<p class="note">Weak lexical path guesses and trivial '
        "whitespace counts are excluded from the profile. Raw lexical "
        "findings remain diagnostic evidence. Native R analyzers are "
        "not run unless configured; their absence appears as not "
        "measured. Source code and deposited configurations are never "
        "executed.</p><footer>"
    )
    links = [
        ("measurements.csv", "Deposit measurements"),
        ("summary.csv", "Distributions and coverage"),
        ("paired-sensitivity.csv", "Paired eligibility sensitivity"),
        ("by-period.csv", "All measures by period"),
        ("by-collection.csv", "All measures by collection"),
        ("by-discipline.csv", "All measures by discipline"),
        ("dictionary.json", "Measure dictionary"),
        ("environment.json", "Environment evidence"),
        ("native.parquet", "Native analyzer evidence"),
        ("manifest.json", "Run provenance"),
    ]
    body += " · ".join(f'<a href="{file}">{label}</a>' for file, label in links)
    body += (
        '</footer></main><script>document.querySelector("#variant")'
        '.addEventListener("change",e=>document.querySelectorAll("[data-variant]")'
        ".forEach(p=>p.hidden=p.dataset.variant!==e.target.value));</script>"
    )
    (output / "report.html").write_text(
        (
            '<!doctype html><html lang="en"><head><meta '
            'charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>Research '
            "code quality</title><style>"
        )
        + STYLE
        + "</style></head><body>"
        + body
        + "</body></html>"
    )
