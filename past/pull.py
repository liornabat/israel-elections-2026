import json,urllib.request,urllib.parse,csv,time
R={'k25_localities':'b392b8ee-ba45-4ea0-bfed-f03a1a36e99c','k25_ballots':'cc223336-07bc-485d-b160-62df92967c0a','k24_localities':'9921a347-8466-4ef4-81f9-22523c5c4632','k24_ballots':'419be3b0-fd30-455a-afc0-034ec36be990'}
for name,rid in R.items():
  recs=[];off=0;fields=None
  while True:
    u=f"https://data.gov.il/api/3/action/datastore_search?resource_id={rid}&limit=5000&offset={off}"
    for a in range(4):
      try:
        d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=120));break
      except Exception as e: print('retry',e);time.sleep(3)
    r=d['result'];fields=[f['id'] for f in r['fields'] if f['id']!='_id']
    recs+=r['records'];off+=len(r['records'])
    if not r['records'] or off>=r['total']: break
  json.dump({'resource_id':rid,'source':f'https://data.gov.il/api/3/action/datastore_search?resource_id={rid}','total':r['total'],'fields':fields,'records':recs},open(name+'_raw.json','w'),ensure_ascii=False)
  with open(name+'_raw.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(recs)
  print(name,len(recs),r['total'],fields[:12])
