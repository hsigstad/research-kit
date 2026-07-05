#!/usr/bin/env bash
# Shared R package install for the claude-sandbox image. Runs as root so
# packages land in the system library /usr/local/lib/R/site-library.
# Fails loudly: if any package is missing afterwards the build aborts, so a
# stale image can never silently ship without its R libraries.
#
# rdd was archived on CRAN (orphaned; last release 0.57), so it is not in the
# current contrib index — install it separately from the CRAN archive by URL.
# Its deps (AER, sandwich, lmtest, Formula) come from the main list below.
set -euo pipefail

Rscript -e '
    pkgs <- c(
        "dplyr", "readr", "tidyr", "lubridate", "arrow",
        "fixest", "lfe", "data.table", "dtplyr", "purrr", "ggplot2",
        "kableExtra", "knitr", "stringr", "forcats", "broom",
        "modelsummary", "did", "sandwich", "lmtest",
        "haven", "marginaleffects", "tidyverse",
        "Hmisc", "quantreg", "stargazer",
        "tinytable", "rdrobust", "rddensity",
        "estimatr", "jsonlite", "boot",
        "ggpubr", "gridExtra", "scales", "readxl",
        "janitor", "AER", "MatchIt", "clubSandwich"
    );
    install.packages(pkgs, repos = "https://cloud.r-project.org", Ncpus = 4);
    install.packages("https://cran.r-project.org/src/contrib/Archive/rdd/rdd_0.57.tar.gz", repos = NULL, type = "source");
    all_pkgs <- c(pkgs, "rdd");
    missing <- all_pkgs[!all_pkgs %in% rownames(installed.packages())];
    if (length(missing)) { cat("FAILED to install:", missing, "\n"); quit(status = 1) }
'
