root <- commandArgs(trailingOnly=TRUE)[[1]]
library <- file.path(normalizePath(root), 'library')
if (dir.exists(library)) .libPaths(c(library, .libPaths()))
check <- function(source) {
  input <- tempfile()
  on.exit(unlink(input))
  writeLines(source, input)
  out <- system2('Rscript', c('--vanilla', shQuote(file.path(root,'lint.R')),
                            shQuote(file.path(root,'renv.lock'))),
                 stdin=input, stdout=TRUE)
  jsonlite::fromJSON(paste(out,collapse='\n'), simplifyVector=FALSE)
}
a <- check(c('x == NA', 'stop("MUST NOT EXECUTE")'))
stopifnot(a$status == 'processed', any(vapply(a$findings, function(f) f$linter == 'equals_na_linter', logical(1))))
stopifnot(check('x <- (')$status == 'analysis_failed')
stopifnot(check('is.na(x)')$status == 'processed')
cat('R adapter checks passed\n')
