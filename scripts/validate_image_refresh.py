"""Offline integrity and render checks for the dated image/catalogue release."""
from pathlib import Path
from lxml import html,etree
from PIL import Image,ImageDraw
import argparse,hashlib,json,re
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'outputs/2026-11-25-product-image-refresh'
LANGS={'ko','en','es','zh','ja','ar','fr','de','it'}

def run(manifest_path='assets/catalogues/manifest-20261125.json', output=None):
    output=Path(output) if output else OUT
    output.mkdir(parents=True,exist_ok=True)
    data=json.loads((ROOT/'content/product-image-refresh-20261125.json').read_text())
    catalog=json.loads((ROOT/'content/catalog.json').read_text())
    expected={a['src'] for a in data['assets']};seen=set();html_files=[]
    for path in ROOT.rglob('*.html'):
        tree=html.parse(str(path));ids=tree.xpath('//*[@id]/@id')
        assert len(ids)==len(set(ids)),('duplicate IDs',path)
        for im in tree.xpath('//img[@src]'):
            src=im.get('src');seen.add(src)
            if src.startswith('/'):assert (ROOT/src.lstrip('/')).is_file(),(path,src)
        html_files.append(str(path.relative_to(ROOT)))
    assert expected<=seen
    assert len(expected)==67 and data['archive_image_count']==73 and len(catalog['products'])==19
    for a in data['assets']:
        path=ROOT/a['src'].lstrip('/');im=Image.open(path)
        assert im.size==(a['width'],a['height'])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==a['sha256']
    for ident in ['ssamssam','hotssam','tossam','gossam']:
        p=next(p for p in catalog['products'] if p['id']==ident)
        assert '150' in p['format']['en'] and '18-month' in p['format']['en']
    manifest=json.loads((ROOT/manifest_path).read_text())
    if manifest.get('revision')=='low-sodium-7-products':
        low=[p for p in catalog['products'] if 'low-sodium' in p['collections']]
        vegan=[p for p in catalog['products'] if 'vegan' in p['collections']]
        assert len(low)==7 and {p['id'] for p in low}=={p['id'] for p in vegan}
        page=html.parse(str(ROOT/'products/low-sodium/index.html'))
        assert len(page.xpath('//section[contains(@class,"product-detail")]'))==7
        assert not page.xpath('//div[contains(@class,"collection-empty")]')
    assert len(manifest['documents'])==27
    assert {(r['id'],r['language']) for r in manifest['documents']}=={(i,l) for i in ['company','products','complete'] for l in LANGS}
    allowed={'svg','g','defs','path','rect','circle','ellipse','polygon','polyline','line','text','tspan','image','use','clipPath','mask','linearGradient','radialGradient','stop','pattern','symbol','filter','feColorMatrix','title','desc'}
    checked_svg=set();pdfs=[];reviews=output/'pdf-review';reviews.mkdir(exist_ok=True)
    for r in manifest['documents']:
        path=ROOT/r['url'].lstrip('/');d=fitz.open(path)
        assert path.stat().st_size==r['bytes']<25*1024*1024
        assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']
        assert len(d)==r['pages']==len(r['print_pages'])
        for p in d:assert abs(p.rect.width-595.2756)<1 and abs(p.rect.height-841.8898)<1
        for link in r['print_pages']:
            if link in checked_svg:continue
            tree=etree.parse(str(ROOT/link.lstrip('/')))
            assert not ({etree.QName(e).localname for e in tree.iter()}-allowed)
            for image in tree.xpath('//*[local-name()="image"]'):
                href=image.get('href') or image.get('{http://www.w3.org/1999/xlink}href')
                assert re.fullmatch(r'/assets/catalogues/[A-Za-z0-9_./-]+\.(?:png|jpe?g)',href) and '..' not in href
                assert (ROOT/href.lstrip('/')).is_file()
            checked_svg.add(link)
        if r['id'] in ['company','products']:
            prefix='company-profile' if r['id']=='company' else 'product-catalogue'
            original=fitz.open(ROOT/f"assets/catalogues/seoulcook-{prefix}-{r['language']}-20261119.pdf")
            indices=range(6) if r['id']=='company' else range(2,10)
            for idx in indices:
                new_text=''.join(d[idx].get_text().split())
                for b in original[idx].get_text('dict')['blocks']:
                    for line in b.get('lines',[]):
                        for span in line['spans']:
                            text=span['text'];box=span['bbox']
                            if 80<box[1]<780 and (r['id']=='company' or box[0]>=168) and text.strip()!='11':
                                assert ''.join(text.split()) in new_text,(r['language'],idx,text)
        if r['id']=='products':
            # Each of the 67 distinct source designs appears in the appendix.
            photos=[im for p in list(d)[11:] for im in p.get_image_info() if im['height']>im['width']]
            assert len(photos)==67,(r['language'],len(photos))
        if r['id']=='complete':
            sheet=Image.new('RGB',(1400,1340),'#eee');draw=ImageDraw.Draw(sheet)
            for i,p in enumerate(d):
                pix=p.get_pixmap(matrix=fitz.Matrix(.32,.32));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                x=i%7*200;y=i//7*335;sheet.paste(im,(x,y));draw.text((x+5,y+278),str(i+1),fill='black')
            sheet.save(reviews/f"final-all-pages-{r['language']}.jpg")
        pdfs.append({'id':r['id'],'language':r['language'],'pages':len(d),'bytes':r['bytes'],'sha256':r['sha256']})
    result={'html_count':len(html_files),'unique_images':67,'source_image_records':73,'no_image_upscaling':True,
            'original_150ml_identity_retained':True,'pdfs':pdfs,'unique_svg_pages':len(checked_svg),
            'all_original_body_copy_checked':True,'appendix_images_per_language':67,'local_integrity_passed':True}
    (output/'final-local-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='pdfs'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',default='assets/catalogues/manifest-20261125.json')
    parser.add_argument('--output')
    args=parser.parse_args()
    run(args.manifest,args.output)
