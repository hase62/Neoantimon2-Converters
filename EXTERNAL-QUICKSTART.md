# External prediction: BA, EL and IM

The [README](README.md) is the complete introductory workflow. This page extends
its offline project into separate BA/EL/IM worked examples.

[Converter catalog](CATALOG.md) · [Security reference](MAINTAINERS.md) ·
[Upstream evidence](UPSTREAM-RESEARCH.json)

The Registry provides format adapters, not prediction engines. Use the existing
Neoantimon2 **v0.3.0** installation and Python >= 3.9; these adapters need only
Python's standard library. Do not install predictors or download weights to run
this guide. Review the selected immutable script before authorizing execution.

## Your own predictions

1. Configure your original samples, references, HLA and inputs with
   `neo_config()` / `neo_project()`, then complete `p <- neo_run(p)`.
2. Export `bundle <- neo_export_bundle(p)`. Retain the completed project;
   export does not require successful native predictions or grades.
3. Run your separately installed/licensed predictor outside Neoantimon2. Use
   the precise version/mode listed in its converter README. Retain software,
   model, invocation and original output provenance.
4. Execute the reviewed converter with `--input`, `--output` and `--bundle`.
   Output must be a new filename. All selected scores retain their numeric
   values; native default field names and schemas must match.
5. Import standard TSV through `neo_analyze_external(p, standard, policy)`.
   Alternatively select the same `converter_id` and reviewed local `index.json`
   on the raw input with explicit first-use `trust = TRUE`.
6. Read `neo_external_results()` and `neo_external_explain()`. Select an explicit
   provider/run/task/metric/direction for ranking; native results stay unchanged.

## Complete offline walkthrough

**All prediction values below are SCHEMA_FAITHFUL_SYNTHETIC_FIXTURE values.**
They are not produced by the upstream tools. The test project has two 9-mer
peptides, three origins and ten candidates across five declared presenters.
One peptide has two distinct origins. Its reference data are the installed
hand-authored technical fixtures, not a human reference-genome benchmark.

Start R in this Registry checkout with the immutable Neoantimon2 v0.3.0 package
already installed. This runs no predictor, network request or installer:

```r
library(Neoantimon2)
stopifnot(as.character(packageVersion("Neoantimon2")) == "0.3.0")
registry_root <- normalizePath(".")
example_dir <- tempfile("neo-converter-demo-") # new output, temporary for this R session
status <- system2(file.path(R.home("bin"), "Rscript"),
  c(shQuote(file.path(registry_root, "tests/integration/released_v030.R")),
    shQuote(registry_root), shQuote(example_dir)))
stopifnot(status == 0L)
meta <- jsonlite::read_json(file.path(example_dir, "integration-results.json"))
p <- neo_project(path = meta$project)
before <- neo_results(p)
cat("Example files:", example_dir, "\n")
```

Choose a durable **new** output location instead of `tempfile()` to retain the
example. The integration script builds the synthetic project, exports through
`neo_export_bundle()`, constructs native-format schema fixtures matched to its
queries, and invokes **all nine converters via the actual local Registry** with
explicit trust. It verifies imports, ranks, explanations, origins, missingness,
project reopening, and hashes of every pre-existing native artifact. An IM
somatic-grade request is explicitly rejected by released core prerequisites.

The next block repeats conversion explicitly for three worked examples, using
new output filenames. It is also executable after the first block:

```r
convert_one <- function(id, filename) {
  target <- file.path(example_dir, filename)
  status <- system2(Sys.which("python3"), c(
    shQuote(file.path(registry_root, "converters", id, "converter.py")),
    "--input", shQuote(file.path(example_dir, id, "native-output.tsv")),
    "--output", shQuote(target), "--bundle", shQuote(meta$export_bundle)))
  stopifnot(status == 0L)
  target
}
ba_tsv <- convert_one("mhcflurry-ba@1.0.0", "ba-review.tsv")
el_tsv <- convert_one("bigmhc-el@1.0.0", "el-review.tsv")
im_tsv <- convert_one("bigmhc-im@1.0.0", "im-review.tsv")

analyze_one <- function(path, metric) {
  standard <- read.delim(path, colClasses = "character", check.names = FALSE)
  channel <- standard[standard$metric == metric, , drop = FALSE]
  stopifnot(nrow(channel) > 0L)
  fields <- c("provider", "run_id", "task", "metric", "score_direction")
  policy <- c(list(mode = "external_rank"), as.list(channel[1L, fields]))
  a <- neo_analyze_external(p, path, policy = policy)
  results <- neo_external_results(a)
  id <- results$candidate_id[results$ligand_sequence == "MQPGKPGKP" &
    results$mhc_key == "HLA-A*02:01"][[1L]]
  explanation <- neo_external_explain(a, id)
  stopifnot(length(explanation$candidates[[1L]]$origins) == 2L)
  print(results[, c("ligand_sequence", "mhc_key", "external_status",
    "external_score", "external_rank")])
  list(analysis = a, results = results, explanation = explanation)
}
BA <- analyze_one(ba_tsv, "affinity_nM")
EL <- analyze_one(el_tsv, "score")
IM <- analyze_one(im_tsv, "score")
stopifnot(identical(neo_results(p), before))
stopifnot(EL$analysis$analysis_id != IM$analysis$analysis_id,
  !identical(EL$results$external_rank, IM$results$external_rank))
```

| Demo | Native-format synthetic file | Imported metric | Unit / direction |
| --- | --- | --- | --- |
| BA | `mhcflurry-ba@1.0.0/native-output.tsv` (CSV) | affinity_nM | nM / lower |
| EL | `bigmhc-el@1.0.0/native-output.tsv` (CSV) | score | unitless / higher |
| IM | `bigmhc-im@1.0.0/native-output.tsv` (CSV) | score | unitless / higher |

The `*-review.tsv` files contain the exact standard 18-column format; the
per-method `standard.tsv`, `external-results.csv` and
`explanation-provenance.json` are retained under the generated method directory.
`integration-results.json` records analysis IDs and validation counts. Native
Class II candidates without Class I predictions remain NOT_PREDICTED, not
negative or zero. MHCflurry's optional affinity percentile is a **separate BA
metric**, not the IC50 value. PRIME's IM percentile is `external_percentile`,
not an EL rank. No worked example requests somatic grading.

## Scientific boundaries

BA, EL and IM have different targets and incompatible score scales. EL and IM
are intentionally analyzed as separate channels on the same candidate set;
the different synthetic rankings prove traceability, not model agreement or
predictive accuracy. IM scores are not clinical immunogenicity measurements;
a high IM score does not guarantee an immune response. Raw sigmoid/softmax
outputs are not claimed calibrated probabilities.

Missing, unsupported, failed, not evaluated, valid zero and evaluated negative
evidence remain different states. No missing score is replaced by zero. Scores
that cannot be represented faithfully fail clearly; invalid peptide characters
cannot be imported as a valid query. These adapters do not infer HLA identity,
run upstream fuzzy matching or broadcast best-allele scores to every allele.
Exact Class II alpha/beta identity and the no-context restriction matter.

Validation status:
`CONVERTER_AND_IMPORT_VALIDATED_WITH_SCHEMA_FAITHFUL_FIXTURE`.
No upstream predictor was executed. Software/model acquisition, licensing and
actual predictor execution remain the user's responsibility. The core research
outputs do not establish clinical immunogenicity or treatment efficacy.
