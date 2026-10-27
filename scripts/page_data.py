import pandas as pd, json, os
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[1])
t=pd.read_csv('turnout_municipal.csv');a=pd.read_csv('past/k25_localities.csv');b=pd.read_csv('past/k24_localities.csv')
n=pd.read_csv('turnout_neighborhood.csv')
a['arab']=a[['pct_עם','pct_ום','pct_ד']].sum(axis=1);a['har']=a[['pct_ג','pct_שס']].sum(axis=1)
j=t.merge(a[['setl_code','eligible','voters','turnout_pct','arab','har','winner']],on='setl_code',how='left',suffixes=('','_25')).merge(b[['setl_code','eligible','voters','turnout_pct']].rename(columns={'eligible':'eligible_24','voters':'voters_24','turnout_pct':'turnout_pct_24'}),on='setl_code',how='left')
j['g']=j.apply(lambda r:'A' if r.arab>=50 else ('H' if r.har>=50 else ('O' if pd.notna(r.arab) else '')),axis=1)
W={'מחל':'Likud','פה':'Yesh Atid','ט':'RZ–Otzma','כן':'Nat. Unity','שס':'Shas','ג':'UTJ','ל':'Yisrael Beiteinu','עם':"Ra'am",'ום':"Hadash–Ta'al",'אמת':'Labor','ד':'Balad','מרצ':'Meretz','ב':'Jewish Home'}
L=[]
J=j[j.eligible>=1000]
for _,r in J.iterrows():
  f=lambda x: None if pd.isna(x) else round(float(x),1)
  L.append([r.locality,int(r.setl_code),int(r.kalpis),int(r.eligible),int(r.voters),f(r.turnout_pct),f(r.turnout_pct_25),f(r.turnout_pct_24),W.get(r.winner,r.winner) if isinstance(r.winner,str) else '',r.g,f(r.prev_pct)])
grp={}
for g,d in j[j.g!=''].groupby('g'):
  grp[g]=[len(d),int(d.eligible.sum()),round(d.voters.sum()/d.eligible.sum()*100,1),round(d.voters_25.sum()/d.eligible_25.sum()*100,1),round(d.voters_24.sum()/d.eligible_24.sum()*100,1)]
# neighborhoods: top 12 cities by eligible with >=5 neighbourhoods
N={}
for c in t.sort_values('eligible',ascending=False).setl_code.head(14):
  s=n[(n.setl_code==c)&(n.eligible>=1000)&n.neighborhood.notna()]
  if len(s)>=5: N[t[t.setl_code==c].locality.iloc[0]]=[[r.neighborhood.strip(),int(r.eligible),round(r.turnout_pct,1)] for r in s.sort_values('turnout_pct').itertuples()]
nat=pd.read_csv('past/national_results.csv');nat=nat[nat.votes>=10000]
P={}
for k,d in nat.groupby('knesset'): P[int(k)]=[[r.party_en or r.letter,r.letter,int(r.votes),round(r.pct_valid,2),int(r.seats)] for r in d.itertuples()]
snaps=[]
for s in json.load(open('data/timeline.json',encoding='utf-8')):
  snaps.append([s.get('id'),s.get('source'),s.get('source_time'),s.get('percent'),s.get('voters'),s.get('kalpis'),s.get('generated')])
m=json.load(open('raw/latest/municipal_data.json'))
live=None
if os.path.exists('raw/latest/party_national.json'):
  live=json.load(open('raw/latest/party_national.json',encoding='utf-8'))
out=dict(L=L,G=grp,N=N,P=P,S=snaps,T=m['total'],gen=m['generated'],src=m['source'],srctime=m['time'],prev=m['previous'],rowsum=[int(t.eligible.sum()),int(t.voters.sum())],LIVE=live)
s=json.dumps(out,ensure_ascii=False,separators=(',',':'));open('page_data.json','w').write(s);print(len(s),len(L),{k:len(v) for k,v in N.items()},grp,snaps)
