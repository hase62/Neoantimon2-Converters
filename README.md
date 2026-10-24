# Neoantimon2 Community Converter Registry

Public registry: https://github.com/hase62/Neoantimon2-Converters

Discovery: https://www.hase62.jp/Neoantimon2-Converters/

This source includes nine pinned BA/EL/IM adapters (eight method families), plus
the original synthetic example. See the [catalog](CATALOG.md),
[offline external prediction walkthrough](EXTERNAL-QUICKSTART.md) and
[machine-readable upstream research](UPSTREAM-RESEARCH.json).
Local additions are not hosted until reviewed, merged and explicitly deployed.
Converters adapt output files; they do not install or execute prediction engines.

HTTPS index: https://www.hase62.jp/Neoantimon2-Converters/index.json

The canonical HTTPS domain is the existing account GitHub Pages domain.
No new domain or non-GitHub backend is used. Use the canonical URLs above:
the github.io alias was observed redirecting through HTTP before HTTPS,
even after this project enabled HTTPS enforcement. That alias is not the
recommended registry URL. Do not assume redirect hops are secure merely
because an initial URL starts with HTTPS.

Initial maintainer: @hase62. Public contributions use Pull Requests with
maintainer review. See [LICENSING.md](LICENSING.md), [LICENSE](LICENSE) and
[NOTICE](NOTICE) for the preserved infrastructure and converter boundaries.

Anyone with a GitHub account can propose an immutable `name@1.0.0` directory
containing a script, metadata.json and small nonprivate synthetic input/output
examples through a pull request. Read the script before use. Maintainers check
schema hygiene, paths and obvious repository safety, not scientific validity.
Accepted versions are immutable: changing code or metadata requires a new ID.
Issue links and vote snapshots are maintained separately in feedback.json;
they never authorize execution or change an accepted converter version.
Never include patient data, credentials, licensed predictors or model files.

The contract is `Rscript converter.R --input X --output standard.tsv --bundle export`
or the same arguments to python3. Output must be external-prediction-1.0.0.
Scripts do not install/execute predictors, upload annotations, reconstruct
origins or perform grading. Return nonzero for any failure. Users install any
converter dependencies explicitly. This subprocess is arbitrary user code,
not a security sandbox; a timeout is a resource bound, not a security boundary.

Run `python3 build_index.py .` to validate metadata, checksum scripts and build
index.json without executing any contributor code. The validator uses only
Python's standard library. The read-only PR workflow runs the trusted validator
from the base branch against submitted files as data, with no secrets or write
permissions. The workflow also rejects edits to accepted version directories.
It never uses pull_request_target or runs a contributed R/Python script.

GitHub Pages serves the reviewed default branch via a manually dispatched
GitHub Actions workflow, serving the output of
`python3 prepare_pages.py . /new/directory/outside/registry`. This builds the
index and stages only index.html, index.json, feedback.json, README.md,
converters/, LICENSE, NOTICE, LICENSING.md and .nojekyll. The read-only build
and privileged deployment are separate jobs. Nondefault branches cannot deploy.
Local validation alone does not establish hosted GitHub behavior.

## Submit a converter (any GitHub account)

1. Fork https://github.com/hase62/Neoantimon2-Converters and make a branch. Add
   `converters/your-name@1.0.0/`; use lowercase names and major.minor.patch.
   A fix to an accepted version goes in a **new** version directory.
2. Add one standalone converter.R or converter.py, input-X.tsv and expected.tsv.
   Fixtures must be small, synthetic and nonprivate. expected.tsv uses exactly
   the external-prediction-1.0.0 columns. README.md is recommended for input
   format, dependencies, installation, tested predictor versions and limitations;
   description/usage/license metadata are required even without a README.
3. Create metadata.json following metadata.schema.json. Set the exact directory
   ID, R/Python runtime and root-relative script path. Set the script SHA256
   with `shasum -a 256 converters/your-name@1.0.0/converter.py` (or converter.R).
   Declare your own script license and supported predictor versions; do not
   inherit the synthetic example's license without permission. Include full
   license terms and applicable notices in LICENSE.txt; see LICENSING.md. Use a stable
   upstream revision or an earlier commit containing the script as
   source_revision. Omit legacy issue_url/ok/ng fields; feedback is separate.
4. Run `python3 build_index.py .`. It validates submitted files as data and
   refreshes index.json. Open a Pull Request using the template. Describe how
   a user installs dependencies and runs the converter locally; any optional
   execution is your responsibility and is never a privileged CI step.
5. Maintainers check metadata, documentation, schema hygiene, checksums, paths
   and obvious security problems. This is **not scientific peer review**,
   official algorithm approval, or assurance that the converter is correct.
   CI does not execute your script or prove its output equals expected.tsv.

Version files are limited to 2 MiB each, 100 files/20 MiB per version, and
R/Python, JSON, TSV/CSV, Markdown/plain-text files (plus README/LICENSE).
Symlinks, special files, executable web content and binaries are refused.
feedback.json is limited to 2 MiB. The copied prediction contract is byte-identical
to Neoantimon2's frozen contract. CI checks expected.tsv structure, declared
enums/statuses, finite scores, percent units/ranges and duplicates without
executing the converter. Neoantimon2's R importer remains authoritative for
full HLA presenter resolution, task compatibility and biological matching.
No licensed model, predictor or private sample belongs in a PR.

## Find and use one exact version

Search the discovery page by ID, description or declared predictor version.
Each entry links its exact metadata and script and displays SHA256. Review
the script, dependencies and compatibility reports before downloading/executing.
Choose an explicit ID such as name@1.0.0, never an automatic "latest" version.
For a downloaded script, compare `shasum -a 256 /path/converter.py` with the
published digest. Checksum agreement identifies bytes, not code safety.
The R examples below support a configured local index or the public
HTTPS index URL above. An original
completed neo_project is required. Local `converter = "/path/converter.py"`
explicitly requests execution; registry lookup additionally requires first-use
`trust = TRUE`. Preserve inputs and reviewed scripts outside disposable runs.

## Community OK/NG, comments and broken converters

Any GitHub user can react +1 for OK or -1 for NG on the linked version Issue
and add comments. Include converter ID/SHA256, predictor/model version,
dependency/runtime version, expected versus actual result and a small synthetic
reproduction. Report incompatible predictor versions explicitly; an OK on
one version is not an endorsement of other versions. Use the broken-converter
Issue template when no feedback Issue exists, or to report a specific failure.
Never attach private provider outputs, patient data, credentials or licensed
files. Maintainers link the canonical Issue and record observed reaction totals
in feedback.json through a data-only PR, including refreshed_at. Counts stay
manual, can be stale, and do not authorize execution or certify science. No
database, Cloudflare, API token or hosted backend is needed for this workflow.

## Maintainer deployment

The owner maintains this standalone repository. Community PRs require one
maintainer/CODEOWNERS review and the validate status check. Accepted converter
files cannot be changed: use a new version directory. Infrastructure updates
need particular security review. The owner can perform documented maintenance
using administrator bypass; this is not independent contributor approval.
Do not add repository secrets or execute scripts in PR validation. Default
workflow tokens are read-only and cannot approve PRs.

Pages is configured with GitHub Actions as its source and github-pages accepts
only the main branch. Dispatch pages.yml on main after reviewing a change.
Its read-only build stages static assets; its privileged deployment job has
no checkout or converter execution. Direct action commits are pinned. Review
upstream/transitive action updates before changing those pins.

The initial feedback snapshot links [maintainer test Issue #3](https://github.com/hase62/Neoantimon2-Converters/issues/3).
Its OK=1 and NG=1 reactions are both from the same owner account @hase62.
The maintainer synthetic test PRs and Issue are operational smoke tests, not
independent community validation, scientific review or real predictor accuracy
claims. Feedback snapshots remain manual; an Issue's reaction counts can be
stale and can include maintainer test reactions. Genuine third-party reports,
licensed predictors and fork-account behavior require separate verification.

## Immutable metadata and mutable feedback

New submissions put only id, runtime, script, sha256, metadata,
supported_predictor_versions and source_revision in metadata.json. All files
in an accepted version directory remain immutable, including synthetic fixtures.
For compatibility, existing version files may retain the old issue_url/ok/ng
fields. The builder validates their hygiene and **ignores** these frozen copies;
it does not edit the accepted files or fall back to their obsolete counts.
The provided synthetic version directory is byte-for-byte unchanged.

feedback.json uses schema_version 1.0.0 and a feedback object keyed by accepted
converter ID. Each value has issue_url (GitHub Issue or null), nonnegative
integer ok/ng snapshots, and optional refreshed_at (UTC YYYY-MM-DDTHH:MM:SSZ
or null). An unlinked entry has zero counts and no timestamp. Missing IDs
default to unlinked/zero, displayed as unavailable feedback rather than live
zero votes. Duplicate IDs, unknown IDs, unexpected fields, malformed URLs,
counts and timestamps are rejected. feedback.schema.json documents this data
contract; build_index.py additionally checks referential integrity and dates.

The builder merges the mapping into the existing public index schema; the R
reader and pinned offline converter resolver need no change. A timestamp stays
in feedback.json, because adding it to public index entries would break the
current strict R reader. The static page reads both files and labels counts
as snapshots, including their recorded date or an explicit unknown date.

## Post-merge issue creation and snapshot updates

1. Review and merge a new immutable converter version with its real source
   revision and no issue link. Build the index; no votes are claimed current.
2. After merge, create one feedback Issue for the accepted ID through GitHub.
   Do not edit its accepted version directory. Record the real Issue URL in
   feedback.json via a separate data-only PR, initially with zero counts and
   no refresh timestamp. The issue template records ID/SHA and synthetic use.
3. Build with `python3 build_index.py .`. The link appears in index.json and
   remains on every subsequent rebuild, because feedback.json is authoritative.
4. A maintainer may record observed +1/-1 totals and their observation timestamp
   in another feedback-only PR. Rebuilding preserves these values and does
   not change any converter files. Snapshots can be stale; this scaffold does
   not implement automatic reaction synchronization or claim live counts.

The offline tests simulate this lifecycle with synthetic URLs, repeated index
builds and complete version-directory hash comparisons. They do not alone establish hosted GitHub behavior. For an existing registry adopting
this scaffold, merge the trusted validator/schema/workflow update first,
copy reviewed legacy feedback into the separate mapping once, then permit
feedback-only PRs. Do not relax accepted-file immutability for the migration.
Do not repair generated index.json alone; a rebuild intentionally replaces it.

GitHub users give **OK** with an issue's `+1` reaction and **NG** with `-1`.
Comments should describe tool/version, synthetic test, discrepancy and expected
behavior. GitHub accounts are required for reactions. These are community
observations, not official approval or scientific certification. The static
index displays snapshots and links to the issue. Unlinked entries show counts
as unavailable; linked snapshots may become stale. No per-analysis GitHub API call occurs. A future
read-only maintenance job may refresh counts using the
[official issue reaction endpoints](https://docs.github.com/en/rest/reactions/reactions#create-reaction-for-an-issue).
The [GitHub Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
describes why untrusted pull-request code must not execute with privileged access.

Package usage (after choosing a real URL, or entirely offline):

```r
neo_analyze_external(p, "X.tsv", policy = list(mode = "evidence_only"),
  converter_id = "synthetic-example@1.0.0", registry = "/local/registry/index.json")
# First use refuses execution and prints the pinned file and checksum for review.
neo_analyze_external(p, "X.tsv", policy = list(mode = "evidence_only"),
  converter_id = "synthetic-example@1.0.0", registry = "/local/registry/index.json",
  trust = TRUE) # explicit authorization to execute this exact script
```

Approval is stored beside the pinned bytes under the disposable run cache.
Subsequent use verifies and reuses the pin offline; changing the remote index
does not replace it. A new run requires trust again. Preserve converters and raw
prediction outputs outside runs to recreate analyses after deleting a run.
Feedback updates also do not replace a cached pin or its recorded discovery
snapshot. An OK vote does not approve local script execution.

## Execute one reviewed converter locally

With Neoantimon2 installed and a completed local neo_project `p`, choose the
exact version, inspect its public script and install dependencies yourself:

```r
registry <- "https://www.hase62.jp/Neoantimon2-Converters/index.json"
# Explicit selection for the synthetic example only:
policy <- list(mode = "external_rank", provider = "synthetic-model",
  run_id = "demo-run-1", task = "external:synthetic_score", metric = "score",
  score_direction = "higher_is_better")
a <- neo_analyze_external(p, "/path/to/output-X.tsv", policy,
  converter_id = "synthetic-example@1.0.0", registry = registry, trust = TRUE)
results <- neo_external_results(a)
neo_external_explain(a, results$candidate_id[[1L]])
```

`policy` is the explicit external ranking policy described by Neoantimon2's
external-prediction guide; the synthetic example uses external:synthetic_score,
provider synthetic-model, run_id demo-run-1, metric score, higher_is_better.
Without trust=TRUE first use stops with TRUST_REQUIRED before executing code.
SHA256 is verified before execution; later approved cache reuse needs no network.
Consent is per completed project and exact cached version, never granted by votes.
Scripts run with the user's local permissions. Inspect them; this is not a sandbox.
Original inputs stay in data, while generated outputs/caches stay in runs.
Portable export-bundle-only execution and universal downstream integration are
not supported: retain the completed project. Local paths also remain supported.
