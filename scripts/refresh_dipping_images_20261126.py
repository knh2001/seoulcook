"""Add two supplied 100 ml designs, preserving prior products and releases."""
from copy import deepcopy
from pathlib import Path
import hashlib, json, shutil
from PIL import Image
from lxml import html, etree
import refresh_catalogues as g
import refresh_product_images as web
import reflect_low_sodium as print_helpers

ROOT = g.ROOT
REV = '20261126-dipping'
BASE = '20261125-low-sodium'
REVIEW = ROOT.parent / 'outputs/2026-11-26-dipping-images'
SOURCES = [('hot-kimchi', 'KakaoTalk_Photo_2026-11-26-14-06-41 001.png'),
           ('hot-bulgogi', 'KakaoTalk_Photo_2026-11-26-14-06-41 002.png')]
HEADINGS = {
    'ko': '핫김치·핫불고기 디핑소스 · 100ml', 'en': 'Hot Kimchi & Hot Bulgogi · 100 ml',
    'es': 'Hot Kimchi y Hot Bulgogi · 100 ml', 'zh': 'Hot Kimchi与Hot Bulgogi蘸酱 · 100 ml',
    'ja': 'Hot Kimchi・Hot Bulgogi ディッピングソース · 100 ml',
    'ar': 'صلصتا Hot Kimchi وHot Bulgogi · 100 مل',
    'fr': 'Sauces dip Hot Kimchi et Hot Bulgogi · 100 ml',
    'de': 'Hot Kimchi und Hot Bulgogi Dipsaucen · 100 ml',
    'it': 'Salse dip Hot Kimchi e Hot Bulgogi · 100 ml',
}


def prepare_assets():
    images = []
    audit = []
    for flavour, name in SOURCES:
        source = Path.home() / 'Downloads' / name
        data = source.read_bytes(); sha = hashlib.sha256(data).hexdigest()
        dest = ROOT / 'assets/img/products-20261126' / (flavour + '-dipping-100ml-' + sha[:10] + '.png')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert hashlib.sha256(dest.read_bytes()).hexdigest() == sha, 'Asset content conflict'
        else:
            shutil.copyfile(source, dest)
        with Image.open(dest) as im: width, height = im.size
        ko, en = g.NAMES[flavour]
        images.append(dict(id=dest.stem, group='dipping-100ml', flavour=flavour,
            format='100ml', src='/' + str(dest.relative_to(ROOT)), width=width, height=height,
            source_sha256=sha, sha256=sha, source_members=[name],
            label=web.pair(ko + ' 디핑소스 · 100ml · 2026.11.26 패키지',
                en + ' Dipping Sauce · 100 ml · 2026-11-26 packaging')))
        audit.append(dict(source_path=str(source), sha256=sha, bytes=len(data), dimensions=[width, height]))
    (REVIEW / 'source-files.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    old = json.loads((ROOT / 'content/product-image-refresh-20261125.json').read_text())
    old.update(updated_at='2026-11-26', unique_image_count=69, additional_image_count=2, source_image_count=75)
    old['assets'].extend(images)
    (ROOT / 'content/product-image-refresh-20261126.json').write_text(json.dumps(old, ensure_ascii=False, indent=2) + '\n')
    return images


def update_website(images):
    path = ROOT / 'content/catalog.json'; catalog = json.loads(path.read_text())
    substitutions = {}
    for image in images:
        p = next(p for p in catalog['products'] if p['id'] == image['flavour'])
        previous = next(a for a in p['images'] if a['group'] == 'gat-original')
        substitutions[previous['src']] = image
        current = {k: image[k] for k in ['src', 'label', 'width', 'height', 'group', 'format', 'source_sha256']}
        p['images'] = [a for a in p['images'] if a['src'] != image['src']]
        p['images'].insert(0, current)
        previous['label'] = web.pair(g.NAMES[image['flavour']][0] + ' · 이전 100ml 패키지',
            g.NAMES[image['flavour']][1] + ' · Previous 100 ml packaging')
    known = {a['src'] for a in catalog['packaging_images']}
    catalog['packaging_images'].extend([{k: v for k, v in a.items() if k != 'sha256'} for a in images if a['src'] not in known])
    catalog['updated_at'] = '2026-11-26'
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    for path in ROOT.rglob('*.html'):
        if path == ROOT / 'products/packaging/index.html': continue
        source = path.read_text()
        if not any(old in source for old in substitutions): continue
        tree = html.document_fromstring(source)
        for node in tree.xpath('//img[@src]'):
            image = substitutions.get(node.get('src'))
            if image:
                node.attrib.update(dict(src=image['src'], width=str(image['width']), height=str(image['height']),
                    alt=image['label']['en'] + ' · ' + image['label']['ko']))
        for node in tree.xpath('//script[@type="application/ld+json"]'):
            text = node.text or ''
            for old, image in substitutions.items(): text = text.replace(old, image['src'])
            node.text = text
        path.write_text('<!DOCTYPE html>\n' + html.tostring(tree, encoding='unicode', method='html'))
    path = ROOT / 'products/packaging/index.html'; tree = html.parse(str(path))
    gallery = web.gallery(images, web.pair(HEADINGS['ko'], HEADINGS['en']))
    section = html.Element('section', id='dipping-100ml-20261126', **{'class': 'sec-tight'})
    wrapper = etree.SubElement(section, 'div', {'class': 'wrap'}); wrapper.append(gallery)
    tree.xpath('//main')[0].insert(1, section)
    for figure in tree.xpath('//figure'):
        pictures = figure.xpath('./img'); captions = figure.xpath('./figcaption')
        if pictures and pictures[0].get('src') in substitutions and captions:
            flavour = substitutions[pictures[0].get('src')]['flavour']
            captions[0].clear(); web.bilingual(captions[0], 'span', web.pair(
                g.NAMES[flavour][0] + ' · 이전 100ml 패키지', g.NAMES[flavour][1] + ' · Previous 100 ml packaging'))
    path.write_text(html.tostring(tree, encoding='unicode', method='html', doctype='<!DOCTYPE html>'))


def finalise_product(doc, title):
    for i, page in enumerate(doc):
        g.redact_text(page, (0, 786, g.W, g.H))
        page.draw_rect(g.fitz.Rect(0, 786, g.W, g.H), fill=(1, 1, 1), color=None)
        page.draw_line(g.fitz.Point(48, 788), g.fitz.Point(547, 788), color=(.88, .88, .85), width=.5)
        g.textbox(page, (48, 800, 420, 820), 'SEOULCOOK ARTISAN · seoulcook.com · 2026.11.26', 'en', 7, color='#77776f')
        g.textbox(page, (471, 800, 547, 820), f'{i + 1:02} / {len(doc):02}', 'en', 7, color='#77776f', align='right')
    doc.set_metadata(dict(title=title, author='SeoulCook Artisan', subject='2026-11-26 dipping sauce packaging update'))
    doc.subset_fonts()


def update_catalogues(images):
    path = g.OUT / ('manifest-' + BASE + '.json'); manifest = json.loads(path.read_text()); records = []
    print_helpers.REV = REV
    for lang in g.LANGS:
        old = {r['id']: r for r in manifest['documents'] if r['language'] == lang}
        product = g.fitz.open(ROOT / old['products']['url'].lstrip('/'))
        for image, page_index in [(images[0], 6), (images[1], 5)]:
            p = product[page_index]
            candidates = [im for im in p.get_image_info() if im['height'] > im['width'] > 500 and im['bbox'][1] > 400]
            assert len(candidates) == 1, (lang, page_index, candidates)
            box = g.fitz.Rect(candidates[0]['bbox']); box.y0 -= 4; box.y1 += 4
            p.draw_rect(box, color=None, fill=(1, 1, 1)); g.place_image(p, box, image)
        extra = g.gallery_page(lang, HEADINGS[lang], images, subtitle=g.I18N[lang]['available'] + ' · 100 ml')
        product.insert_pdf(extra); extra.close()
        finalise_product(product, old['products']['title'])
        print_urls = [print_helpers.svg_page(page, f'products-{lang}-{i + 1:02}') for i, page in enumerate(product)]
        company_record = deepcopy(old['company']); records.append(company_record)
        company = g.fitz.open(ROOT / company_record['url'].lstrip('/'))
        complete = g.fitz.open(); complete.insert_pdf(company); complete.insert_pdf(product); company.close()
        for ident, doc in [('products', product), ('complete', complete)]:
            record = deepcopy(old[ident]); filename = record['filename'].replace(BASE, REV)
            target = g.OUT / filename
            assert not target.exists(), 'Dated revision already exists: ' + filename
            doc.save(target, garbage=4, deflate=True)
            assert target.stat().st_size < 25 * 1024 * 1024, filename
            urls = print_urls if ident == 'products' else company_record['print_pages'] + print_urls
            record.update(url='/assets/catalogues/' + filename, filename=filename, pages=len(doc),
                bytes=target.stat().st_size, sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                print_pages=urls, updated_at='2026-11-26', revision=REV)
            records.append(record); doc.close()
        print(lang, 'updated product / complete PDF; company profile retained', flush=True)
    records.sort(key=lambda r: (g.LANGS.index(r['language']), ['company', 'products', 'complete'].index(r['id'])))
    manifest.update(documents=records, revision=REV, updated_at='2026-11-26',
        packaging_manifest='content/product-image-refresh-20261126.json')
    manifest['image_refresh'].update(unique_source_images=69, source_image_records=75)
    (g.OUT / ('manifest-' + REV + '.json')).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    for name in ['catalogues', 'catalogue-print']:
        src = ROOT / 'assets/js' / (name + '-' + BASE + '.js')
        dest = ROOT / 'assets/js' / (name + '-' + REV + '.js')
        dest.write_text(src.read_text().replace('manifest-' + BASE + '.json', 'manifest-' + REV + '.json'))
    for path in (ROOT / 'catalogues').rglob('*.html'):
        text = path.read_text().replace('catalogues-' + BASE + '.js', 'catalogues-' + REV + '.js').replace('catalogue-print-' + BASE + '.js', 'catalogue-print-' + REV + '.js')
        # Company profile links intentionally retain the unchanged verified file.
        for lang in g.LANGS:
            for prefix in ['product-catalogue', 'company-product-catalogue']:
                text = text.replace(f'seoulcook-{prefix}-{lang}-{BASE}.pdf', f'seoulcook-{prefix}-{lang}-{REV}.pdf')
        path.write_text(text)


if __name__ == '__main__':
    REVIEW.mkdir(parents=True, exist_ok=True)
    assets = prepare_assets(); update_website(assets); update_catalogues(assets)
    (REVIEW / 'build.json').write_text(json.dumps(dict(new_images=assets, products_unchanged=19,
        revised_pdfs=18, retained_company_profiles=9, original_images_preserved=True), ensure_ascii=False, indent=2) + '\n')
