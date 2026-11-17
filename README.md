# get-perks-social

Renders Get Perks social graphics with GitHub Actions so they have public image URLs for Instagram, Facebook and LinkedIn.

- Write a page spec list to `specs/<post id>.json` (templates and fields are documented at the top of `render.py`).
- The workflow renders `out/<page id>.png` and records each page's spec hash in `out/manifest.json`.
- Image URL: `https://raw.githubusercontent.com/hjjconsultingltd-sys/get-perks-social/main/out/<page id>.png`
- LinkedIn image uploads: write `uploads/<name>.json` with `png`, `upload_url` and `image_urn`; the result appears in `out/uploads/<name>.json`.

Posting rules, the queue and the schedule live in the Get Perks Claude project (`claude/get-perks-social-content.md` and `claude/get-perks-social-queue.md`).
