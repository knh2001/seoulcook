"""Publish supplied packaging images without conflating recipes, sizes or labels.

Usage: python refresh_product_images.py INPUT_MANIFEST
Original ZIPs and existing dated assets are preserved. No certification or
nutritional values are inferred from package artwork.
"""
from pathlib import Path
from collections import defaultdict
from copy import deepcopy
from PIL import Image
from lxml import html, etree
import argparse, hashlib, json, re

DATE = '20261125'
ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    'sesame-ssam': ('참깨쌈', 'Sesame Ssam'), 'smoky-ssam': ('스모키쌈', 'Smoky Ssam'),
    'hot-tteokbokki': ('핫떡볶이', 'Hot Tteokbokki'), 'hot-bulgogi': ('핫불고기', 'Hot Bulgogi'),
    'garlic-ssam': ('갈릭쌈', 'Garlic Ssam'), 'hot-kimchi': ('핫김치', 'Hot Kimchi'),
    'gossam': ('고쌈', 'GoSsam'), 'ssamssam': ('쌈쌈', 'SsamSsam'),
    'hotssam': ('핫쌈', 'HotSsam'), 'tossam': ('토쌈', 'ToSsam'),
}
ORDER = list(NAMES)[:7]
GROUPS = {
    'gat-original': ('갓소스 · 기본 패키지', 'Gat Sauce · Original packaging', '100ml'),
    'gat-vegan': ('갓소스 · 비건·글루텐프리 표기 패키지', 'Gat Sauce · Vegan / gluten-free label design', '100ml'),
    'gat-halal': ('갓소스 · 할랄·글루텐프리 표기 패키지', 'Gat Sauce · Halal / gluten-free label design', '100ml'),
    'bottle-original': ('70ml · 기본 패키지', '70 ml · Original packaging', '70ml'),
    'bottle-halal': ('70ml · 할랄·글루텐프리 표기 패키지', '70 ml · Halal / gluten-free label design', '70ml'),
    'gat-2kg': ('갓소스 · 업소용 2kg', 'Gat Sauce · Foodservice 2 kg', '2kg'),
    'gat-20kg': ('갓소스 · 식자재용 20kg', 'Gat Sauce · Foodservice 20 kg', '20kg'),
    'low-sugar-vegan-100ml': ('저당비건 · 100ml 패키지', 'Low Sugar Vegan · 100 ml packaging', '100ml'),
    'low-sugar-vegan-2kg': ('저당비건 · 업소용 2kg', 'Low Sugar Vegan · Foodservice 2 kg', '2kg'),
    'low-sugar-vegan-20kg': ('저당비건 · 식자재용 20kg', 'Low Sugar Vegan · Foodservice 20 kg', '20kg'),
    'legacy': ('이전 패키지 디자인 · 100ml', 'Previous packaging design · 100 ml', '100ml'),
}


def pair(ko, en):
    return {'ko': ko, 'en': en}


def flavour(member):
    stem = Path(member).stem
    if 'KakaoTalk_20261113_160319968' in stem:
        return {'KakaoTalk_20261113_160319968': 'hotssam', 'KakaoTalk_20261113_160319968_01': 'gossam',
                'KakaoTalk_20261113_160319968_02': 'ssamssam', 'KakaoTalk_20261113_160319968_03': 'tossam'}[stem]
    if 'KakaoTalk_20261113_172035661' in stem:
        return {'KakaoTalk_20261113_172035661': 'garlic-ssam', 'KakaoTalk_20261113_172035661_01': 'hot-kimchi',
                'KakaoTalk_20261113_172035661_02': 'hot-bulgogi', 'KakaoTalk_20261113_172035661_03': 'hot-tteokbokki',
                'KakaoTalk_20261113_172035661_04': 'smoky-ssam', 'KakaoTalk_20261113_172035661_05': 'sesame-ssam'}[stem]
    for word, ident in [('핫떡볶이', 'hot-tteokbokki'), ('핫김치', 'hot-kimchi'), ('핫불고기', 'hot-bulgogi'),
                        ('갈릭쌈', 'garlic-ssam'), ('스모키쌈', 'smoky-ssam'), ('참깨쌈', 'sesame-ssam'),
                        ('고쌈', 'gossam'), ('토쌈', 'tossam'), ('핫쌈', 'hotssam'), ('쌈쌈', 'ssamssam')]:
        if word in stem:
            return ident
    raise ValueError('Unrecognised product: ' + member)


def group(member):
    if member.startswith('저당비건'):
        return 'low-sugar-vegan-' + ('20kg' if '20kg' in member else '2kg' if '2kg' in member else '100ml')
    if member.startswith('70ml/'):
        return 'bottle-halal' if '할랄' in member else 'bottle-original'
    if '이전 디자인/' in member:
        return 'legacy'
    for word, ident in [('20kg', 'gat-20kg'), ('2kg', 'gat-2kg'), ('비건', 'gat-vegan'), ('할랄', 'gat-halal')]:
        if word in member:
            return ident
    return 'gat-original'


def read_assets(manifest):
    raw = json.loads(Path(manifest).read_text())
    by_hash = defaultdict(list)
    for record in raw:
        assert hashlib.sha256(Path(record['path']).read_bytes()).hexdigest() == record['sha256']
        by_hash[record['sha256']].append(record)
    assets = []
    for sha, aliases in by_hash.items():
        record = sorted(aliases, key=lambda r: '이전 디자인/' in r['member'])[0]
        g, f = group(record['member']), flavour(record['member'])
        dest = ROOT / 'assets' / 'img' / ('products-' + DATE) / f'{g}-{f}-{sha[:10]}.jpg'
        dest.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(record['path']).convert('RGB')
        # Native source dimensions are retained; this is encoding, not upscaling.
        im.save(dest, quality=95, subsampling=0, optimize=True, progressive=True)
        ko, en, size = GROUPS[g]
        assets.append({'id': dest.stem, 'group': g, 'flavour': f, 'format': size,
                       'src': '/' + str(dest.relative_to(ROOT)), 'width': im.width, 'height': im.height,
                       'source_sha256': sha, 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                       'source_members': [r['member'] for r in aliases],
                       'label': pair(f'{NAMES[f][0]} · {ko}', f'{NAMES[f][1]} · {en}')})
    return assets, raw


def image_el(asset):
    return html.Element('img', src=asset['src'], alt=asset['label']['en'] + ' · ' + asset['label']['ko'],
                        width=str(asset['width']), height=str(asset['height']), loading='lazy', decoding='async')


def bilingual(parent, tag, data, **attrs):
    el = etree.SubElement(parent, tag, attrs)
    for lang in ['ko', 'en']:
        span = etree.SubElement(el, 'span', {'data-' + lang: ''}); span.text = data[lang]
    return el


def gallery(assets, title=None):
    box = html.Element('div', {'class': 'package-designs image-refresh-gallery'})
    if title:
        bilingual(box, 'h3', title)
    grid = etree.SubElement(box, 'div', {'class': 'product-design-grid image-variant-grid'})
    for asset in assets:
        fig = etree.SubElement(grid, 'figure'); fig.append(image_el(asset))
        bilingual(fig, 'figcaption', asset['label'])
    return box


def make_product(product, assets):
    section = html.Element('section', id=product['id'], **{'class': 'product-detail'})
    wrap = etree.SubElement(section, 'div', {'class': 'wrap'})
    split = etree.SubElement(wrap, 'div', {'class': 'split'})
    art = etree.SubElement(split, 'div', {'class': 'split-art image-refresh-art'})
    art.append(image_el(assets[0]))
    copy = etree.SubElement(split, 'div')
    bilingual(copy, 'p', product['status'], **{'class': 'product-status is-available'})
    bilingual(copy, 'h2', product['name'])
    bilingual(copy, 'p', product['kicker'], **{'class': 'lead'})
    bilingual(copy, 'p', product['description'])
    bilingual(copy, 'p', product['format'], **{'class': 'collection-note'})
    bilingual(copy, 'p', product['pairing'], **{'class': 'collection-note'})
    link = etree.SubElement(copy, 'a', {'href': '/contact/', 'class': 'btn btn-o'})
    bilingual(link, 'span', pair('제품·구매 문의', 'Product & sales enquiries'))
    if len(assets) > 1:
        wrap.append(gallery(assets[1:], pair('용량별·표기별 패키지', 'Packaging by size and label')))
    return section


def replace_main(tree, products, assets_for):
    main = tree.xpath('//main')[0]
    for child in list(main)[1:]:
        main.remove(child)
    for product in products:
        main.append(make_product(product, assets_for(product)))


def update_web(assets):
    catalog_path = ROOT / 'content/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    products = {p['id']: p for p in catalog['products']}
    lookup = {(a['group'], a['flavour']): a for a in assets if a['group'] != 'legacy'}
    gat_go = deepcopy(products['gossam']); gat_go.update({'id': 'gossam-gat', 'collections': ['gat-sauce'],
        'format': pair('100ml 스퀴즈 보틀 · 판매 중', '100 ml squeeze bottle · Available'), 'reference_volume_ml': 100})
    gat_go['name'] = pair('고쌈 · 갓소스', 'GoSsam · Gat Sauce')
    products[gat_go['id']] = gat_go
    for ident in ORDER:
        source = products['gossam-gat' if ident == 'gossam' else ident]
        p = deepcopy(source); p['id'] = 'low-sugar-vegan-' + ident
        p['name'] = pair(NAMES[ident][0] + ' · 저당비건', NAMES[ident][1] + ' · Low Sugar Vegan')
        p['collections'] = ['vegan']; p.pop('product_information', None)
        p['kicker'] = pair('저당비건 패키지 · ' + NAMES[ident][0], 'Low Sugar Vegan packaging · ' + NAMES[ident][1])
        p['description'] = pair('저당비건 컬렉션의 ' + NAMES[ident][0] + ' 패키지입니다. 100ml 보틀과 식당·업소용 2kg·20kg 포맷으로 소개합니다.',
                                NAMES[ident][1] + ' in the Low Sugar Vegan packaging range, presented in a 100 ml bottle and 2 kg / 20 kg foodservice formats.')
        p['format'] = pair('100ml 보틀 · 2kg 파우치 · 20kg 용기', '100 ml bottle · 2 kg pouch · 20 kg container')
        p['status'] = pair('판매 중', 'Available'); p['sales_status'] = 'available'
        products[p['id']] = p
    for p in products.values():
        ident = p['id']
        if ident.startswith('low-sugar-vegan-'):
            f = ident.removeprefix('low-sugar-vegan-')
            choices = [lookup[(g, f)] for g in ['low-sugar-vegan-100ml', 'low-sugar-vegan-2kg', 'low-sugar-vegan-20kg']]
        elif ident in ORDER[:6] or ident == 'gossam-gat':
            f = 'gossam' if ident == 'gossam-gat' else ident
            choices = [a for a in assets if a['flavour'] == f and not a['group'].startswith('low-sugar') and a['group'] != 'legacy']
            choices.sort(key=lambda a: list(GROUPS).index(a['group']))
        else:
            continue  # Original 150 ml line and the distinct 130 ml SKU remain distinct.
        p['images'] = [{k: a[k] for k in ['src', 'label', 'width', 'height', 'group', 'format', 'source_sha256']} for a in choices]
    for c in catalog['collections']:
        if c['id'] == 'gat-sauce':
            c['description'] = pair('참깨·스모키·떡볶이·불고기·마늘·김치·고수. 일곱 가지 풍미를 용량별·표기별 패키지로 만나보세요.',
                                    'Sesame, smoky, tteokbokki, bulgogi, garlic, kimchi and cilantro. Seven flavours, with packaging by size and label.')
        if c['id'] == 'vegan':
            c['description'] = pair('저당비건 패키지 7종. 100ml 보틀부터 식당·업소용 2kg·20kg까지 소개합니다.',
                                    'Seven Low Sugar Vegan packaging designs, from 100 ml bottles to 2 kg and 20 kg foodservice formats.')
            c['status'] = pair('판매 중', 'Available')
        if c['id'] == 'bulk':
            c['description'] = pair('식당 및 업소를 위한 2kg 파우치와 20kg 식자재용 소스. 갓소스와 저당비건 패키지를 확인해 보세요.',
                                    '2 kg pouches and 20 kg sauce containers for restaurants and foodservice, in Gat Sauce and Low Sugar Vegan packaging.')
    catalog['products'] = list(products.values()); catalog['updated_at'] = '2026-11-25'
    catalog['packaging_images'] = [{k: v for k, v in a.items() if k != 'sha256'} for a in assets]
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    collections = {c['id']: c for c in catalog['collections']}
    for file in ROOT.rglob('*.html'):
        if '.git' in file.parts:
            continue
        tree = html.parse(str(file)); body = tree.xpath('//body')
        if not body:
            continue
        for section in tree.xpath('//section[contains(concat(" ",normalize-space(@class)," ")," product-detail ")][@id]'):
            ident = section.get('id')
            if ident not in products or ident not in ORDER[:6]:
                continue
            p = products[ident]; image = p['images'][0]
            art = section.xpath('.//div[contains(concat(" ",@class," ")," split-art ")]')[0]
            art.clear(); art.set('class', 'split-art image-refresh-art'); art.append(image_el(image))
            for old in section.xpath('.//*[contains(concat(" ",@class," ")," package-designs ")]'):
                old.getparent().remove(old)
            section.xpath('./div')[0].append(gallery(p['images'][1:], pair('용량별·표기별 패키지', 'Packaging by size and label')))
        route = '/' + str(file.parent.relative_to(ROOT)).strip('.') + '/'
        if route == '/products/gat-sauce/':
            tree.xpath('//main')[0].append(make_product(gat_go, [lookup[('gat-original', 'gossam')], lookup[('gat-vegan', 'gossam')], lookup[('gat-halal', 'gossam')]]))
        if route == '/products/vegan/':
            replace_main(tree, [p for p in products.values() if p['collections'] == ['vegan']], lambda p: p['images'])
        if route == '/products/bulk/':
            bulk_products = []
            for ident in ORDER:
                p = deepcopy(products['gossam-gat' if ident == 'gossam' else ident]); p['id'] = 'bulk-' + ident
                p['format'] = pair('2kg 파우치 · 20kg 식자재용 용기', '2 kg pouch · 20 kg foodservice container')
                p['description'] = pair('식당·업소의 조리, 디핑과 메뉴 운영에 사용할 수 있는 ' + NAMES[ident][0] + ' 대용량 패키지입니다.',
                                        NAMES[ident][1] + ' in bulk packaging for restaurant preparation, dipping and foodservice menus.')
                p['bulk_flavour'] = ident; bulk_products.append(p)
            replace_main(tree, bulk_products, lambda p: [lookup[(g, p['bulk_flavour'])] for g in ['gat-2kg', 'gat-20kg', 'low-sugar-vegan-2kg', 'low-sugar-vegan-20kg']])
        if route.startswith('/products/') and route.count('/') == 3:
            cid = route.split('/')[2]
            if cid in ['gat-sauce', 'vegan', 'bulk']:
                c = collections[cid]
                page_body=tree.xpath('//body')[0]
                for lang in ['ko','en']:page_body.set('data-desc-'+lang,c['description'][lang])
                for meta in tree.xpath('//meta[@name="description"]|//meta[@property="og:description"]|//meta[@name="twitter:description"]'):
                    meta.set('content',c['description']['ko'])
                for e in tree.xpath('//section[contains(@class,"collection-hero")]//p[contains(@class,"lead")]'):
                    e.clear(); e.set('class', 'lead'); bilingual(e, 'span', c['description'])
                for e in tree.xpath('//section[contains(@class,"collection-hero")]//p[contains(@class,"collection-status")]'):
                    e.clear(); e.set('class', 'collection-status is-available'); bilingual(e, 'span', pair('판매 중', 'Available'))
        # Update collection thumbnails and descriptions wherever cards are reused.
        for card in tree.xpath('//a[contains(concat(" ",@class," ")," collection-card ")]'):
            cid = (card.get('href') or '').strip('/').split('/')[-1]
            if cid not in ['gat-sauce', 'vegan', 'bulk']:
                continue
            art = card.xpath('.//*[contains(concat(" ",@class," ")," collection-card-art ")]')[0]
            art.clear(); art.set('class', 'collection-card-art')
            g = {'gat-sauce': 'gat-original', 'vegan': 'low-sugar-vegan-100ml', 'bulk': 'gat-2kg'}[cid]
            for f in ['sesame-ssam', 'hot-tteokbokki', 'gossam']:
                art.append(image_el(lookup[(g, f)]))
            copy = card.xpath('.//*[contains(concat(" ",@class," ")," collection-card-copy ")]')[0]
            for el in copy.xpath('./p'):
                el.clear(); bilingual(el, 'span', collections[cid]['description'])
            for el in copy.xpath('.//*[contains(concat(" ",@class," ")," collection-count ")]'):
                el.clear(); el.set('class', 'collection-count')
                bilingual(el, 'span', pair('7종 · 판매 중' if cid != 'bulk' else '2kg · 20kg · 업소용',
                                          '7 products · Available' if cid != 'bulk' else '2 kg · 20 kg · Foodservice'))
        # Keep the original 150 ml product identity; earlier 100 ml designs are labelled separately.
        if route == '/products/ssamssam/':
            for ident in ['ssamssam', 'hotssam', 'tossam', 'gossam']:
                nodes = tree.xpath(f'//section[@id="{ident}"]/div')
                old = [a for a in assets if a['group'] == 'legacy' and a['flavour'] == ident]
                if nodes and old:
                    nodes[0].append(gallery(old, pair('이전 100ml 패키지 디자인', 'Previous 100 ml packaging designs')))
        # Fresh structured data is generated from the same catalogue, rather than old crop sheets.
        if route.startswith('/products/'):
            cid = route.strip('/').split('/')[-1]
            selected = (bulk_products if cid == 'bulk' else list(products.values()) if cid == 'products'
                        else [p for p in products.values() if cid in p['collections']])
            for node in tree.xpath('//script[@type="application/ld+json"]'):
                obj = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'url': 'https://seoulcook.com' + route,
                       'mainEntity': {'@type': 'ItemList', 'itemListElement': [
                           {'@type': 'ListItem', 'position': i+1, 'item': {'@type': 'Product', 'name': p['name']['en'],
                            'image': 'https://seoulcook.com' + p['images'][0]['src'], 'description': p['description']['en']}}
                           for i,p in enumerate(selected)]}}
                node.text = json.dumps(obj, ensure_ascii=False)
        head = tree.xpath('//head')[0]
        etree.SubElement(head, 'link', rel='stylesheet', href='/assets/css/product-images-' + DATE + '.css')
        output = html.tostring(tree, encoding='unicode', doctype='<!DOCTYPE html>')
        output = output.replace('6 Collections', '7 Collections')
        if route == '/products/':
            output = output.replace('저염·비건 컬렉션은 상품 개발 중입니다.', '저염 컬렉션은 상품 개발 중이며, 비건 컬렉션에서 저당비건 패키지를 만나보세요.')
        if route in ['/products/vegan/', '/products/bulk/']:
            output = output.replace('상품 개발 중 In development', '판매 중 Available')
        file.write_text(output)
    # All 67 unique images are reachable in a clearly labelled reference gallery too.
    gallery_page = html.parse(str(ROOT / 'products/gat-sauce/index.html'))
    main = gallery_page.xpath('//main')[0]
    for node in list(main): main.remove(node)
    hero = etree.SubElement(main, 'section', {'class': 'phero'})
    wrap = etree.SubElement(hero, 'div', {'class': 'wrap'})
    bilingual(wrap, 'h1', pair('제품·패키지 이미지', 'Product & packaging images'))
    bilingual(wrap, 'p', pair('상품·용량·라벨 표기와 이전 디자인을 구분한 이미지 모음입니다.',
                               'Images grouped by product, size, label design and previous packaging.'))
    for g in GROUPS:
        selected = sorted([a for a in assets if a['group'] == g], key=lambda a: list(NAMES).index(a['flavour']))
        if not selected: continue
        section = etree.SubElement(main, 'section', {'class': 'sec-tight', 'id': g})
        wrap = etree.SubElement(section, 'div', {'class': 'wrap'}); wrap.append(gallery(selected, pair(*GROUPS[g][:2])))
    target = ROOT / 'products/packaging/index.html'; target.parent.mkdir(exist_ok=True)
    gallery_page.xpath('//title')[0].text = '제품·패키지 이미지 | SeoulCook'
    gallery_body = gallery_page.xpath('//body')[0]
    gallery_body.set('data-title-ko', '제품·패키지 이미지 | 서울쿡')
    gallery_body.set('data-title-en', 'Product & packaging images | SeoulCook')
    gallery_body.set('data-desc-ko', '상품·용량·라벨 표기와 이전 디자인을 구분한 서울쿡 이미지 모음입니다.')
    gallery_body.set('data-desc-en', 'SeoulCook images grouped by product, size, label design and previous packaging.')
    for el in gallery_page.xpath('//link[@rel="canonical"]'): el.set('href', 'https://seoulcook.com/products/packaging/')
    for el in gallery_page.xpath('//link[@rel="alternate"]'): el.set('href', 'https://seoulcook.com/products/packaging/' + ('?lang=en' if el.get('hreflang') == 'en' else ''))
    for el in gallery_page.xpath('//script[@type="application/ld+json"]'): el.getparent().remove(el)
    target.write_text(html.tostring(gallery_page, encoding='unicode', doctype='<!DOCTYPE html>'))
    for route, groups in [('halal', ['gat-halal', 'bottle-halal']), ('vegan', ['gat-vegan'])]:
        f=ROOT/f'products/{route}/index.html'; t=html.parse(str(f)); main=t.xpath('//main')[0]
        for g in groups:
            section=etree.SubElement(main,'section',{'class':'sec-tight'}); w=etree.SubElement(section,'div',{'class':'wrap'})
            w.append(gallery([a for a in assets if a['group']==g],pair(*GROUPS[g][:2])))
        f.write_text(html.tostring(t,encoding='unicode',doctype='<!DOCTYPE html>'))
    for route in ['gat-sauce', 'vegan', 'bulk', 'ssamssam']:
        f = ROOT / f'products/{route}/index.html'; t = html.parse(str(f)); main=t.xpath('//main')[0]
        section = etree.SubElement(main, 'section', {'class': 'sec-tight'}); w=etree.SubElement(section,'div',{'class':'wrap'})
        a=etree.SubElement(w,'a',{'href':'/products/packaging/', 'class':'btn btn-o'})
        bilingual(a,'span',pair('전체 제품·패키지 이미지 보기', 'View all product & packaging images'))
        f.write_text(html.tostring(t,encoding='unicode',doctype='<!DOCTYPE html>'))
    (ROOT/'assets/css'/f'product-images-{DATE}.css').write_text('''/* Native-resolution packaging, retaining the ivory / charcoal identity. */
.image-refresh-art{min-height:400px;aspect-ratio:auto;display:flex;align-items:center;justify-content:center;padding:28px}
.image-refresh-art>img{position:static;max-height:440px;max-width:100%;height:auto;width:auto;object-fit:contain;mix-blend-mode:multiply}
.image-variant-grid{max-width:none;grid-template-columns:repeat(4,minmax(0,1fr));gap:28px}
.image-variant-grid figure{min-width:0;margin:0;display:flex;flex-direction:column;align-items:center;justify-content:flex-end}
.image-variant-grid img{width:100%;height:260px;object-fit:contain;mix-blend-mode:multiply}
.image-variant-grid figcaption{font-size:.82rem;line-height:1.6;margin-top:14px}
.image-refresh-gallery{margin-bottom:36px}
@media(max-width:900px){.image-variant-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.image-variant-grid img{height:230px}}
@media(max-width:560px){.image-variant-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.image-variant-grid img{height:210px}.image-refresh-art{min-height:340px}.image-refresh-art>img{max-height:360px}}
''')
    return catalog


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('manifest'); args=parser.parse_args()
    if (ROOT/'content'/f'product-image-refresh-{DATE}.json').exists():
        raise SystemExit('This dated refresh already exists. Preserve it and use a new revision.')
    assets, raw = read_assets(args.manifest)
    catalog = update_web(assets)
    data = {'updated_at':'2026-11-25','archive_image_count':len(raw),'unique_image_count':len(assets),
            'product_count':len(catalog['products']),'assets':assets,
            'rules':['No upscaling','150 ml original line retained','Low sugar is not low sodium','Package label variants do not establish certification']}
    (ROOT/'content'/f'product-image-refresh-{DATE}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='assets'},ensure_ascii=False,indent=2))
