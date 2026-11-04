args <- commandArgs(trailingOnly = TRUE)
library <- file.path(dirname(normalizePath(args[[1]])), 'library')
if (dir.exists(library)) .libPaths(c(library, .libPaths()))
lock <- jsonlite::fromJSON(args[[1]], simplifyVector = FALSE)
for (p in names(lock$Packages)) {
  stopifnot(utils::packageVersion(p) == package_version(lock$Packages[[p]]$Version))
}
stopifnot(as.character(getRversion()) == lock$R$Version)
source <- paste(readLines(file('stdin'), warn = FALSE), collapse = '\n')
rules <- c('equals_na_linter', 'duplicate_argument_linter', 'indentation_linter',
           'line_length_linter')
result <- tryCatch({
  parse(text = source, keep.source = TRUE)
  linters <- setNames(lapply(rules, function(x) getExportedValue('lintr', x)()), rules)
  linters$line_length_linter <- lintr::line_length_linter(100L)
  findings <- lintr::lint(text = source, linters = linters, parse_settings = FALSE,
                         cache = FALSE)
  list(status = if (any(vapply(findings, function(x) x$type == 'error', logical(1))))
    'analysis_failed' else 'processed', findings = unclass(findings))
}, error = function(e) list(status = 'analysis_failed', error = conditionMessage(e), findings = list()))
result$tool <- 'lintr'
result$version <- as.character(utils::packageVersion('lintr'))
result$r_version <- as.character(getRversion())
cat(jsonlite::toJSON(result, auto_unbox = TRUE, null = 'null'))
