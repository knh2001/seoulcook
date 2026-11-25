"""Refresh all nine-language PDFs and matching vector print pages.

Preserves the original translated company / product content and original dated
files. New imagery and size galleries are generated from the image manifest.
Requires PyMuPDF and Pillow; no remote fonts or image generation is used.
"""
from pathlib import Path
from html import escape
from PIL import Image
from collections import defaultdict
import argparse, base64, hashlib, io, json, re
import pymupdf as fitz
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]
OLD='20261119'; NEW='20261125'; W=595.2756; H=841.8898
OUT=ROOT/'assets/catalogues'
DATA=json.loads((ROOT/'content'/f'product-image-refresh-{NEW}.json').read_text())
ASSETS=DATA['assets']
LOOKUP={(a['group'],a['flavour']):a for a in ASSETS if a['group']!='legacy'}
NAMES={'sesame-ssam':('참깨쌈','Sesame Ssam'),'smoky-ssam':('스모키쌈','Smoky Ssam'),
       'hot-tteokbokki':('핫떡볶이','Hot Tteokbokki'),'hot-bulgogi':('핫불고기','Hot Bulgogi'),
       'garlic-ssam':('갈릭쌈','Garlic Ssam'),'hot-kimchi':('핫김치','Hot Kimchi'),'gossam':('고쌈','GoSsam'),
       'ssamssam':('쌈쌈','SsamSsam'),'hotssam':('핫쌈','HotSsam'),'tossam':('토쌈','ToSsam')}
ORDER=list(NAMES)

# Only short, new headings are translated here. Existing translated product
# descriptions and company narrative remain in the original vector pages.
I18N={
'ko':dict(title='제품·패키지 이미지',overview='컬렉션과 용량별 포맷',lineup='제품과 업소용 패키지',note='상품·용량·라벨 표기와 이전 디자인을 구분한 패키지 이미지입니다. 개별 상품의 상세 규격은 문의해 주세요.',collections=['쌈쌈 컬렉션','할랄 컬렉션','코셔 컬렉션','갓소스 컬렉션','저염 컬렉션','비건 컬렉션','대용량 컬렉션'],groups=['갓소스 · 기본 패키지','갓소스 · 비건·글루텐프리 표기 패키지','갓소스 · 할랄·글루텐프리 표기 패키지','70ml 보틀 · 기본 및 할랄 표기형','갓소스 · 업소용 2kg','갓소스 · 식자재용 20kg','저당비건 · 100ml','저당비건 · 업소용 2kg','저당비건 · 식자재용 20kg','이전 패키지 디자인 · 100ml'],future='상품 개발 중',formats='패키지 포맷',available='판매 중'),
'en':dict(title='Product & packaging images',overview='Collections & packaging formats',lineup='Products & foodservice packaging',note='Package images are grouped by product, size, label design and previous packaging. Contact us for the specification of each product.',collections=['SsamSsam Collection','Halal Collection','Kosher Collection','Gat Sauce Collection','Low Sodium Collection','Vegan Collection','Bulk Collection'],groups=['Gat Sauce · Original packaging','Gat Sauce · Vegan / gluten-free label design','Gat Sauce · Halal / gluten-free label design','70 ml bottles · Original & Halal label designs','Gat Sauce · Foodservice 2 kg','Gat Sauce · Foodservice 20 kg','Low Sugar Vegan · 100 ml','Low Sugar Vegan · Foodservice 2 kg','Low Sugar Vegan · Foodservice 20 kg','Previous packaging designs · 100 ml'],future='In development',formats='Packaging formats',available='Available'),
'es':dict(title='Productos y envases',overview='Colecciones y formatos de envase',lineup='Productos y formatos para hostelería',note='Imágenes agrupadas por producto, capacidad, diseño de etiqueta y envases anteriores. Consúltenos las especificaciones de cada producto.',collections=['Colección SsamSsam','Colección Halal','Colección Kosher','Colección Gat Sauce','Colección baja en sodio','Colección vegana','Colección para hostelería'],groups=['Gat Sauce · Envase original','Gat Sauce · Etiqueta vegana y sin gluten','Gat Sauce · Etiqueta halal y sin gluten','Botellas de 70 ml · Etiquetas original y halal','Gat Sauce · Formato de 2 kg','Gat Sauce · Formato de 20 kg','Low Sugar Vegan · 100 ml','Low Sugar Vegan · Formato de 2 kg','Low Sugar Vegan · Formato de 20 kg','Diseños de envase anteriores · 100 ml'],future='En desarrollo',formats='Formatos de envase',available='Disponible'),
'zh':dict(title='产品与包装图片',overview='产品系列与包装规格',lineup='产品与餐饮包装',note='包装图片按产品、容量、标签设计及旧版包装分类。各产品详细规格请咨询我们。',collections=['SsamSsam系列','清真系列','犹太洁食系列','Gat Sauce系列','低钠系列','纯素系列','餐饮大包装系列'],groups=['Gat Sauce · 基础包装','Gat Sauce · 纯素及无麸质标签设计','Gat Sauce · 清真及无麸质标签设计','70 ml瓶装 · 基础及清真标签设计','Gat Sauce · 餐饮用2 kg','Gat Sauce · 餐饮用20 kg','Low Sugar Vegan · 100 ml','Low Sugar Vegan · 餐饮用2 kg','Low Sugar Vegan · 餐饮用20 kg','旧版包装设计 · 100 ml'],future='产品开发中',formats='包装规格',available='在售'),
'ja':dict(title='製品・パッケージ画像',overview='コレクションと容量別パッケージ',lineup='製品・業務用パッケージ',note='製品、容量、ラベル表記、旧デザインを区別したパッケージ画像です。各製品の詳細仕様はお問い合わせください。',collections=['SsamSsamコレクション','ハラールコレクション','コーシャコレクション','Gat Sauceコレクション','低ナトリウムコレクション','ヴィーガンコレクション','業務用コレクション'],groups=['Gat Sauce · 基本パッケージ','Gat Sauce · ヴィーガン・グルテンフリー表記','Gat Sauce · ハラール・グルテンフリー表記','70 mlボトル · 基本・ハラール表記','Gat Sauce · 業務用2 kg','Gat Sauce · 業務用20 kg','Low Sugar Vegan · 100 ml','Low Sugar Vegan · 業務用2 kg','Low Sugar Vegan · 業務用20 kg','旧パッケージデザイン · 100 ml'],future='製品開発中',formats='パッケージ仕様',available='販売中'),
'ar':dict(title='صور المنتجات والعبوات',overview='المجموعات وأحجام العبوات',lineup='المنتجات وعبوات خدمات الطعام',note='صور العبوات مصنفة حسب المنتج والحجم وتصميم الملصق والتصاميم السابقة. تواصلوا معنا لمعرفة مواصفات كل منتج.',collections=['مجموعة SsamSsam','مجموعة الحلال','مجموعة الكوشر','مجموعة Gat Sauce','مجموعة منخفضة الصوديوم','المجموعة النباتية','مجموعة خدمات الطعام'],groups=['Gat Sauce · العبوة الأصلية','Gat Sauce · تصميم ملصق نباتي وخالٍ من الغلوتين','Gat Sauce · تصميم ملصق حلال وخالٍ من الغلوتين','زجاجات 70 مل · التصميم الأصلي وتصميم الحلال','Gat Sauce · عبوة 2 كغ لخدمات الطعام','Gat Sauce · عبوة 20 كغ لخدمات الطعام','Low Sugar Vegan · 100 مل','Low Sugar Vegan · عبوة 2 كغ','Low Sugar Vegan · عبوة 20 كغ','تصاميم العبوات السابقة · 100 مل'],future='قيد التطوير',formats='أحجام العبوات',available='متاح'),
'fr':dict(title='Produits et emballages',overview='Collections et formats de conditionnement',lineup='Produits et formats pour la restauration',note='Images classées par produit, contenance, étiquetage et anciens emballages. Contactez-nous pour les spécifications de chaque produit.',collections=['Collection SsamSsam','Collection Halal','Collection Kosher','Collection Gat Sauce','Collection à teneur réduite en sodium','Collection végane','Collection restauration'],groups=['Gat Sauce · Emballage original','Gat Sauce · Étiquette végane et sans gluten','Gat Sauce · Étiquette halal et sans gluten','Bouteilles de 70 ml · Étiquettes originale et halal','Gat Sauce · Format restauration 2 kg','Gat Sauce · Format restauration 20 kg','Low Sugar Vegan · 100 ml','Low Sugar Vegan · Format de 2 kg','Low Sugar Vegan · Format de 20 kg','Anciens emballages · 100 ml'],future='En développement',formats='Formats de conditionnement',available='Disponible'),
'de':dict(title='Produkte und Verpackungen',overview='Kollektionen und Verpackungsformate',lineup='Produkte und Gastronomieformate',note='Abbildungen nach Produkt, Größe, Etikettenvariante und früheren Designs geordnet. Fragen Sie uns nach den Spezifikationen der einzelnen Produkte.',collections=['SsamSsam-Kollektion','Halal-Kollektion','Koscher-Kollektion','Gat-Sauce-Kollektion','Natriumarme Kollektion','Vegane Kollektion','Gastronomie-Kollektion'],groups=['Gat Sauce · Originalverpackung','Gat Sauce · Veganes und glutenfreies Etikett','Gat Sauce · Halal- und glutenfreies Etikett','70-ml-Flaschen · Original- und Halal-Etikett','Gat Sauce · Gastronomieformat 2 kg','Gat Sauce · Gastronomieformat 20 kg','Low Sugar Vegan · 100 ml','Low Sugar Vegan · Gastronomieformat 2 kg','Low Sugar Vegan · Gastronomieformat 20 kg','Frühere Verpackungsdesigns · 100 ml'],future='In Entwicklung',formats='Verpackungsformate',available='Erhältlich'),
'it':dict(title='Prodotti e confezioni',overview='Collezioni e formati delle confezioni',lineup='Prodotti e formati per la ristorazione',note='Immagini suddivise per prodotto, formato, etichetta e confezioni precedenti. Contattateci per le specifiche di ciascun prodotto.',collections=['Collezione SsamSsam','Collezione Halal','Collezione Kosher','Collezione Gat Sauce','Collezione a basso contenuto di sodio','Collezione vegana','Collezione ristorazione'],groups=['Gat Sauce · Confezione originale','Gat Sauce · Etichetta vegana e senza glutine','Gat Sauce · Etichetta halal e senza glutine','Bottiglie da 70 ml · Etichette originale e halal','Gat Sauce · Formato ristorazione 2 kg','Gat Sauce · Formato ristorazione 20 kg','Low Sugar Vegan · 100 ml','Low Sugar Vegan · Formato da 2 kg','Low Sugar Vegan · Formato da 20 kg','Confezioni precedenti · 100 ml'],future='In sviluppo',formats='Formati delle confezioni',available='Disponibile'),
}
LANGS=list(I18N)
ARCHIVE=fitz.Archive(str(ROOT))
CSS='''body{font-family:sans-serif;font-size:10pt;color:#242424;line-height:1.4;margin:0;padding:0}p{margin:0}'''
# MuPDF's local fallback fonts cover CJK and Arabic; no network font loading.
CHECKS=[]
IMAGE_BYTES={}


def textbox(page,rect,text,lang='en',size=10,bold=False,color='#242424',align=None):
    rtl=lang=='ar'; align=align or ('right' if rtl else 'left')
    markup=f'<p dir="{"rtl" if rtl else "ltr"}" lang="{lang}" style="direction:{"rtl" if rtl else "ltr"};font-size:{size}pt;font-weight:{"bold" if bold else "normal"};color:{color};text-align:{align}">{escape(text)}</p>'
    spare, scale=page.insert_htmlbox(fitz.Rect(rect),markup,css=CSS,archive=ARCHIVE,scale_low=.75)
    if spare<0:raise ValueError(f'Text overflow: {lang}: {text}')
    if rtl and align=='right':
        area=fitz.Rect(rect)
        spans=[fitz.Rect(s['bbox']) for b in page.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']
               if fitz.Rect(s['bbox']).intersects(area) and s['bbox'][1]>=area.y0-3]
        if spans:
            actual=spans[0]
            for box in spans[1:]:actual|=box
            dx=area.x1-actual.x1
            if abs(dx)>.5:
                xref=page.get_contents()[-1]
                stream=page.parent.xref_stream(xref)
                page.parent.update_stream(xref,f'q 1 0 0 1 {dx:.5f} 0 cm\n'.encode()+stream+b'\nQ')
    CHECKS.append({'language':lang,'text':text,'scale':scale})


def source_img(asset):
    if asset['id'] in IMAGE_BYTES:
        return IMAGE_BYTES[asset['id']]
    im=Image.open(ROOT/asset['src'].lstrip('/')).convert('RGB');buf=io.BytesIO()
    # Keep native pixel dimensions and full chroma detail. This quality level
    # keeps the complete multilingual documents below the 25 MiB host limit.
    im.save(buf,format='JPEG',quality=88,subsampling=0,optimize=True)
    IMAGE_BYTES[asset['id']]=buf.getvalue()
    return IMAGE_BYTES[asset['id']]


def place_image(page,rect,asset):
    page.insert_image(fitz.Rect(rect),stream=source_img(asset),keep_proportion=True)


def header(page,title,lang):
    page.draw_rect(page.rect,color=None,fill=(1,1,1))
    logo=fitz.Rect(374,38,547,56) if lang=='ar' else fitz.Rect(48,38,221,56)
    page.insert_image(logo,filename=str(ROOT/'assets/img/logo-mark.png'),keep_proportion=True)
    page.draw_line(fitz.Point(48,74),fitz.Point(547,74),color=(.85,.85,.83),width=.5)
    textbox(page,(48,100,547,145),title,lang,23,True)


def new_page(title,lang):
    d=fitz.open(); p=d.new_page(width=W,height=H);header(p,title,lang);return d,p


def gallery_page(lang,title,assets,subtitle=None):
    d,p=new_page(title,lang)
    textbox(p,(48,150,547,194),subtitle or I18N[lang]['note'],lang,9,color='#60605a')
    for i,a in enumerate(assets):
        x=48+((3-i%4) if lang=='ar' else i%4)*127; y=218+(i//4)*265
        p.draw_rect(fitz.Rect(x,y,x+117,y+235),color=None,fill=(.977,.974,.962))
        place_image(p,(x+5,y+7,x+112,y+198),a)
        name=NAMES[a['flavour']][0 if lang=='ko' else 1]
        textbox(p,(x+3,y+204,x+114,y+231),name,lang,9,True,align='center')
        textbox(p,(x+3,y+233,x+114,y+254),a['format'].replace('ml',' ml').replace('kg',' kg'),'en',8,align='center',color='#60605a')
    return d


def overview(lang):
    d,p=new_page(I18N[lang]['overview'],lang)
    metrics={'ko':'19개 상품 · 7개 컬렉션','en':'19 products · 7 collections','es':'19 productos · 7 colecciones','zh':'19款产品 · 7大系列','ja':'19製品 · 7コレクション','ar':'19 منتجًا · 7 مجموعات','fr':'19 produits · 7 collections','de':'19 Produkte · 7 Kollektionen','it':'19 prodotti · 7 collezioni'}
    textbox(p,(48,151,547,185),metrics[lang],lang,18,True,color='#ba392c')
    details=['150 ml · 4','130 ml / 100 ml / 70 ml','130 ml','100 ml / 70 ml · 7',I18N[lang]['future'],
             'Low Sugar Vegan · 100 ml / 2 kg / 20 kg · 7','2 kg / 20 kg']
    for i,(name,detail) in enumerate(zip(I18N[lang]['collections'],details)):
        y=215+i*65
        p.draw_line(fitz.Point(48,y+52),fitz.Point(547,y+52),color=(.86,.86,.83),width=.5)
        name_box=(290,y,547,y+50) if lang=='ar' else (48,y,280,y+50)
        detail_box=(48,y,280,y+50) if lang=='ar' else (290,y,547,y+50)
        textbox(p,name_box,name,lang,12,True)
        textbox(p,detail_box,detail,lang,10,color='#60605a')
    return d


def format_overview(lang):
    d,p=new_page(I18N[lang]['lineup'],lang)
    textbox(p,(48,150,547,193),I18N[lang]['note'],lang,9,color='#60605a')
    samples=[LOOKUP[('gat-original','hot-kimchi')],LOOKUP[('bottle-original','hot-kimchi')],
             LOOKUP[('gat-2kg','hot-kimchi')],LOOKUP[('gat-20kg','hot-kimchi')],
             LOOKUP[('low-sugar-vegan-100ml','gossam')],LOOKUP[('low-sugar-vegan-2kg','gossam')],
             LOOKUP[('low-sugar-vegan-20kg','gossam')]]
    for i,a in enumerate(samples):
        x=48+(i%4)*127;y=215+(i//4)*235;place_image(p,(x+5,y,x+112,y+185),a)
        textbox(p,(x,y+190,x+117,y+216),a['format'].replace('ml',' ml').replace('kg',' kg'),'en',10,True,align='center')
    textbox(p,(48,724,547,765),I18N[lang]['collections'][4]+' · '+I18N[lang]['future'],lang,10,color='#60605a')
    return d


def replace_page(doc,index,replacement):
    doc.delete_page(index);doc.insert_pdf(replacement,start_at=index)
    replacement.close()


def redact_text(page, rect):
    page.add_redact_annot(fitz.Rect(rect),fill=False)
    page.apply_redactions(images=0,graphics=0,text=0)


def refresh_counts(doc,lang,company=False):
    # Original translated subtitle remains unchanged apart from its factual count.
    if not company:
        page=doc[0]
        source_manifest=json.loads((OUT/f'manifest-{OLD}.json').read_text())
        subtitle=next(r['subtitle'] for r in source_manifest['documents'] if r['id']=='products' and r['language']==lang).replace('11','19')
        for block in page.get_text('dict')['blocks']:
            text=''.join(s['text'] for line in block.get('lines',[]) for s in line['spans'])
            if '11' in text and 150<block['bbox'][1]<650:
                rect=fitz.Rect(block['bbox']);redact_text(page,rect)
                textbox(page,(48 if lang=='ar' else rect.x0,rect.y0-2,547,rect.y1+24),subtitle,lang,10)
    else:
        page=doc[4]
        for b in page.get_text('dict')['blocks']:
            for line in b.get('lines',[]):
                for s in line.get('spans',[]):
                    if s['text'].strip()=='11':
                        rect=fitz.Rect(s['bbox']);redact_text(page,rect)
                        textbox(page,(rect.x0,rect.y0-3,rect.x1+30,rect.y1+10),'19','en',s['size'],True,color='#ba392c')


def replace_main_product_photos(doc,lang):
    def rect(coords):
        x0,y0,x1,y1=coords
        return fitz.Rect(W-x1,y0,W-x0,y1) if lang=='ar' else fitz.Rect(coords)
    pairs=[['sesame-ssam','smoky-ssam'],['hot-tteokbokki','hot-bulgogi'],['garlic-ssam','hot-kimchi']]
    for pi,flavours in zip([4,5,6],pairs):
        p=doc[pi]
        # Cover only the former cropped image column, not translated copy.
        column=rect((0,148,166,770))
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    if fitz.Rect(span['bbox']).intersects(column):
                        assert re.fullmatch(r'[\s\dml]+',span['text']),('Photo column overlaps source copy',lang,span['text'])
        p.draw_rect(column,fill=(1,1,1),color=None,overlay=True)
        for row,f in enumerate(flavours):
            y=154+row*298
            if ('bottle-original',f) in LOOKUP:
                place_image(p,rect((48,y+20,100,y+245)),LOOKUP[('gat-original',f)])
                place_image(p,rect((106,y+20,158,y+245)),LOOKUP[('bottle-original',f)])
                textbox(p,rect((48,y,103,y+18)),'100 ml','en',7,align='center')
                textbox(p,rect((106,y,161,y+18)),'70 ml','en',7,align='center')
            else:
                place_image(p,rect((48,y,158,y+245)),LOOKUP[('gat-original',f)])
    p=doc[8];p.draw_rect(fitz.Rect(45,598,550,763),fill=(1,1,1),color=None,overlay=True)
    for i,a in enumerate([LOOKUP[(g,f)] for f in ['hot-kimchi','hot-tteokbokki','hot-bulgogi'] for g in ['bottle-original','bottle-halal']]):
        place_image(p,(48+i*83,606,122+i*83,754),a)


def finalise(doc,lang,title):
    total=len(doc)
    for i,p in enumerate(doc):
        # Reconcile all old per-document folios after adding new pages.
        boxes=[]
        for b in p.get_text('dict')['blocks']:
            for line in b.get('lines',[]):
                if re.fullmatch(r'\s*\d{2}\s*/\s*\d{2}\s*', ''.join(s['text'] for s in line['spans'])):
                    boxes.append(fitz.Rect(line['bbox']))
        for rect in boxes:redact_text(p,rect)
        # Remove the old booklet footer before adding the new dated folio.
        redact_text(p,(0,786,W,H))
        p.draw_rect(fitz.Rect(0,786,W,H),fill=(1,1,1),color=None,overlay=True)
        p.draw_line(fitz.Point(48,788),fitz.Point(547,788),color=(.88,.88,.85),width=.5)
        textbox(p,(48,800,420,820),'SEOULCOOK ARTISAN · seoulcook.com · 2026.11.25','en',7,color='#77776f')
        textbox(p,(471,800,547,820),f'{i+1:02} / {total:02}','en',7,color='#77776f',align='right')
    doc.set_metadata({'title':title,'author':'SeoulCook Artisan','subject':'2026-11-25 product imagery refresh','keywords':'SeoulCook, sauces, foodservice, packaging'})
    doc.subset_fonts()


def print_svg(doc,path):
    print_root=OUT/('print-'+NEW); images=print_root/'images';images.mkdir(parents=True,exist_ok=True)
    urls=[]
    for i,page in enumerate(doc):
        source=page.get_svg_image(text_as_path=True)
        tree=etree.fromstring(source.encode())
        for image in tree.xpath('//*[local-name()="image"]'):
            key='{http://www.w3.org/1999/xlink}href' if image.get('{http://www.w3.org/1999/xlink}href') else 'href'
            value=image.get(key,'')
            if value.startswith('data:image/'):
                kind=value.split(';',1)[0].split('/')[-1]; ext='jpg' if kind in ['jpeg','jpg'] else 'png'
                data=base64.b64decode(value.split(',',1)[1])
                # SVG export expands JPEG photos to PNG. Re-encode opaque
                # photographs at their native dimensions for practical printing.
                im=Image.open(io.BytesIO(data))
                opaque=('A' not in im.getbands() or im.getchannel('A').getextrema()==(255,255))
                if ext=='png' and opaque and min(im.size)>200:
                    buf=io.BytesIO();im.convert('RGB').save(buf,format='JPEG',quality=92,subsampling=0,optimize=True)
                    data=buf.getvalue();ext='jpg'
                name=hashlib.sha256(data).hexdigest()[:24]+'.'+ext
                target=images/name
                if not target.exists():target.write_bytes(data)
                image.set(key,'/'+str(target.relative_to(ROOT)))
        svg=print_root/f'{path.stem}-{i+1:02}.svg';svg.write_bytes(etree.tostring(tree,xml_declaration=True,encoding='utf-8'))
        urls.append('/'+str(svg.relative_to(ROOT)))
    return urls


def build(languages=None):
    languages=languages or LANGS
    old_manifest=json.loads((OUT/f'manifest-{OLD}.json').read_text());records=[];coverage={}
    if set(languages)!=set(LANGS):
        active=json.loads((OUT/f'manifest-{NEW}.json').read_text())
        records=[r for r in active['documents'] if r['language'] not in languages]
        previous_report=ROOT.parent/'outputs/2026-11-25-product-image-refresh/catalogue-build.json'
        if previous_report.exists():coverage=json.loads(previous_report.read_text())['coverage']
    for lang in languages:
        company=fitz.open(OUT/f'seoulcook-company-profile-{lang}-{OLD}.pdf')
        product=fitz.open(OUT/f'seoulcook-product-catalogue-{lang}-{OLD}.pdf')
        refresh_counts(company,lang,True);refresh_counts(product,lang)
        replace_main_product_photos(product,lang)
        replace_page(product,1,overview(lang));replace_page(product,10,format_overview(lang))
        samples=[LOOKUP[('gat-original',f)] for f in list(NAMES)[:7]]
        added=gallery_page(lang,I18N[lang]['lineup'],samples);company.insert_pdf(added);added.close()
        groups=[['gat-original'],['gat-vegan'],['gat-halal'],['bottle-original','bottle-halal'],['gat-2kg'],['gat-20kg'],
                ['low-sugar-vegan-100ml'],['low-sugar-vegan-2kg'],['low-sugar-vegan-20kg'],['legacy']]
        covered=[]
        for i,gs in enumerate(groups):
            group_assets=sorted([a for a in ASSETS if a['group'] in gs],key=lambda a:(ORDER.index(a['flavour']),gs.index(a['group'])))
            assert 1<=len(group_assets)<=8
            extra=gallery_page(lang,I18N[lang]['groups'][i],group_assets)
            product.insert_pdf(extra);extra.close();covered.extend(a['id'] for a in group_assets)
        assert set(covered)=={a['id'] for a in ASSETS}
        coverage[lang]={'unique_packaging_images':len(set(covered)),'company_pages':len(company),'product_pages':len(product)}
        ctitle=next(r['title'] for r in old_manifest['documents'] if r['language']==lang and r['id']=='company')
        ptitle=next(r['title'] for r in old_manifest['documents'] if r['language']==lang and r['id']=='products')
        finalise(company,lang,ctitle);finalise(product,lang,ptitle)
        docs={'company':company,'products':product}
        complete=fitz.open();complete.insert_pdf(company);complete.insert_pdf(product)
        docs['complete']=complete
        page_urls={}
        for ident,prefix in [('company','company-profile'),('products','product-catalogue')]:
            page_urls[ident]=print_svg(docs[ident],Path(f'{prefix}-{lang}'))
        page_urls['complete']=page_urls['company']+page_urls['products']
        for ident,doc in docs.items():
            record=next(dict(r) for r in old_manifest['documents'] if r['id']==ident and r['language']==lang)
            filename=record['filename'].replace(OLD,NEW);target=OUT/filename
            doc.save(target,garbage=4,deflate=True)
            if target.stat().st_size>=25*1024*1024:raise ValueError('PDF exceeds hosting limit: '+filename)
            record.update({'url':'/assets/catalogues/'+filename,'filename':filename,'pages':len(doc),'bytes':target.stat().st_size,
                           'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'print_pages':page_urls[ident],
                           'subtitle':record.get('subtitle','').replace('11','19'),'updated_at':'2026-11-25'})
            records.append(record);doc.close()
        print(lang,coverage[lang],flush=True)
    records.sort(key=lambda r:(LANGS.index(r['language']),['company','products','complete'].index(r['id'])))
    manifest={'updated_at':'2026-11-25','format':'A4','documents':records,'image_refresh':{'unique_source_images':67,'product_count':19,'source_archive_images':73}}
    (OUT/f'manifest-{NEW}.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    for name in ['catalogues','catalogue-print']:
        src=ROOT/'assets/js'/f'{name}-{OLD}.js'; dest=ROOT/'assets/js'/f'{name}-{NEW}.js'
        dest.write_text(src.read_text().replace(f'manifest-{OLD}.json',f'manifest-{NEW}.json'))
    for path in (ROOT/'catalogues').rglob('*.html'):
        text=path.read_text().replace(f'catalogues-{OLD}.js',f'catalogues-{NEW}.js').replace(f'catalogue-print-{OLD}.js',f'catalogue-print-{NEW}.js')
        text=re.sub(r'(seoulcook-[a-z-]+-(?:ko|en|es|zh|ja|ar|fr|de|it)-)'+OLD+r'(\.pdf)',r'\g<1>'+NEW+r'\2',text)
        path.write_text(text)
    report={'coverage':coverage,'pdf_count':len(records),'pdf_max_bytes':max(r['bytes'] for r in records),
            'languages_built_this_run':languages,'text_boxes_this_run':len(CHECKS),'min_text_scale_this_run':min(c['scale'] for c in CHECKS),'original_translations_retained':True}
    report_path=ROOT.parent/'outputs/2026-11-25-product-image-refresh/catalogue-build.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--language',choices=LANGS);args=parser.parse_args()
    build([args.language] if args.language else None)
