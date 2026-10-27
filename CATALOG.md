# BA / EL / IM converter catalog

[User workflow](README.md) · [Worked BA/EL/IM examples](EXTERNAL-QUICKSTART.md) · [Machine-readable research](UPSTREAM-RESEARCH.json)

The nine BA/EL/IM converters listed in this catalog are publicly available through the [hosted Neoantimon2 Converter Registry](https://www.hase62.jp/Neoantimon2-Converters/) as of October 25, 2026. The Registry contains these **9 registrations / 8 method families** plus a synthetic-example converter. New local additions or pull requests are published only after review and deployment.

BigMHC-EL and BigMHC-IM are distinct scientific models with separate provider IDs. There are no aliases counted as new converters. Feedback for synthetic-example is maintainer testing, as explained in the [Registry feedback guide](README.md#community-okng-comments-and-broken-converters).

All input fixtures are **SCHEMA_FAITHFUL_SYNTHETIC_FIXTURE** files. No predictor, model weights, large dataset, GPU, Docker or new environment was installed or executed. Converters require Python >= 3.9 and its standard library. The existing Registry execution and 18-column external-prediction-1.0.0 contract are unchanged.

| Converter | Target version / schema | Target | MHC | Primary output metric / direction |
| --- | --- | --- | --- | --- |
| [bigmhc-el@1.0.0](converters/bigmhc-el@1.0.0/README.md) | git-199e890fa69a63646730bcecea0a520e08ca4f02 | EL | I | score (unitless, higher_is_better) |
| [bigmhc-im@1.0.0](converters/bigmhc-im@1.0.0/README.md) | git-199e890fa69a63646730bcecea0a520e08ca4f02 | IM | I | score (unitless, higher_is_better) |
| [prime-im@1.0.0](converters/prime-im@1.0.0/README.md) | 2.1 | IM | I | immunogenicity_percentile (percent, lower_is_better); immunogenicity_score (unitless, higher_is_better) |
| [deepimmuno-cnn@1.0.0](converters/deepimmuno-cnn@1.0.0/README.md) | git-df42ac5b6bddfe531268335e2dcb496559cd488b | IM | I | immunogenicity_score (unitless, higher_is_better) |
| [mixmhcpred-el@1.0.0](converters/mixmhcpred-el@1.0.0/README.md) | 3.0 | EL | I | presentation_percentile (percent, lower_is_better) |
| [mixmhc2pred-el@1.0.0](converters/mixmhc2pred-el@1.0.0/README.md) | 2.1-beta1 | EL | II | presentation_percentile (percent, lower_is_better) |
| [caphla-el@1.0.0](converters/caphla-el@1.0.0/README.md) | 2.0 | EL | I | presentation_score (unitless, higher_is_better) |
| [immuneapp-im@1.0.0](converters/immuneapp-im@1.0.0/README.md) | git-320e021e2339ee75c7da0d010a736c4fabe906c8 | IM | I | immunogenicity_score (unitless, higher_is_better) |
| [mhcflurry-ba@1.0.0](converters/mhcflurry-ba@1.0.0/README.md) | 2.0.6 | BA | I | affinity_nM (nM, lower_is_better); affinity_percentile (percent, lower_is_better) |

[Illustrated converter workflow and scientific boundaries](WORKFLOW.md).

## Native schemas and provenance

Each version README gives the executable command, input mode, interpretation, citation, licensing and limits. PROVENANCE.json gives mandatory/optional columns, immutable upstream URLs/commit, fixture hashes and exact metric mappings. Wide formats retain **all per-allele** selected measurements; best-allele summaries never fan out. Source row provenance includes the original input-byte SHA256, physical line, metric column and, for ImmuneApp, source group label. Run IDs are deterministic input hashes, not invented predictor run identifiers.

`predictor_version` declares the supported schema pin. Versionless outputs cannot establish the executable version: users must retain their original invocation/software provenance. `model_version` is empty because these files do not identify a weights release; a source commit is not a model-weight version. Provider IDs distinguish EL/IM/model families. No upstream example values, code, binaries or weights are redistributed. Independently authored adapters/fixtures use the Registry’s PolyForm Noncommercial 1.0.0 with full terms and notices in each version. Upstream licenses remain separate.

## Important mode restrictions

- MixMHC2pred supports only pinned 2.1-beta1 **no-context** output. DP/DQ pairs are explicit. DR beta shorthand requires a unique full DRA*01:01~DRB declaration in the real bundle; no alpha is invented. Other/ambiguous alpha declarations fail. Native NA remains unsupported; unknown/malformed scores fail.
- MHCflurry is pinned to 2.0.6 **--affinity-only**, default output names and one allele per row. Genotype/best-allele ambiguity fails. Affinity is nM, and optional affinity percentile remains separate.
- PRIME imports IM score/rank separately. Its binding-related columns are not imported as BA or EL. DeepImmuno-CNN supports only multiple-mode 9/10-mers; GAN output is unsupported.
- CapHLA imports Class I presentation only; raw affinity_score is not called nM. ImmuneApp imports the raw immunogenicity TSV for a single upstream sample group; the group is provenance, not a Neoantimon2 sample assignment.
- BigMHC/DeepImmuno upstream HLA rescue/fuzzy matching is not reproduced. Verify that upstream prediction actually used the intended allele. Converters normalize only documented reversible spellings, never truncate high-resolution alleles or guess identities.
- Plain missing/NaN/Inf is never zero: only documented missing encodings are mapped to explicit non-evaluated statuses; otherwise conversion fails before output.

## Considered but not registered

| Candidate / mode | Decision and uncertainty |
| --- | --- |
| IEDB Class I Immunogenicity | Official help establishes peptide/length/score display and masking dependence, but an exact pinned downloadable output schema/version was not immediately established. No form submission or gated software download. |
| MHCnuggets | Native peptide,ic50 output omits allele identity; no guess or new input-wrapper system added. |
| CapHLA-BA | Native affinity_score is untransformed model output; nM conversion/direction not established from immediately available serializer code. EL branch is supported. |
| NetMHCpan-BA | Considered as BA alternative; MHCflurry pinned affinity-only CSV offered a smaller explicit schema. No converter registered. |

IEDB’s mask configuration also affects score meaning; no allele-specific result was fabricated from an unversioned peptide score. MHCnuggets requires explicit external allele context not present in its native CSV; no new wrapper system was invented. CapHLA BA scale/direction remains unresolved in the short serializer review. These omissions do not imply a defect in those predictors.

## Local validation (explicit reviewed execution)

```sh
python3 build_index.py .
python3 -m unittest discover -s tests -v
python3 tests/converter_checks.py -v
python3 tools/build_converters.py
Rscript tests/integration/released_v030.R . /path/to/new/output
```

Existing CI/Pages hygiene remains data-only and does not discover the explicit execution test file. `converter_checks.py` deliberately is not named `test_*.py`; execute it only after reviewing the local code. The R command reuses an already installed immutable v0.3.0 package. Its examples validate conversion/import and origins, not predictor execution, accuracy or clinical response. External ranks are separate from native grades/ranks; no adapter requests somatic A–E grading.
