# Security dependency maintenance — November 4, 2026

## Baseline

Reviewed `master` at `d43250c37c7bb14afb2711feb8fe0054875d61ba`.
The repository was public, not archived, and contained no tests or CI.
Dependabot PRs #1 (uvicorn 0.11.7), #2 (aiohttp 3.7.4), and #3
(NumPy 1.22.0) were open. The November 3 digest was read directly.

The digest's suggested versions are not a complete remediation plan. For
example, aiohttp 3.7.4 predates the fix in 3.13.3 for CVE-2025-69223, and
Starlette's 2026 advisories require versions beyond the digest's older 0.25.0
suggestion. NumPy 1.22 cannot be installed with the original Python 3.7 wheels.

## Changes

| Component | Previous | Replacement |
| --- | --- | --- |
| Python / container | 3.7 / Debian Stretch | 3.11 / Debian Bookworm |
| aiohttp | 3.5.4 | Removed along with automatic model downloading |
| NumPy | 1.16.3 | 1.26.4 (retain 1.x behavior) |
| Starlette | 0.12.0 | 1.10.0 |
| Uvicorn | 0.7.1 | 0.54.0 |
| python-multipart | 0.0.5 | 0.0.33 |
| fast.ai | 1.0.52 | 1.0.61 (retain v1 export format) |
| torch / torchvision | 1.1.0 / 0.3.0, cp37 wheels | 2.15.0+cpu / 0.29.2+cpu |
| setuptools | Previously unpinned | 84.2.1 |
| asyncio / aiofiles | Obsolete backport / 0.4.0 | Removed; stdlib asyncio and current Starlette file handling |

All 44 runtime dependencies are pinned with distribution hashes in
`requirements.txt`. fastprogress 1.0.3 avoids unrelated web-stack dependencies;
pandas 2.3.3 preserves the API used by v1.

Application routes now use the supported Starlette Route/lifespan APIs.
Import no longer creates and closes an event loop. Model loading occurs during
startup, CPU inference is offloaded and serialized, and uploads are bounded
before multipart parsing. The browser displays errors and uses textContent for
untrusted filenames and result text.

The compatibility adapter replaces only the version-check API used by fast.ai
v1's imports with importlib.metadata and packaging. It checks installed versions
and removes its temporary module registration after import. It avoids keeping
setuptools 80.9.0, which the audit found affected by CVE-2026-59890 and
GHSA-xmj3-9gf7-h52w. No vulnerability exemptions are configured.

The v1 loader follows fast.ai 1.0.61's load_learner reconstruction, uses CPU and
zero DataLoader workers, and explicitly sets `weights_only=False` for the
trusted local model only. It does not change torch.load globally. This is
necessary for object-based v1 exports and is not safe for untrusted models.

## Advisory evidence

- [Uvicorn CVE-2020-7694](https://github.com/advisories/GHSA-33c7-2mpw-hg34)
  and CVE-2020-7695: the digest's floor was 0.11.7; selected 0.54.0 is also
  checked against the current package advisory database.
- [aiohttp CVE-2025-69223](https://github.com/advisories/GHSA-6mq8-rvhq-8wgg):
  fixed in 3.13.3; removing aiohttp removes the dependency entirely, including
  the digest's CVE-2024-23334 and CVE-2024-30251 exposure.
- [Starlette CVE-2026-48818](https://github.com/advisories/GHSA-wqp7-x3pw-xc5r):
  fixed in 1.1.0.
- [Starlette CVE-2026-54282](https://github.com/advisories/GHSA-jp82-jpqv-5vv3):
  fixed in 1.3.0.
- [python-multipart CVE-2026-24486](https://github.com/advisories/GHSA-wp53-j4wj-2cfg):
  fixed in 0.0.22.
- [NumPy 1.22 release notes](https://numpy.org/doc/stable/release/1.22.0-notes.html):
  Python 3.7 support was dropped. Updating the interpreter and CPU wheel
  targets is essential, rather than merging PR #3 alone.
- [fast.ai v1 loader source](https://github.com/fastai/fastai1/blob/master/fastai/basic_train.py):
  basis for the local trusted-model compatibility loader.

The current full lock audit, rather than only these example advisory floors,
is the security validation. No finding was ignored or dismissed.

## Validation and limitations

Local checks on CPython 3.11.17 / Linux x86_64:

- Hash-enforced installation from the complete runtime lock succeeded in a
  fresh virtual environment; pip check found no broken requirements.
- 18 pytest tests passed, including real export/reload/HTTP prediction round
  trips for generated linear and ResNet-18 fast.ai v1 classifiers, multipart
  limits, missing/corrupt models, static files, CORS, and compatibility checks.
- The audit wrapper uses pip-audit 2.10.1 to check all 44 locked runtime
  dependencies, mapping the two official PyTorch +cpu builds to their upstream
  public versions because the CPU builds are not published on PyPI. It fails
  if any package is skipped. No known vulnerabilities were reported.
  A clean result is a point-in-time database check,
  not a guarantee of absence of vulnerabilities.
- JavaScript syntax and git whitespace checks passed.
- Docker was unavailable in the local executor. The added GitHub CI workflow
  builds the image, imports the ML stack as the non-root user, and checks
  container startup/readiness; consult its run
  results for that separate validation.

The original trained export is unavailable: the public download and a metadata
lookup through the connected Drive account both returned 404. Prediction
accuracy, any custom classes in that export, and exact compatibility with a
1.0.52-trained artifact therefore remain unverified. The generated test models
are never shipped or used as production fallbacks.

fast.ai v1 is unsupported upstream. This patch preserves its model format with
a tested compatibility boundary; a future v2 migration requires the trained
model or training code and separate prediction comparisons.

No deployment service was inspected or changed, and the original README's
sample Render URL does not establish an active deployment. The private full
Dependabot alert inventory was not available through the connector; findings
were checked using the digest, upstream advisories, and the complete local
dependency audit. GitHub may take time to refresh alerts after the merge.
