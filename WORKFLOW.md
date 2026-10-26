# Converter workflow and figure guide

[Catalog](CATALOG.md) · [Offline BA/EL/IM examples](EXTERNAL-QUICKSTART.md) · [Registry](README.md)

![Neoantimon2-Converters workflow: a completed project exports peptide or peptide–HLA queries with all origins; users run BA, EL or IM engines separately; nine pinned adapters produce the standard TSV; strict import preserves origins and native results while providing separate external rankings and explanations.](docs/assets/converter-workflow.svg)

[SVG](docs/assets/converter-workflow.svg) · [High-resolution PNG](docs/assets/converter-workflow.png) ·
[Vector PDF](docs/assets/converter-workflow.pdf) · [Editable draw.io](docs/assets/source/converter-workflow.drawio)

## Read the figure

Read left to right. Declared samples/patients, variants, references and patient
HLA support core Event → Origin → Peptide → Candidate reconstruction. Multiple
origins can share a peptide; candidate occurrences retain every contributing
Origin within their sample/context. `neo_export_bundle()` exports queries and
annotations from a **completed project**; native predictions/grades need not
have succeeded. Retain that project for import; a bundle alone is insufficient.

The user runs external engines separately. BA predicts binding affinity, EL
models presentation/eluted-ligand behavior, and IM models immunogenicity. The
Registry provides **nine adapters across eight method families**, not prediction
engines or model weights. All IDs shown are the actual published @1.0.0
registrations in the catalog. BigMHC EL/IM remain distinct provider identities.
MHCflurry's BA adapter is separate from its other upstream modes.

The converter transforms a pinned native-output schema into the exact
external-prediction-1.0.0 standard TSV. Strict literal peptide or peptide plus
presenter matching happens in `neo_analyze_external()` against the original
completed project. These nine adapters emit peptide+HLA scope; the broader core
contract also supports peptide-only evidence. Class II identity requires exact
alpha~beta pairs, with the documented MixMHC2pred no-context/DR restrictions.

`neo_external_results()` and `neo_external_explain()` expose a separate derived
view with every matched candidate's original Origin links. Ranking needs an
explicit metric/provider/run/direction policy. Native evidence, grades and ranks
are unchanged. Raw IM scores are not EL percentiles; IM scores do not automatically
produce somatic A–E grades. Genuine binding/presentation percentiles can support
only the released conditional grading route with all original prerequisites.
Missing, unsupported, NOT_RUN, valid zero and evaluated negatives remain distinct.

Solid arrows show data flow; the dashed connector supplies the retained completed
project to import. No arrow means automatic model execution, consensus across
incompatible scores or integration with every optional core workflow.

## Evidence supporting the arrows

The authoritative compatibility target is immutable Neoantimon2
[v0.3.0 / eca5f06](https://github.com/hase62/Neoantimon2/tree/eca5f06fc39c1275f1e4f47ba3886f532fb08a6b).
Core `R/external_export.R` defines the completed-project/query/origin graph;
`R/external_registry.R` and `R/external_converter.R` enforce script pins and
execution consent; `R/external_predictions.R` defines strict schema/matching;
`R/external_analysis.R` keeps derived views separate. Registry
[UPSTREAM-RESEARCH.json](UPSTREAM-RESEARCH.json), per-version PROVENANCE.json and
[the catalog](CATALOG.md) define all nine native schema/metric boundaries.
The released-core [integration script](tests/integration/released_v030.R) checks
all original origins/native files and independent external rankings.

The tests used **SCHEMA_FAITHFUL_SYNTHETIC_FIXTURE** values. No upstream engine,
accuracy, clinical immunogenicity or treatment efficacy was validated. See the
[offline walkthrough](EXTERNAL-QUICKSTART.md) for executable code and limitations.

## Rebuild and edit

Open the uncompressed draw.io source in a local diagrams.net editor to change
individual labels, boxes and connectors. SVG retains vector text/shapes and has
no external fonts/scripts/images. The renderer uses Python's standard library;
Chrome/Chromium is optional for PNG/PDF and size previews. No predictor needed.
It reuses the core figure's reviewed renderer/style; it supports a deliberately
small subset of draw.io primitives, not arbitrary diagram plugins.

```sh
python3 tools/build_workflow_figure.py \
  --source docs/assets/source/converter-workflow.drawio \
  --output docs/assets/converter-workflow.svg
# Optional exports with an existing Chrome/Chromium installation:
python3 tools/build_workflow_figure.py \
  --source docs/assets/source/converter-workflow.drawio \
  --output docs/assets/converter-workflow.svg \
  --png docs/assets/converter-workflow.png \
  --pdf docs/assets/converter-workflow.pdf \
  --work-dir /path/to/new/local-preview
```

The main SVG is 1200 × 760; PNG is 3600 × 2280. Full-size and 1200/900/600 px
previews must be inspected after changes. At 600 px, open the full-size figure
for small adapter names; text descriptions remain accessible independently.
The Pages builder stages only the explicitly reviewed figure files/guide;
it never runs this renderer, a converter or an upstream prediction engine.
