# Public Video Template Library Runbook

## Purpose

Use this pipeline to ingest public tutorial videos into the formal template
library. It retains raw source evidence under `backend/data/public-video-template-library/`,
extracts 5-step frame/audio evidence, and publishes machine-generated templates
into the existing standard template tables.

## Prerequisites

- PostgreSQL available at the backend `DATABASE_URL`
- `yt-dlp` available either through:
  - `MIMU_YT_DLP_BIN=/abs/path/to/yt-dlp`
  - or `yt-dlp` on `PATH`
  - or `python3 -m yt_dlp`
- Optional proxy for public video download:
  - `MIMU_PUBLIC_VIDEO_PROXY_URL=http://127.0.0.1:7890`
- Optional cookie support for protected platforms:
  - `MIMU_PUBLIC_VIDEO_COOKIES_FILE=/abs/path/to/cookies.txt`
  - or `MIMU_PUBLIC_VIDEO_COOKIES_FROM_BROWSER=chrome`

## Default manifest

The default seed manifest is:

```text
backend/data/public-video-template-library/public-video-seeds.json
```

It currently contains 35 public YouTube entries.

Note: the current default manifest is metadata-complete, but some platforms
such as YouTube or Bilibili may reject anonymous automated downloads. For
unattended smoke tests, prefer a manifest that points to anonymously accessible
sources, or provide browser cookies.

## Run a smoke ingestion

From the repo root:

```bash
bash scripts/run-public-video-template-library.sh --limit 2 --max-publish-count 2
```

Optional explicit manifest:

```bash
bash scripts/run-public-video-template-library.sh \
  --manifest /abs/path/to/public-video-seeds.json \
  --limit 5 \
  --max-publish-count 5
```

## Expected outputs

- Raw videos:
  - `backend/data/public-video-template-library/raw/<source-id>/`
- Extraction artifacts:
  - `backend/data/public-video-template-library/extractions/<source-id>/`
- Database rows:
  - `public_video_sources`
  - `public_video_assets`
  - `public_video_extractions`
  - `public_video_template_drafts`
  - `public_video_publish_runs`
  - `standard_makeup_templates`
  - `standard_makeup_template_versions`

## API verification

After backend startup:

```bash
curl -fsS -H "Authorization: Bearer demo-token" \
  http://127.0.0.1:13000/makeup-template-library/ingestion/runs

curl -fsS -H "Authorization: Bearer demo-token" \
  http://127.0.0.1:13000/makeup-template-library/templates
```

The ingestion runs response is:

```json
{
  "items": []
}
```

Each item includes `candidateCount`, `downloadedCount`, `extractedCount`,
`draftCount`, `autoReadyCount`, `publishedVisibleCount`, `publishedHiddenCount`,
`failedCount`, `startedAt`, `completedAt`, `createdAt`, and `updatedAt`.
