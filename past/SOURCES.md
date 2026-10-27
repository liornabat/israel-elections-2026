# Past Knesset results – sources
Dataset: https://data.gov.il/dataset/votes-knesset (CEC "תוצאות האמת", Knesset 16–25)
Direct CSV downloads return 403 (CloudFront) from the box; pulled via CKAN datastore API instead:
- K25 by locality:  https://data.gov.il/api/3/action/datastore_search?resource_id=b392b8ee-ba45-4ea0-bfed-f03a1a36e99c  (1,216 rows)
- K25 by ballot box: https://data.gov.il/api/3/action/datastore_search?resource_id=cc223336-07bc-485d-b160-62df92967c0a (12,545 rows)
- K24 by locality:  https://data.gov.il/api/3/action/datastore_search?resource_id=9921a347-8466-4ef4-81f9-22523c5c4632  (1,215 rows)
- K24 by ballot box: https://data.gov.il/api/3/action/datastore_search?resource_id=419be3b0-fd30-455a-afc0-034ec36be990 (12,926 rows)
Seats / party names: Wikipedia 2022_ and 2021_Israeli_legislative_election (raw wikitext saved as wiki_*.txt)
Hourly national turnout 2022/2021: ynetnews, JDN, votes26.com (see page)
setl_code 9999 = double envelopes (external votes), eligible=0.
