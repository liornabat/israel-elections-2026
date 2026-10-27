import json, re, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
import os
os.chdir(ROOT)
d=json.load(open('page_data.json'))
JERUSALEM=ZoneInfo('Asia/Jerusalem')
PARTY_HE={"Likud":"הליכוד","Yesh Atid":"יש עתיד","RZ–Otzma":"הציונות הדתית–עוצמה יהודית","Religious Zionism–Otzma Yehudit":"הציונות הדתית–עוצמה יהודית","Nat. Unity":"המחנה הממלכתי","National Unity":"המחנה הממלכתי","Shas":"ש\"ס","UTJ":"יהדות התורה","United Torah Judaism":"יהדות התורה","Yisrael Beiteinu":"ישראל ביתנו","Ra'am":"רע\"ם","Hadash–Ta'al":"חד\"ש–תע\"ל","Labor":"העבודה","Balad":"בל\"ד","Meretz":"מרצ","Jewish Home":"הבית היהודי","Blue and White":"כחול לבן","Yamina":"ימינה","Religious Zionist Party":"הציונות הדתית","Joint List":"הרשימה המשותפת","New Hope":"תקווה חדשה"}
def fixname(s):
    s=s.strip()
    m=re.match(r"^\((.*) \((.*)$",s)
    if m: s=f"{m.group(1)} ({m.group(2)})"
    if s.startswith("'"): s=s[1:]+"'"
    return s
L=[[r[0],r[2],r[3],r[4],r[5],r[6],r[7],PARTY_HE.get(r[8],r[8]),r[9]] for r in d['L']]
N={c:[[fixname(x[0]),x[1],x[2]] for x in v] for c,v in d['N'].items()}
P={k:[[PARTY_HE.get(x[0],x[0]),x[1],x[2],x[3],x[4]] for x in v if isinstance(x[0],str) and x[0]] for k,v in d['P'].items()}
G={'A':'רוב למפלגות ערביות ב-2022','H':'רוב למפלגות חרדיות ב-2022','O':'כל שאר היישובים'}
GR=[[G[k]]+v for k,v in sorted(d['G'].items())]
# 2026 chart points: latest national reading in each even-hour block, from the saved timeline.
T={}
for s in d['S']:
    if not s[2] or s[3] is None: continue
    h=int(str(s[2])[:2]); h=h-(h%2)
    if h>=10: T[h]=s[3]
T26=sorted(T.items())
HOURS=[[10,14.8,15.9],[12,25.4,28.4],[14,34.6,38.9],[16,42.3,47.5],[18,51.5,57.7],[20,60.9,66.3],[22,67.4,71.3]]
gen=datetime.datetime.fromisoformat(d['gen']).astimezone(JERUSALEM).strftime('%d.%m.%Y %H:%M')
updated=datetime.datetime.now(JERUSALEM).strftime('%d.%m.%Y %H:%M')
DATA=dict(L=L,N=N,P=P,GR=GR,S=d['S'],T=d['T'],T26=T26,HOURS=HOURS,src=d['src'],srctime=d['srctime'],gen=gen,rowsum=d['rowsum'],prev=d.get('prev'),LIVE=d.get('LIVE'),updated=updated)
tpl=open('site_template.html',encoding='utf-8').read()
live=d.get('LIVE')
if live:
    toc='<a href="#live">תוצאות ארציות</a>'
    section='''<section id="live">
<h2>תוצאות ארציות לפי מפלגה</h2>
<p class="cap" id="liveCap"></p>
<div class="tablewrap"><table id="liveTable"></table></div>
</section>
'''
else:
    toc=''
    section=''
out=tpl.replace('/*__DATA__*/', 'const D='+json.dumps(DATA,ensure_ascii=False)+';')
out=out.replace('__UPDATED__', updated).replace('<!--__TOC_LIVE__-->', toc).replace('<!--__LIVE_SECTION__-->', section)
open('index.html','w',encoding='utf-8').write(out)
print('index.html',len(out),'bytes; localities',len(L),'T26',T26,'live',bool(live),'updated',updated)
