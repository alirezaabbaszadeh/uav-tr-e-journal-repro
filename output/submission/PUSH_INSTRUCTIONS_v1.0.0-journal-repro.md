# Push Instructions (v1.0.0-journal-repro)

No git remote is currently configured in this repository.

## 1) Add remote
```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
```

## 2) Push branch and tag
```bash
git push -u origin main
git push origin v1.0.0-journal-repro
```

## 3) Create GitHub release
Use this body:
- `output/submission/GITHUB_RELEASE_BODY_v1.0.0-journal-repro.md`

Optional checksum attachment reference:
- `output/submission/ARTIFACT_SHA256_journal_v3_full_20260219_000231.txt`
