# Neoantimon2-Converters

**Use an external prediction method without losing your candidate's origins.**
A converter is a small format adapter: it turns one supported prediction program's
output into the TSV that Neoantimon2 can import. You need one when you have an
external tool's native output rather than an already standardized table.

Neoantimon2 reconstructs candidates and interprets evidence. This independent
Registry supplies adapters; **it does not run prediction engines or bundle their
software, models or weights**.

![Four steps: export queries from Neoantimon2, run a BA/EL/IM engine separately, convert its output format, and import into the retained project. Origins stay traceable and native results stay unchanged.](docs/assets/converter-workflow.svg)

[Start with your files](#start-with-your-files) · [Convert and import](#convert-and-import) ·
[Offline example](#try-it-offline) · [Choose a converter](#published-converters)

## Start with your files

You need an installed Neoantimon2 **v0.3.0**, a **completed project** `p`, its
Export Bundle and the external predictor's output. Native scores/grades need
not be available. Keep the original project for import; the bundle alone cannot
replace it. No new HLA typing or peptide reconstruction happens here.

```r
library(Neoantimon2)
bundle <- neo_export_bundle(p)
bundle$path
```

The bundle contains unique `peptides.tsv` / `pmhc_queries.tsv`, candidate and
Origin annotations and `candidate_origin_links.tsv`. Supply queries in the
format required by your selected predictor, run it **separately**, and keep its
version/model/invocation and original output. Patient data stays local.

| Choose the scientific target | What the score means |
| --- | --- |
| **BA — binding affinity** | e.g. IC50 in nM, lower is better; affinity percentiles are separate measurements |
| **EL — eluted ligand / presentation** | Model score or percentile for presentation-related behavior |
| **IM — immunogenicity** | Immunogenicity-related score or percentile, not a clinical immune-response measurement |

These scales are not interchangeable. Raw IM scores are not EL percentiles;
model scores are not automatically calibrated probabilities.

## Convert and import

Choose the **exact converter ID/version and supported predictor mode** from the
catalog below. Review its README, PROVENANCE, license and script. Python ≥ 3.9
and its standard library suffice for the nine published adapters. No predictor
installation is needed to convert an existing output file.

For example, after obtaining `bigmhc-el@1.0.0/converter.py`, compare its SHA256
with the entry in the hosted `index.json` or your reviewed local index:

```sh
shasum -a 256 converters/bigmhc-el@1.0.0/converter.py
python3 converters/bigmhc-el@1.0.0/converter.py \
  --input /your/predictions/bigmhc.csv \
  --output /your/predictions/standard.tsv \
  --bundle /your/completed-project/results/export_bundle
```

Replace the paths; output must be a **new** file. Checksum agreement identifies
bytes, not code safety. Executing a converter uses your local privileges: inspect
it and authorize the operation. It is not a sandbox. Original files are not modified.

A concrete **SCHEMA_FAITHFUL_SYNTHETIC_FIXTURE**, not a model run:

```csv
mhc,pep,len,BigMHC_EL
HLA-A*02:01,SIINFEKLA,9,0
HLA-B*07:02,SIINFEKLA,9,0.875
```

Selected columns of the converted output are shown below. The converter writes
**all 18** standard columns, including schema/model/run identity and source-row
provenance; this display is not an alternative input schema.

| peptide_sequence | mhc_key | provider / metric | score | unit / score_direction |
| --- | --- | --- | ---: | --- |
| SIINFEKLA | HLA-A*02:01 | bigmhc-el / score | 0 | unitless / higher_is_better |
| SIINFEKLA | HLA-B*07:02 | bigmhc-el / score | 0.875 | unitless / higher_is_better |

Zero is evaluated data, not a missing prediction. For a converted BigMHC-EL table
matched to your original project, import a deliberately chosen channel:

```r
standard_tsv <- path.expand("~/predictions/standard.tsv")
scores <- read.delim(standard_tsv, colClasses = "character", check.names = FALSE)
channel <- scores[scores$provider == "bigmhc-el" & scores$metric == "score", ]
stopifnot(nrow(channel) > 0L)
fields <- c("provider", "run_id", "task", "metric", "score_direction")
stopifnot(nrow(unique(channel[, fields])) == 1L)
policy <- c(list(mode = "external_rank"), as.list(channel[1L, fields]))
a <- neo_analyze_external(p, standard_tsv, policy = policy)
r <- neo_external_results(a)
id <- r$candidate_id[r$external_status == "evaluated"][[1L]]
neo_external_explain(a, candidate_id = id)
```

Matching is strict peptide or peptide+full HLA identity. These nine adapters emit
peptide+HLA evidence; Class II pairs remain exact. All matched original Origins
are retained. Results/explanations and external ranking remain **separate**;
native evidence, grades and ranks stay unchanged. Raw scores, especially IM,
do not automatically produce somatic A–E grades. Other methods require their
own explicit provider/metric/direction, not the BigMHC policy by analogy.

Neoantimon2 can also select a version through a local/HTTPS Registry index.
First use requires `trust = TRUE` after review; later approved cached bytes are
verified offline. Without consent it stops with `TRUST_REQUIRED`. Direct standard
TSV import above executes no converter. The canonical index is
[hosted here](https://www.hase62.jp/Neoantimon2-Converters/index.json).

## Try it offline

From this Registry checkout, with Neoantimon2 v0.3.0 and its dependencies already
installed, review the local scripts and run this complete synthetic demonstration.
It executes format adapters, **not prediction engines**, and needs no network:

```r
library(Neoantimon2)
registry_root <- normalizePath(".")
example_dir <- tempfile("neo-converter-demo-")
status <- system2(file.path(R.home("bin"), "Rscript"), c(
  shQuote(file.path(registry_root, "tests/integration/released_v030.R")),
  shQuote(registry_root), shQuote(example_dir)))
stopifnot(status == 0L)
meta <- jsonlite::read_json(file.path(example_dir, "integration-results.json"))
p <- neo_project(path = meta$project)
cat("Synthetic output files:", example_dir, "\n")
```

The script builds **3 events, 3 origins and 10 candidates** for two 9-mer peptides
and five presenters. It converts/imports all nine adapters, checks every Origin,
native artifact hashes and independent EL/IM rankings. Its synthetic predictions
are not biological validation. In the import block above, set `standard_tsv` to
`file.path(example_dir, "bigmhc-el@1.0.0", "standard.tsv")` to inspect that EL run.
Use a durable new output path rather than R temporary storage if retaining results.

## Published converters

Nine adapters across **eight method families** are public, plus
`synthetic-example@1.0.0`. New submissions are published only after review and
deployment. Choose a target, then check the method’s pinned schema:

| Target | Published adapters (all @1.0.0) |
| --- | --- |
| BA | MHCflurry BA |
| EL | BigMHC EL, MixMHCpred, MixMHC2pred, CapHLA EL |
| IM | BigMHC IM, PRIME, DeepImmuno CNN, ImmuneApp IM |

The [catalog](CATALOG.md) gives exact IDs, supported versions, units/directions,
commands, restrictions and citations. Do not infer compatibility with other
versions/modes. MixMHC2pred is pinned to no-context output; BigMHC fuzzy allele
rescue is not reproduced. The [BA/EL/IM worked examples](EXTERNAL-QUICKSTART.md)
continue the same offline project with one selected run per category.

## Limitations and reproducibility

Validation status is **CONVERTER_AND_IMPORT_VALIDATED_WITH_SCHEMA_FAITHFUL_FIXTURE**.
No upstream prediction engine was executed. Conversion/import tests do not
establish model accuracy or clinical immunogenicity/treatment efficacy. A high IM
score does not guarantee an immune response. Missing/unsupported/failed results,
valid zero and evaluated negative evidence stay distinct; do not substitute zero
for missing data or average incompatible scores.

Keep original prediction files, model/software versions, the completed project,
reviewed converter ID/SHA256 and matching reference information. Vendor licensing,
installation and model acquisition remain your responsibility. Full per-adapter
source/fixture provenance is retained in its immutable PROVENANCE.json and the
[machine-readable inventory](UPSTREAM-RESEARCH.json).

## Community OK/NG, comments and broken converters

Community feedback is not scientific certification or execution consent.
[Issue #3](https://github.com/hase62/Neoantimon2-Converters/issues/3) and its
one-OK/one-NG snapshot are retained **maintainer synthetic testing**, not independent
user evaluation. Do not upload patient data. [Maintenance/security reference](MAINTAINERS.md)
contains submission, immutable-version, feedback and deployment rules; none are
relaxed. [Figure exports and editing](WORKFLOW.md) are separate from this user path.

[LICENSE](LICENSE), [NOTICE](NOTICE) and [LICENSING.md](LICENSING.md) preserve
infrastructure/converter boundaries and third-party terms. A checksum or vote is
not a security guarantee. Core scientific analysis remains in the released
Neoantimon2 package; this Registry does not change its APIs or algorithms.
