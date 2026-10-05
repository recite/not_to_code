
library("pkgsearch")

pkgs = read_csv("data/imports_per_package.csv")
pkgs$last_update = NA

for(i in 1:nrow(pkgs)){
	print(i)
	out <- cran_package_history(pkgs$imports[i])
	pkgs$last_update[i] <- out[nrow(out), "Date/Publication"]
}

# Retry function with a maximum of 3 attempts
retry_cran_package_history <- function(pkg_name, max_attempts = 3) {
  attempt <- 1
  while (attempt <= max_attempts) {
    print(paste("Package:", pkg_name, "Attempt:", attempt))
    out <- tryCatch(
      cran_package_history(pkg_name),
      error = function(e) {
        print(paste("Error in attempt", attempt, ":", conditionMessage(e)))
        return(NULL)
      }
    )
    if (!is.null(out)) {
      return(out)
    }
    attempt <- attempt + 1
    Sys.sleep(5)  # Wait 5 seconds before the next attempt (adjust if needed)
  }
  return(NULL)  # Return NULL if all attempts fail
}

# Loop through the packages and get the last update date
for (i in seq_len(nrow(pkgs))) {
  pkg_name <- pkgs$imports[i]
  out <- retry_cran_package_history(pkg_name)
  if (length(out) > 0 && "Date/Publication" %in% colnames(out)) {
    pkgs$last_update[i] <- out[nrow(out), "Date/Publication"]
  }
}

write_csv(pkgs, "data/imports_per_package_with_last_updated.csv")

# Not the right thing as best calculated when the code was used. Either way, numbers look pretty ~ good.

summary(as.numeric(difftime(Sys.time(), pkgs$last_update, units = "weeks"))/52, na.rm = T)

#    Min.  1st Qu.   Median     Mean  3rd Qu.     Max.     NA's 
# 0.00037  0.33699  0.89092  1.85142  2.48060 11.34296       33 

weighted.mean(as.numeric(difftime(Sys.time(), pkgs$last_update, units = "weeks"))/52, w = pkgs$count, na.rm = T)

# [1] 1.45093



