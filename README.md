# SeoulCook website

Static bilingual website, with a separate nine-language document library.
The existing Cloudflare Pages integration deploys `main` to `seoulcook.com`;
feature branches are verified through their Cloudflare preview checks.

## Product image refresh — 2026-11-25

- Three supplied archives contain 73 image records, representing 67 byte-distinct designs.
- The 2026-11-26 Hot Kimchi and Hot Bulgogi 100 ml PNGs add two distinct
  designs, bringing the live packaging gallery to 69 images. Their original
  pixels are retained; they replace the Gat Sauce representative photos only.
  Other sizes and the Low Sodium, Vegan, Halal and Kosher artwork stay distinct.
- Native image dimensions are retained. Product, size, label variant and previous
  packaging are recorded in `content/product-image-refresh-20261125.json`.
- Original 150 ml / 18-month SsamSsam information is retained; 100 ml imagery is
  separately labelled. The brand confirmed on 2026-11-25 that the seven
  Low Sugar Vegan products also belong to the Low Sodium collection. They are
  shared product entries, with 100 ml, 2 kg and 20 kg photographs in both
  collections. This assignment does not add numeric sodium claims.
- The 2 kg and 20 kg formats populate the Bulk collection. All 69 designs can
  be reached from `/products/packaging/`. A package-label design does not by
  itself establish certification, nutritional test results or a changed recipe.
- `content/catalog.json` contains 19 product entries, with sizes represented as
  packaging variants rather than duplicated products.

## Company and product documents

The document library uses `assets/catalogues/manifest-20261126-dipping.json`: company
profiles (7 pages), product catalogues (22 pages), and combined documents
(29 pages), in Korean, English, Spanish, Chinese, Japanese, Arabic, French,
German and Italian. Hindi is excluded. Each product catalogue includes all
69 supplied distinct designs. Original translated body copy is retained.
The 2026-11-26 revision updates 18 product / combined PDFs, while retaining
the nine unchanged company-profile files and their verified print pages.

Matching SVG print pages retain vector lettering and native-resolution images.
All active PDFs are below the 25 MiB individual-file hosting limit. Dated asset
paths avoid reusing the immutable cache URLs of older documents and images.
The older 2026-11-19 and initial 2026-11-25 documents remain available for rollback.
The Low Sodium revision adds only three revised print pages per language;
unchanged vector pages and images are reused.

## Reproduce and validate

The one-time source-image manifest is kept outside this public repository. It
contains the local path, archive member, dimensions and SHA-256 of each input.
Do not commit local credentials, private paths, supplier forms or source ZIPs.

Dependencies: Python, Pillow, lxml and PyMuPDF (tested with 2.1); Node is used for
JavaScript syntax checks. No new runtime dependency is loaded by the website.

```
python scripts/refresh_product_images.py INPUT_MANIFEST.json
python scripts/refresh_catalogues.py
python scripts/validate_image_refresh.py --manifest assets/catalogues/manifest-20261126-dipping.json
node --check assets/js/catalogues-20261126-dipping.js
node --check assets/js/catalogue-print-20261126-dipping.js
git diff --check
```

The dated image refresh refuses a repeat run against an already generated
batch. Reproduce it from its pre-refresh source revision or use a new dated
revision. Validation checks image identity, native dimensions, all 27 PDF
hashes and page counts, source body copy, the 69-image appendix in every
language, and all 261 vector print pages and their image references. It also
renders the nine combined documents for visual review. Browser checks cover
responsive pages, the nine-language selector and printable-page readiness.
`scripts/reflect_low_sodium.py` creates the brand-confirmed collection revision
from the initial 2026-11-25 release. Run it only from that pre-revision source
state; it refuses to overwrite the revised PDF filenames.
`scripts/refresh_dipping_images_20261126.py` creates the two-image revision
from the Low Sodium release; it preserves earlier assets and PDF editions.

## Rollback

Pre-refresh production checkpoint: `9c5a13b7fe2f2b106582bafae364c99277ed4b3d`.
Revert the release commits, preserving later unrelated changes, to restore
the prior HTML, catalogue data and document manifest. The old dated assets are
not deleted. Verify Cloudflare deployment and the restored public pages.
