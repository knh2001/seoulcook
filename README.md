# SeoulCook website

Static bilingual website, with a separate nine-language document library.
The existing Cloudflare Pages integration deploys `main` to `seoulcook.com`;
feature branches are verified through their Cloudflare preview checks.

## Product image refresh — 2026-11-25

- Three supplied archives contain 73 image records, representing 67 byte-distinct designs.
- Native image dimensions are retained. Product, size, label variant and previous
  packaging are recorded in `content/product-image-refresh-20261125.json`.
- Original 150 ml / 18-month SsamSsam information is retained; 100 ml imagery is
  separately labelled. Low Sugar Vegan is presented in the Vegan collection,
  while Low Sodium remains a distinct development collection.
- The 2 kg and 20 kg formats populate the Bulk collection. All 67 designs can
  be reached from `/products/packaging/`. A package-label design does not by
  itself establish certification, nutritional test results or a changed recipe.
- `content/catalog.json` contains 19 product entries, with sizes represented as
  packaging variants rather than duplicated products.

## Company and product documents

The document library uses `assets/catalogues/manifest-20261125.json`: company
profiles (7 pages), product catalogues (21 pages), and combined documents
(28 pages), in Korean, English, Spanish, Chinese, Japanese, Arabic, French,
German and Italian. Hindi is excluded. Each product catalogue includes all
67 supplied distinct designs. Original translated body copy is retained.

Matching SVG print pages retain vector lettering and native-resolution images.
All active PDFs are below the 25 MiB individual-file hosting limit. Dated asset
paths avoid reusing the immutable cache URLs of older documents and images.
The older 2026-11-19 documents and images remain available for rollback.

## Reproduce and validate

The one-time source-image manifest is kept outside this public repository. It
contains the local path, archive member, dimensions and SHA-256 of each input.
Do not commit local credentials, private paths, supplier forms or source ZIPs.

Dependencies: Python, Pillow, lxml and PyMuPDF (tested with 2.1); Node is used for
JavaScript syntax checks. No new runtime dependency is loaded by the website.

```
python scripts/refresh_product_images.py INPUT_MANIFEST.json
python scripts/refresh_catalogues.py
python scripts/validate_image_refresh.py
node --check assets/js/catalogues-20261125.js
node --check assets/js/catalogue-print-20261125.js
git diff --check
```

The dated image refresh refuses a repeat run against an already generated
batch. Reproduce it from its pre-refresh source revision or use a new dated
revision. Validation checks image identity, native dimensions, all 27 PDF
hashes and page counts, source body copy, the 67-image appendix in every
language, and all 252 vector print pages and their image references. It also
renders the nine combined documents for visual review. Browser checks cover
responsive pages, the nine-language selector and printable-page readiness.

## Rollback

Pre-refresh production checkpoint: `9c5a13b7fe2f2b106582bafae364c99277ed4b3d`.
Revert the two release commits, preserving later unrelated changes, to restore
the prior HTML, catalogue data and document manifest. The old dated assets are
not deleted. Verify Cloudflare deployment and the restored public pages.
