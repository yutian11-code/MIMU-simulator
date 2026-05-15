# Public Video Template Library 100 Template Update

Date: 2026-05-13

## Result

- `standard_makeup_templates`
  - `source = 'machine_generated'`
  - `status = 'published'`
  - total: `100`
- visibility split:
  - `team = 98`
  - `private = 2`

## Base

Before this expansion round:

- published machine-generated templates: `50`

## Successful expansion batches

### Batch A

- `runId`: `public_video_run_1778684088667`
- `triggerSource`: `vimeo_100_batch_a`
- manifest: [public-video-100-batch-a-29.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-100-batch-a-29.json)
- result:
  - `candidateCount = 29`
  - `downloadedCount = 29`
  - `extractedCount = 29`
  - `draftCount = 29`
  - `autoReadyCount = 29`
  - `publishedVisibleCount = 29`
  - `failedCount = 0`

### Batch BC

- `runId`: `public_video_run_1778684712473`
- `triggerSource`: `vimeo_100_batch_bc`
- manifest: [public-video-100-batch-bc.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-100-batch-bc.json)
- result:
  - `candidateCount = 9`
  - `downloadedCount = 9`
  - `extractedCount = 9`
  - `draftCount = 9`
  - `autoReadyCount = 9`
  - `publishedVisibleCount = 9`
  - `failedCount = 0`

### Batch D

- `runId`: `public_video_run_1778684712488`
- `triggerSource`: `vimeo_100_batch_d`
- manifest: [public-video-100-batch-d.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-100-batch-d.json)
- result:
  - `candidateCount = 12`
  - `downloadedCount = 12`
  - `extractedCount = 12`
  - `draftCount = 12`
  - `autoReadyCount = 12`
  - `publishedVisibleCount = 12`
  - `failedCount = 0`

## Total added in this round

- `29 + 9 + 12 = 50`

So the machine-generated published library moved from:

- `50 -> 100`

## Supporting artifacts

- 50-template milestone record:
  - [public-video-template-library-50-template-update.md](/storage/nvme3/shushanfu/MIMU-colleague/docs/public-video-template-library-50-template-update.md)
- raw discovered Vimeo candidates:
  - [vimeo-public-video-candidates.md](/storage/nvme3/shushanfu/MIMU-colleague/docs/vimeo-public-video-candidates.md)
- intermediate expansion manifests:
  - [public-video-100-expansion.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-100-expansion.json)
  - [public-video-100-expansion.report.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-100-expansion.report.json)

## Notes

- The downloader format cap introduced in the previous round remained effective:
  - prefer `mp4`
  - cap to `720p`
  - recode to `mp4`
- This prevented single large Vimeo sources from blocking the sequential ingestion pipeline.
