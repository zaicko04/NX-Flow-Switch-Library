#!/usr/bin/env python3
"""NX Flow cover resolver. Conservative exact-title matches; custom images take priority."""
from __future__ import annotations
import datetime,html,json,re,unicodedata,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/catalog.json'
MANUAL=ROOT/'data/covers.json'
SERVER='https://thumbnails.libretro.com'
SYSTEMS={
    'NES':'Nintendo - Nintendo Entertainment System',
    'Super Nintendo':'Nintendo - Super Nintendo Entertainment System',
    'Nintendo 64':'Nintendo - Nintendo 64',
    'Game Boy':'Nintendo - Game Boy',
    'Game Boy Color':'Nintendo - Game Boy Color',
    'Game Boy Advance':'Nintendo - Game Boy Advance',
    'Nintendo DS':'Nintendo - Nintendo DS',
    'Nintendo 3DS':'Nintendo - Nintendo 3DS',
    'GameCube':'Nintendo - GameCube',
    'Wii':'Nintendo - Wii',
    'Wii U':'Nintendo - Wii U',
    'Sega Genesis':'Sega - Mega Drive - Genesis',
    'Sega Saturn':'Sega - Saturn',
    'Dreamcast':'Sega - Dreamcast',
    'PlayStation':'Sony - PlayStation',
    'PlayStation 2':'Sony - PlayStation 2',
    'PSP':'Sony - PlayStation Portable',
    'Xbox':'Microsoft - Xbox',
    'Xbox 360':'Microsoft - Xbox 360',
    'Arcade':'MAME',
}
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag!='a':return
        url=dict(attrs).get('href','')
        if url.lower().endswith('.png') and not url.startswith('/') and '?' not in url:
            self.links.append(urllib.parse.unquote(html.unescape(url)))

def valid(url):
    if not isinstance(url,str):return False
    if url.startswith('assets/covers/') or url.startswith('./assets/covers/'):return '..' not in url and '\\' not in url
    try:return urllib.parse.urlparse(url).scheme in ('https','http') and bool(urllib.parse.urlparse(url).netloc)
    except ValueError:return False

def base_title(value):
    s=str(value or '')
    s=re.sub(r'^((?:\W|\s)+)','',s,flags=re.UNICODE)
    s=re.sub(r'\s*\([^)]*\)\s*$', '', s)
    s=re.sub(r'^(.*?), The - ',r'The \1: ',s,flags=re.I)
    s=re.sub(r'^(.*?), A - ',r'A \1: ',s,flags=re.I)
    s=unicodedata.normalize('NFKD',s).casefold()
    s=''.join(c for c in s if not unicodedata.combining(c))
    s=s.replace('&',' and ').replace('starfox','star fox')
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def priority(filename):
    s=filename.lower()
    if any(x in s for x in ('(beta)','(proto)','(hack)','(demo)','(rev ','(debug)')):
        return 200
    if '(usa)' in s or '(usa,' in s or '(world)' in s:
        return 0
    if '(europe)' in s or '(europe,' in s:return 5
    if '(japan)' in s or '(japan,' in s:return 10
    return 30

def fetch_system(system):
    url=SERVER+'/'+urllib.parse.quote(system,safe='')+'/Named_Boxarts/'
    req=urllib.request.Request(url,headers={'User-Agent':'NXFlowCatalog/1.1 cover matcher (+https://github.com/zaicko04/NX-Flow-Switch-Library)'})
    with urllib.request.urlopen(req,timeout=35) as r:
        body=r.read(12000000)
    parser=Links()
    parser.feed(body.decode('utf-8','replace'))
    art={}
    for fname in parser.links:
        stem=fname[:-4]
        stem=re.sub(r'\s*\(.*$','',stem).strip()
        k=base_title(stem)
        if not k:continue
        candidate=(priority(fname),len(fname),fname)
        if k not in art or candidate<art[k]:
            art[k]=candidate
    return {name:url+urllib.parse.quote(info[2],safe='') for name,info in art.items()}

def main():
    doc=json.loads(CAT.read_text(encoding='utf-8'))
    items=doc.get('items',[])
    meta=doc.setdefault('meta',{})
    try:overrides=json.loads(MANUAL.read_text(encoding='utf-8'))
    except (ValueError,OSError):overrides={}
    by_id=overrides.get('by_id',{})
    by_title=overrides.get('by_title',{})
    today=datetime.datetime.now(datetime.timezone.utc)
    recent=False
    try:
        checked=datetime.datetime.fromisoformat(meta.get('covers_checked_at') or '')
        recent=(today-checked).total_seconds()<24*3600
    except (ValueError,TypeError):pass
    records_by_platform={}
    for entry in items:
        if not isinstance(entry,dict):continue
        chosen=by_id.get(entry.get('id')) or by_title.get(str(entry.get('platform'))+'|'+str(entry.get('title'))) or by_title.get(entry.get('title'))
        if chosen and valid(chosen):
            entry['cover']=chosen
            entry['cover_source']='Personalizado'
        elif entry.get('type')=='Port' and entry.get('platform') in SYSTEMS:
            if not entry.get('cover') and base_title(entry.get('title')):
                records_by_platform.setdefault(entry['platform'],[]).append(entry)
    count=0
    if not recent:
        for platform,group in sorted(records_by_platform.items()):
            # Avoid requesting very large indexes when nothing needs resolving.
            print('Searching',platform,len(group),'ports',flush=True)
            try:matches=fetch_system(SYSTEMS[platform])
            except Exception as exc:
                print('Artwork source unavailable:',platform,str(exc)[:150],flush=True)
                continue
            for item in group:
                u=matches.get(base_title(item.get('title')))
                if u and valid(u):
                    item['cover']=u
                    item['cover_source']='Libretro thumbnails'
                    count+=1
        meta['covers_checked_at']=today.isoformat(timespec='seconds')
    meta['covers_resolved']=sum(1 for x in items if isinstance(x,dict) and x.get('cover'))
    CAT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('New box arts:',count,'Current covers:',meta['covers_resolved'],flush=True)

if __name__=='__main__':main()
