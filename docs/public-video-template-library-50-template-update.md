# Public Video Template Library 50 Template Update

Date: 2026-05-13

## Result

- `standard_makeup_templates`
  - `source = 'machine_generated'`
  - `status = 'published'`
  - total: `50`
- visibility split:
  - `team = 48`
  - `private = 2`

## This expansion batch

Base before this update:

- published machine-generated templates: `34`

Successful expansion run:

- `runId`: `public_video_run_1778681062272`
- `triggerSource`: `vimeo_batch_2_new16`
- manifest: [public-video-vimeo-batch-2-new16.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-vimeo-batch-2-new16.json)
- result:
  - `candidateCount = 16`
  - `downloadedCount = 16`
  - `extractedCount = 16`
  - `draftCount = 16`
  - `autoReadyCount = 16`
  - `publishedVisibleCount = 16`
  - `failedCount = 0`

Published source URLs in this batch:

1. `https://vimeo.com/596477675`
2. `https://vimeo.com/885185660`
3. `https://vimeo.com/885185880`
4. `https://vimeo.com/885186471`
5. `https://vimeo.com/885186480`
6. `https://vimeo.com/885186826`
7. `https://vimeo.com/885186853`
8. `https://vimeo.com/885186980`
9. `https://vimeo.com/885187031`
10. `https://vimeo.com/885187066`
11. `https://vimeo.com/885187293`
12. `https://vimeo.com/885187561`
13. `https://vimeo.com/885187877`
14. `https://vimeo.com/885187899`
15. `https://vimeo.com/885188269`
16. `https://vimeo.com/885188342`

## Supporting artifacts

- candidate discovery notes: [vimeo-public-video-candidates.md](/storage/nvme3/shushanfu/MIMU-colleague/docs/vimeo-public-video-candidates.md)
- cleaned batch manifest: [public-video-vimeo-batch-2.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-vimeo-batch-2.json)
- final success manifest: [public-video-vimeo-batch-2-new16.json](/storage/nvme3/shushanfu/MIMU-colleague/backend/data/public-video-template-library/public-video-vimeo-batch-2-new16.json)

## Pipeline fix made during this update

To avoid single Vimeo sources downloading very large original files and blocking sequential ingestion, the downloader was updated to request bounded extraction-friendly video formats:

- prefer `mp4`
- cap height at `720`
- recode to `mp4`

Relevant file:

- [public-video-downloader.service.ts](/storage/nvme3/shushanfu/MIMU-colleague/backend/src/makeup-templates/template-library/public-video-ingestion/public-video-downloader.service.ts)
