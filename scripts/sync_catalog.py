#!/usr/bin/env python3
"""NX Flow: import public metadata; never mirror commercial game files."""
import json,re,hashlib,urllib.request,urllib.parse,html,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/catalog.json'
HB='https://switch.cdn.fortheusers.org'
SP='https://raw.githubusercontent.com/robzilla10001/SwitchPorts/main/README.md'
SYSTEMS={'Nintendo 64':'Nintendo 64','Super Nintendo Entertainment System':'Super Nintendo','Super Nintendo':'Super Nintendo','Gameboy':'Game Boy','Gameboy Color':'Game Boy Color','Gameboy Advance':'Game Boy Advance','GameCube':'GameCube','Wii':'Wii','Wii U':'Wii U','Nintendo DS':'Nintendo DS','PC':'PC','Genesis':'Sega Genesis','Playstation':'PlayStation','Playstation 2':'PlayStation 2','Xbox':'Xbox','Xbox 360':'Xbox 360','Android 32bit':'Android 32bit','Android 64bit':'Android 64bit','Arcade':'Arcade'}
EMUS={'3DS':'Nintendo 3DS','NDS':'Nintendo DS','GC':'GameCube','NGC/WII':'GameCube / Wii','PSX':'PlayStation','PS1':'PlayStation','PS2':'PlayStation 2','PSP':'PSP','VITA':'PS Vita','N64':'Nintendo 64','DC':'Dreamcast','GB':'Game Boy','GBA':'Game Boy Advance','WIN':'Windows PC'}
CUSTOM={'nintendo':dict(nes='NES',snes='Super Nintendo',n64='Nintendo 64',gb='Game Boy',gbc='Game Boy Color',gba='Game Boy Advance',nds='Nintendo DS',gamecube='GameCube',wii='Wii',wiiu='Wii U',switch='Nintendo Switch'),
'playstation':dict(ps1='PlayStation',ps2='PlayStation 2',psp='PSP',vita='PS Vita'),
'sega':dict(genesis='Sega Genesis',dreamcast='Dreamcast',saturn='Sega Saturn',mastersystem='Master System'),
'xbox':dict(xbox='Xbox',x360='Xbox 360'),'pc':dict(pc='PC'),'android':dict(android32='Android 32bit',android64='Android 64bit')}
CUSTOM['nintendo']['3ds']='Nintendo 3DS'
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'NXFlowLibrary/1.0 public metadata collector'})
    with urllib.request.urlopen(req,timeout=40) as r:return r.read()
def clean(s):
    s=re.sub(r'<[^>]+>',' ',str(s))
    s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
    return html.unescape(re.sub('[*_~]','',s)).strip()
def date(s):
    m=re.search(r'(20\d\d)[/-](\d\d?)[/-](\d\d?)',str(s))
    if m:
        try:return datetime(int(m[1]),int(m[2]),int(m[3])).date().isoformat()
        except ValueError:pass
    return ''
def id_for(prefix,*args):
    return prefix+'-'+hashlib.sha1('::'.join(map(str,args)).encode()).hexdigest()[:14]
def link(s):
    for a in re.findall(r'\]\((https?://[^\s)]+)',s):
        if urllib.parse.urlparse(a).netloc:return a
    return ''
def switchports():
    records=[];section=None;last=''
    for line in fetch(SP).decode('utf-8').splitlines():
        m=re.match(r'^###\s+(.+)',line)
        if m:
            n=re.sub('<.*','',m[1]).strip()
            section=n if n in SYSTEMS or n=='Emulators' else None
            last=''
            continue
        if not section or not line.lstrip().startswith('|'):continue
        c=[x.strip() for x in line.strip().strip('|').split('|')]
        if len(c)<6 or c[0].lower() in ('game','system','title') or c[0].startswith('---'):continue
        if section=='Emulators':
            if len(c)<7:continue
            system,title,version,updated,source,discussion,fw=c[:7]
            typ='Wine / PC' if clean(system).upper()=='WIN' else 'Emulador'
            platform=EMUS.get(clean(system),clean(system))
        else:
            title,version,updated,source,discussion,fw=c[:6]
            typ='Port';platform=SYSTEMS[section]
        if '~~' in source or 'down' in version.lower():continue
        title=clean(title) or last
        if not title:continue
        last=title
        url=link(source)
        if not url:continue
        obj=dict(id=id_for('switchports',url,title,platform),title=title,type=typ,platform=platform,
            version=clean(version),updated=date(updated),source='SwitchPorts',url=url,
            status='Catalogado',description='Revisa la fuente original y sus requisitos.')
        discussion=link(discussion)
        if discussion:obj['discussion']=discussion
        records.append(obj)
    if len(records)<20:raise RuntimeError('SwitchPorts response too short')
    return records
def homebrew():
    data=json.loads(fetch(HB+'/repo.json'))
    if not isinstance(data.get('packages'),list):raise ValueError('No packages')
    records=[]
    for p in data['packages']:
        if not isinstance(p,dict):continue
        name=str(p.get('name') or '')
        if not re.fullmatch('[a-zA-Z0-9._-]{1,120}',name):continue
        typ={'emulator':'Emulador','game':'Juego homebrew','tool':'Utilidad','app':'Utilidad'}.get(str(p.get('category') or '').lower(),'Homebrew')
        title=str(p.get('title') or name)
        context=(name+' '+title+' '+str(p.get('description') or '')[:200]).lower()
        platform='Nintendo Switch'
        if re.search(r'\b(wine|box64|fex)\b',context):typ='Wine / PC';platform='Windows PC'
        elif typ=='Emulador':
            platform='Multisistema'
            for term,pf in [('ppsspp','PSP'),('melonds','Nintendo DS'),('mgba','Game Boy Advance'),('n64','Nintendo 64'),('flycast','Dreamcast'),('ps1','PlayStation')]:
                if term in context:platform=pf;break
        q=urllib.parse.quote(name)
        records.append(dict(id='hbas-'+name.lower(),title=title,type=typ,platform=platform,
            source='HB App Store',version=str(p.get('version') or ''),author=str(p.get('author') or ''),
            url='https://hb-app.store/switch/'+q,download=HB+'/zips/'+q+'.zip',
            icon=HB+'/packages/'+q+'/icon.png',description=str(p.get('details') or p.get('description') or '')[:1000],
            status='Publicado en HB App Store'))
    if len(records)<10:raise RuntimeError('HB App Store response too short')
    return records
def forum():
    root=ET.fromstring(fetch('https://gbatemp.net/forums/nintendo-switch.283/index.rss'))
    records=[]
    for x in root.findall('.//item'):
        title=x.findtext('title') or ''
        url=x.findtext('link') or ''
        if '/threads/' not in url or 'gbatemp.net' not in url:continue
        if not re.search(r'\b(port|homebrew|emulator|wine|release|nx)\b',title,re.I):continue
        if re.search(r'\b(help|request|question|rumor|problem)\b',title,re.I):continue
        records.append(dict(id=id_for('gbatemp',url),title=title,type='Comunidad',
            platform='Nintendo Switch',source='GBAtemp',discussion=url,status='Por verificar',
            description='Publicación de la comunidad, no confirmada como descarga oficial.'))
    return records
def custom():
    records=[]
    for path in sorted((ROOT/'data/custom').glob('*/*.json')):
        family=path.parent.name; platform=CUSTOM.get(family,{}).get(path.stem)
        if not platform:continue
        try:
            for item in json.loads(path.read_text(encoding='utf-8')).get('items',[]):
                if not isinstance(item,dict) or not item.get('title'):continue
                rec=dict(item)
                rec.update(id=rec.get('id') or id_for('custom',str(path),rec['title']),type='Port',
                    family=family,platform=platform,source=rec.get('source') or 'Colección propia')
                records.append(rec)
        except (ValueError,OSError,TypeError) as e:print(path,e)
    return records
def main():
    try: old=json.loads(OUT.read_text(encoding='utf-8')).get('items',[])
    except (OSError,ValueError):old=[]
    data=[];status={}
    for source,fn in [('SwitchPorts',switchports),('HB App Store',homebrew),('GBAtemp',forum)]:
        try:
            entries=fn()
            if source=='GBAtemp':entries=(entries+[x for x in old if x.get('source')==source])[:250]
            status[source]=str(len(entries))+' importados'
        except Exception as e:
            entries=[x for x in old if x.get('source')==source]
            status[source]='Error: '+str(e)[:120]+'; conservados '+str(len(entries))
        data.extend(entries)
    data.extend(x for x in old if x.get('source') not in ('SwitchPorts','HB App Store','GBAtemp'))
    data.extend(custom())
    items={str(x['id']):x for x in data if isinstance(x,dict) and x.get('id') and x.get('title')}
    prior={str(x['id']):x for x in old if isinstance(x,dict) and x.get('id')}
    for rec in items.values():
        p=prior.get(str(rec['id'])) or {}
        if not rec.get('cover') and p.get('cover'):
            rec['cover']=p['cover']
            if p.get('cover_source'):rec['cover_source']=p['cover_source']
    sorted_items=sorted(items.values(),key=lambda x:x.get('updated',''),reverse=True)
    try: old_meta=json.loads(OUT.read_text(encoding='utf-8')).get('meta',{})
    except (OSError,ValueError):old_meta={}
    result={'meta':{'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'sources':status,'notice':'Datos públicos; GBAtemp queda por verificar.',
        'covers_checked_at':old_meta.get('covers_checked_at')},'items':sorted_items}
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Catalog items:',len(sorted_items),status)
if __name__=='__main__':main()
