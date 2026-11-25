"""Publish the brand-confirmed shared Low Sodium / Vegan product assignment.

Preserves the 20261125 release. Reuses existing photographs and unchanged
vector pages; only revised PDFs and three print pages per language are added.
"""
from copy import deepcopy
from pathlib import Path
import base64, hashlib, io, json, re
from lxml import html, etree
from PIL import Image
import refresh_catalogues as g
import refresh_product_images as web

ROOT = g.ROOT
OUT = g.OUT
REV = '20261125-low-sodium'
REVIEW = ROOT.parent / 'outputs/2026-11-25-low-sodium'
DESCRIPTION = web.pair(
    '저당비건 7종을 저염 컬렉션에서도 만나보세요. 100ml 보틀과 식당·업소용 2kg·20kg으로 소개합니다.',
    'Explore the seven Low Sugar Vegan products in our Low Sodium Collection, in 100 ml bottles and 2 kg / 20 kg foodservice formats.')
TITLES = {
    'ko': '저염·비건 컬렉션', 'en': 'Low Sodium & Vegan Collections',
    'es': 'Colecciones baja en sodio y vegana', 'zh': '低钠与纯素系列',
    'ja': '低ナトリウム・ヴィーガンコレクション', 'ar': 'المجموعتان منخفضة الصوديوم والنباتية',
    'fr': 'Collections à teneur réduite en sodium et végane',
    'de': 'Natriumarme und vegane Kollektionen', 'it': 'Collezioni a basso contenuto di sodio e vegana',
}


def write_html(path, tree):
    path.write_text(html.tostring(tree, encoding='unicode', method='html', doctype='<!DOCTYPE html>'))


def update_website():
    path = ROOT / 'content/catalog.json'
    catalog = json.loads(path.read_text())
    collection = next(c for c in catalog['collections'] if c['id'] == 'low-sodium')
    collection.update(description=DESCRIPTION, status=web.pair('판매 중', 'Available'))
    products = [p for p in catalog['products'] if p['id'].startswith('low-sugar-vegan-')]
    assert len(products) == 7
    for p in products:
        if 'low-sodium' not in p['collections']:
            p['collections'].append('low-sodium')
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    path = ROOT / 'products/low-sodium/index.html'
    tree = html.parse(str(path))
    for lang in ['ko', 'en']:
        tree.xpath('//body')[0].set('data-desc-' + lang, DESCRIPTION[lang])
        tree.xpath('//main//p[contains(@class,"lead")]/*[@data-' + lang + ']')[0].text = DESCRIPTION[lang]
        tree.xpath('//main//p[contains(@class,"collection-status")]/*[@data-' + lang + ']')[0].text = collection['status'][lang]
    for m in tree.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):
        m.set('content', DESCRIPTION['ko'])
    for old in tree.xpath('//main/*[position()>1]'):
        old.getparent().remove(old)
    for product in products:
        tree.xpath('//main')[0].append(web.make_product(product, product['images']))
    tree.xpath('//head')[0].append(html.Element('link', rel='stylesheet', href='/assets/css/product-images-20261125.css'))
    ld = tree.xpath('//script[@type="application/ld+json"]')[0]
    schema = json.loads(ld.text)
    schema['mainEntity']['itemListElement'] = [
        {'@type': 'ListItem', 'position': i + 1, 'url': 'https://seoulcook.com/products/low-sodium/#' + p['id'], 'name': p['name']['en']}
        for i, p in enumerate(products)]
    ld.text = '\n' + json.dumps(schema, ensure_ascii=False, indent=2) + '\n'
    write_html(path, tree)
    for name in ['index.html', 'products/index.html']:
        path = ROOT / name
        tree = html.parse(str(path))
        cards = tree.xpath('//a[contains(concat(" ",@class," ")," collection-card ")]')
        low = next(c for c in cards if c.get('href') == '/products/low-sodium/')
        vegan = next(c for c in cards if c.get('href') == '/products/vegan/')
        low.replace(low[0], deepcopy(vegan[0]))
        copy = low.xpath('./div[contains(@class,"collection-card-copy")]')[0]
        paragraph = copy.xpath('./p')[0]; paragraph.clear(); web.bilingual(paragraph, 'span', DESCRIPTION)
        count = copy.xpath('./span[contains(@class,"collection-count")]')[0]
        count.clear(); count.set('class', 'collection-count'); web.bilingual(count, 'span', web.pair('7종 · 판매 중', '7 products · Available'))
        if name == 'products/index.html':
            ko = '서울쿡의 일곱 가지 컬렉션. 쌈쌈·갓소스·핫김치와 저염·비건 7종, 식당·업소용 대용량 소스를 만나보세요.'
            en = 'Explore seven SeoulCook collections, including SsamSsam, Gat Sauce, Hot Kimchi, seven shared Low Sodium and Vegan products, and bulk sauces for foodservice.'
            for lang, text in [('ko', ko), ('en', en)]:
                tree.xpath('//body')[0].set('data-desc-' + lang, text)
                tree.xpath('//main//p[contains(@class,"lead")]/*[@data-' + lang + ']')[0].text = text
            for m in tree.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):
                m.set('content', ko)
        write_html(path, tree)
    return products


def footer(page, index, total):
    page.draw_line(g.fitz.Point(48, 788), g.fitz.Point(547, 788), color=(.88, .88, .85), width=.5)
    g.textbox(page, (48, 800, 420, 820), 'SEOULCOOK ARTISAN · seoulcook.com · 2026.11.25', 'en', 7, color='#77776f')
    g.textbox(page, (471, 800, 547, 820), f'{index + 1:02} / {total:02}', 'en', 7, color='#77776f', align='right')


def svg_page(page, name):
    tree = etree.fromstring(page.get_svg_image(text_as_path=True).encode())
    for image in tree.xpath('//*[local-name()="image"]'):
        key = '{http://www.w3.org/1999/xlink}href' if image.get('{http://www.w3.org/1999/xlink}href') else 'href'
        value = image.get(key, '')
        if value.startswith('data:image/'):
            kind = value.split(';', 1)[0].split('/')[-1]
            ext = 'jpg' if kind in ['jpeg', 'jpg'] else 'png'
            data = base64.b64decode(value.split(',', 1)[1])
            im = Image.open(io.BytesIO(data))
            opaque = 'A' not in im.getbands() or im.getchannel('A').getextrema() == (255, 255)
            if ext == 'png' and opaque and min(im.size) > 200:
                buf = io.BytesIO(); im.convert('RGB').save(buf, format='JPEG', quality=92, subsampling=0, optimize=True)
                data = buf.getvalue(); ext = 'jpg'
            target = OUT / 'print-20261125/images' / (hashlib.sha256(data).hexdigest()[:24] + '.' + ext)
            if not target.exists():
                target = OUT / ('print-' + REV) / 'images' / target.name
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            image.set(key, '/' + str(target.relative_to(ROOT)))
    target = OUT / ('print-' + REV) / (name + '.svg')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(etree.tostring(tree, xml_declaration=True, encoding='utf-8'))
    return '/' + str(target.relative_to(ROOT))


def update_documents():
    manifest = json.loads((OUT / 'manifest-20261125.json').read_text())
    records = []
    for lang in g.LANGS:
        original = {r['id']: r for r in manifest['documents'] if r['language'] == lang}
        company = g.fitz.open(ROOT / original['company']['url'].lstrip('/'))
        product = g.fitz.open(ROOT / original['products']['url'].lstrip('/'))
        pages = {k: list(original[k]['print_pages']) for k in ['company', 'products']}
        replacements = [(company, 'company', 6, g.gallery_page(lang, TITLES[lang],
            [g.LOOKUP[('low-sugar-vegan-100ml', f)] for f in list(g.NAMES)[:7]],
            subtitle='100 ml · 2 kg · 20 kg · 7 / ' + g.I18N[lang]['available']))]
        old_future = g.I18N[lang]['future']
        g.I18N[lang]['future'] = '100 ml / 2 kg / 20 kg · 7'
        replacements.extend([(product, 'products', 1, g.overview(lang)), (product, 'products', 10, g.format_overview(lang))])
        g.I18N[lang]['future'] = old_future
        for doc, ident, index, replacement in replacements:
            footer(replacement[0], index, len(doc))
            pages[ident][index] = svg_page(replacement[0], f'{ident}-{lang}-{index + 1:02}')
            g.replace_page(doc, index, replacement)
        combined = g.fitz.open(); combined.insert_pdf(company); combined.insert_pdf(product)
        pages['complete'] = pages['company'] + pages['products']
        for ident, doc in [('company', company), ('products', product), ('complete', combined)]:
            record = deepcopy(original[ident])
            filename = record['filename'].replace('20261125.pdf', REV + '.pdf')
            target = OUT / filename
            assert not target.exists(), 'Revision already exists: ' + filename
            doc.subset_fonts(); doc.save(target, garbage=4, deflate=True)
            assert target.stat().st_size < 25 * 1024 * 1024, filename
            record.update(url='/assets/catalogues/' + filename, filename=filename,
                bytes=target.stat().st_size, sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                print_pages=pages[ident], revision='low-sodium-7-products')
            records.append(record); doc.close()
        print(lang, '3 PDFs / 3 revised print pages', flush=True)
    manifest.update(documents=records, revision='low-sodium-7-products',
        collection_update={'low-sodium': {'product_count': 7, 'shared_with': 'vegan', 'basis': 'brand-confirmed 2026-11-25'}})
    (OUT / ('manifest-' + REV + '.json')).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    for name in ['catalogues', 'catalogue-print']:
        source = ROOT / 'assets/js' / (name + '-20261125.js')
        (ROOT / 'assets/js' / (name + '-' + REV + '.js')).write_text(source.read_text().replace('manifest-20261125.json', 'manifest-' + REV + '.json'))
    for path in (ROOT / 'catalogues').rglob('*.html'):
        text = path.read_text().replace('catalogues-20261125.js', 'catalogues-' + REV + '.js').replace('catalogue-print-20261125.js', 'catalogue-print-' + REV + '.js')
        text = re.sub(r'(seoulcook-[a-z-]+-(?:ko|en|es|zh|ja|ar|fr|de|it)-)20261125(\.pdf)', r'\g<1>' + REV + r'\2', text)
        path.write_text(text)
    return records


if __name__ == '__main__':
    REVIEW.mkdir(parents=True, exist_ok=True)
    products = update_website()
    records = update_documents()
    (REVIEW / 'build.json').write_text(json.dumps({'product_ids': [p['id'] for p in products],
        'unique_product_count_unchanged': 19, 'pdf_count': len(records), 'languages': g.LANGS,
        'basis': 'User confirmed on 2026-11-25 that the seven Low Sugar Vegan products also belong to Low Sodium.',
        'nutrition_values_invented': False, 'previous_release_preserved': True}, ensure_ascii=False, indent=2) + '\n')
