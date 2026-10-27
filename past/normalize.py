import pandas as pd, json
P25={'מחל':('Likud','הליכוד',32),'פה':('Yesh Atid','יש עתיד',24),'ט':('Religious Zionism–Otzma Yehudit','הציונות הדתית',14),'כן':('National Unity','המחנה הממלכתי',12),'שס':('Shas','ש"ס',11),'ג':('United Torah Judaism','יהדות התורה',7),'ל':('Yisrael Beiteinu','ישראל ביתנו',6),'עם':("Ra'am",'רע"ם',5),'ום':("Hadash–Ta'al",'חד"ש-תע"ל',5),'אמת':('Labor','העבודה',4),'מרצ':('Meretz','מרצ',0),'ד':('Balad','בל"ד',0),'ב':('Jewish Home','הבית היהודי',0)}
P24={'מחל':('Likud','הליכוד',30),'פה':('Yesh Atid','יש עתיד',17),'שס':('Shas','ש"ס',9),'כן':('Blue and White','כחול לבן',8),'ב':('Yamina','ימינה',7),'אמת':('Labor','העבודה',7),'ג':('United Torah Judaism','יהדות התורה',7),'ל':('Yisrael Beiteinu','ישראל ביתנו',7),'ט':('Religious Zionist Party','הציונות הדתית',6),'ודעם':('Joint List','הרשימה המשותפת',6),'ת':('New Hope','תקווה חדשה',6),'מרצ':('Meretz','מרצ',6),'עם':("Ra'am",'רע"ם',4)}
base=['סמל ועדה','שם ישוב','סמל ישוב','בזב','מצביעים','פסולים','כשרים']
ren={'סמל ועדה':'committee_code','שם ישוב':'locality','סמל ישוב':'setl_code','בזב':'eligible','מצביעים':'voters','פסולים':'invalid','כשרים':'valid','ברזל':'barzel','קלפי':'kalpi','ריכוז':'rikuz','שופט':'judge'}
nat=[]
for y,P,src_l,src_b in [('25',P25,'b392b8ee-ba45-4ea0-bfed-f03a1a36e99c','cc223336-07bc-485d-b160-62df92967c0a'),('24',P24,'9921a347-8466-4ef4-81f9-22523c5c4632','419be3b0-fd30-455a-afc0-034ec36be990')]:
  l=pd.read_csv(f'past/k{y}_localities_raw.csv');b=pd.read_csv(f'past/k{y}_ballots_raw.csv',dtype={'קלפי':str})
  pc=[c for c in l.columns if c not in base]
  V=l['כשרים'].sum();E=l['בזב'].sum();T=l['מצביעים'].sum()
  for c in pc:
    v=int(l[c].sum());nm=P.get(c,('','',0))
    nat.append(dict(knesset=int(y),letter=c,party_en=nm[0],party_he=nm[1],votes=v,pct_valid=round(v/V*100,3),passed_threshold=v/V>=0.0325,seats=nm[2]))
  lo=l.rename(columns=ren);lo['turnout_pct']=(lo.voters/lo.eligible*100).round(2).where(lo.eligible>0)
  lo=lo.rename(columns={c:f'v_{c}' for c in pc})
  for c in pc: lo[f'pct_{c}']=(l[c]/l['כשרים']*100).round(2)
  lo['winner']=l[pc].idxmax(axis=1)
  lo.to_csv(f'past/k{y}_localities.csv',index=False,encoding='utf-8-sig')
  bo=b.rename(columns=ren).rename(columns={c:f'v_{c}' for c in pc});bo['turnout_pct']=(bo.voters/bo.eligible*100).round(2).where(bo.eligible>0)
  bo.to_csv(f'past/k{y}_ballots.csv',index=False,encoding='utf-8-sig')
  print(y,'E',E,'T',T,'V',V,'turnout',round(T/E*100,2),'seats',sum(p[2] for p in P.values()))
nd=pd.DataFrame(nat).sort_values(['knesset','votes'],ascending=[True,False]);nd.to_csv('past/national_results.csv',index=False,encoding='utf-8-sig')
print(nd[nd.votes>50000])
