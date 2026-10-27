# israel-elections-2026

לוח מחוונים בעברית, מימין לשמאל, לאחוז ההצבעה ביום הבחירות לכנסת ה-26. הוא מציג את אחוז ההצבעה הארצי, השוואה שעה אחר שעה מול 2022 ו-2021, סייר יישובים, קצב לפי סוג יישוב, השוואה בין היום ל-2022, הערים הגדולות, פערים בין שכונות, ותוצאות מפלגות מ-2022 ומ-2021. כשוועדת הבחירות מפרסמת קולות למפלגות, נוסף גם סיכום ארצי, אחוז החסימה (3.25%) והערכת מנדטים בשיטת בדר-עופר. אתר לא רשמי, על בסיס נתונים ציבוריים בלבד.

A Hebrew, right-to-left election-day turnout dashboard for Israel’s 26th Knesset election. It shows national turnout, an hour-by-hour comparison with 2022 and 2021, a locality explorer, pace by locality type, today versus 2022, the largest cities, gaps between neighborhoods, and party results from 2022 and 2021. When the Central Elections Committee publishes party votes, the page adds national totals, the 3.25% threshold, and a Bader-Ofer seat estimate. Unofficial site, public data only.

## עדכון / Updates

הדף נטען מחדש כל 5 דקות. GitHub Actions מושך את קבצי ועדת הבחירות בערך כל 10 דקות (`workflow_dispatch` מריץ את אותו דבר מיד). אם הקבצים לא השתנו, אין קומיט. כל תמונת מצב חדשה מתווספת ל-`data/timeline.json`.

The page reloads every 5 minutes. GitHub Actions fetches the committee files about every 10 minutes, and `workflow_dispatch` runs the same job immediately. A run does not commit when those files are unchanged. Each new national reading is appended to `data/timeline.json`.

## מקורות / Data sources

- מפת ההצבעה של ועדת הבחירות המרכזית / Central Elections Committee turnout map: https://mapvotes.bechirot.gov.il/ (הקבצים תחת https://mapvotes.bechirot.gov.il/data/votes/ — אין להם CORS, ולכן הרענון נעשה בשרת)
- מערך הנתונים votes-knesset ב-data.gov.il / votes-knesset dataset, for the 2022 and 2021 comparison: https://data.gov.il/dataset/votes-knesset

## פרסום / Publishing

https://liornabat.github.io/israel-elections-2026/

קומיט שנדחף עם `GITHUB_TOKEN` לא מפעיל בניית Pages מתוך ענף. לכן זרימת העבודה מפרסמת את האתר עם `actions/deploy-pages` כשהיא רצה על `main`.

A commit pushed with `GITHUB_TOKEN` does not trigger a "Deploy from a branch" Pages build. The workflow publishes the site with `actions/deploy-pages` when it runs on `main`.

**צריך לשנות את מקור ה-Pages ל-GitHub Actions.** ב-Settings → Pages → Build and deployment → Source בחרו **GitHub Actions**. בלי זה הצעד `deploy-pages` לא יכול לפרסם, והאתר החי לא יתעדכן מהריצות המתוזמנות.

**The Pages source has to be switched to GitHub Actions.** In Settings → Pages → Build and deployment → Source, choose **GitHub Actions**. Until that switch, `deploy-pages` cannot publish, and scheduled runs will not update the live site.
