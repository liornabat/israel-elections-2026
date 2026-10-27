import json,csv,os
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[1])
B='raw/latest/'
m=json.load(open(B+'municipal_data.json'));n=json.load(open(B+'neighborhood_data.json'));k=json.load(open(B+'kalpi_data.json'))
ng=json.load(open(B+'neighborhood_geometry.topojson'));mg=json.load(open(B+'municipal_geometry.topojson'))
nprops={str(g['properties']['id']):g['properties'] for g in ng['objects']['neighborhood']['geometries']}
mprops={str(g['properties']['id']):g['properties'] for g in mg['objects']['municipal']['geometries']}
# centroid approx via bbox of arcs (topojson quantized) - skip; use search api? keep simple
cols=['setl_code','locality','kalpis','eligible','voters','turnout_pct','updated','prev_voters','prev_pct','delta_voters','delta_pct']
def row(code,name,r): return [code,name,r['kalpis'] if 'kalpis' in r else '',r['בזב'],r['מצביעים'],r['percent'],r.get('updated'),r.get('prev_voters'),r.get('prev_percent'),r.get('delta_voters'),r.get('delta')]
with open('turnout_municipal.csv','w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(cols)
  for c,r in m['features'].items(): w.writerow(row(c,r.get('שם ישוב') or mprops.get(c,{}).get('שם ישוב'),r))
with open('turnout_neighborhood.csv','w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['nbr_id','setl_code','locality','neighborhood']+cols[2:])
  for c,r in n['features'].items():
    p=nprops.get(c,{}); w.writerow([c,p.get('SETL_CODE'),p.get('שם ישוב'),p.get('neighborhood_name')]+row(0,0,r)[2:])
names={int(c):(r.get('שם ישוב') or '') for c,r in m['features'].items()}
with open('turnout_kalpi.csv','w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['key','setl_code','locality','nbr_id','neighborhood','kalpi','eligible','voters','turnout_pct','updated','prev_voters','prev_pct','delta_voters','delta_pct'])
  for key,r in k['features'].items():
    p=nprops.get(str(r['nbr']),{}) if r['nbr'] is not None else {}
    w.writerow([key,r['code'],names.get(r['code']),r['nbr'],p.get('neighborhood_name'),r['kalpi'],r['בזב'],r['מצביעים'],r['percent'],r.get('updated'),r.get('prev_voters'),r.get('prev_percent'),r.get('delta_voters'),r.get('delta')])
