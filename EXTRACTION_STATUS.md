# GTBank 42-Page PDF – Extraction Status

## Kya ho raha hai (What’s happening)

Report mein **sirf 9 transactions** aa rahe hain kyunke PDF se itna hi data consistently nikal raha hai.  
42-page statement mein normally hundreds of rows honi chahiye, isliye extraction **incomplete** lag raha hai.

## Possible reasons

1. **PDF layout**  
   GTBank PDF mein tables bina clear borders ke ho sakte hain. `pdfplumber` ko table tab hi milta hai jab lines/boxes clear hon. Agar layout complex hai to sirf kuch pages ya kuch rows hi table ki tarah detect hoti hain.

2. **Text order**  
   `extract_text()` har page se text “reading order” mein deta hai. Agar columns side-by-side hon (e.g. Date | Description | Amount) to text order galat ho sakta hai – pehle saari dates, phir saari descriptions – isse humari date+amount line logic saari rows catch nahi karti.

3. **Sirf ek source se data**  
   Ab code **teen sources** use karta hai: **table**, **text**, **words**.  
   Ho sakta hai:
   - Table se 9 rows aa rahi hon
   - Text aur words se 0 (format/layout ki wajah se)
   - Isliye merge ke baad bhi 9 hi reh jate hain.

## Ab kya add kiya hai

- **Console log**  
  Jab aap same PDF dobara run karoge, terminal pe line aayegi:
  - `[GTBank] table=X text=Y words=Z -> merged ... -> N unique`
  - Isse pata chalega: table se kitni, text se kitni, words se kitni rows mili, aur dedupe ke baad kitni rehi.

- **Date parsing**  
  Ab kaafi date formats try kiye ja rahe hain (30-Jan-2026, 30/01/2026, 2026-01-30, 30 Jan 2026, etc.) taake valid rows date parse fail ki wajah se drop na hon.

## Aap kya kar sakte ho

1. **PDF dobara run karo**  
   Same GTBank 42-page file upload karke analysis chalao.  
   Terminal/console mein **woh line** dhoondo:  
   `[GTBank] table=... text=... words=...`  
   Us line ka screenshot ya copy bhej do – isse pata chalega kaun sa source (table / text / words) rows de raha hai.

2. **Agar possible ho to ek sample page**  
   PDF ka **ek page** (personal details hata kar) bhej sakte ho – sirf layout dekhna hai (columns, headings, date/amount format). Us hisaab se parser rules (table/text/words) aur date regex tune kiye ja sakte hain taake zyada rows niklen.

3. **OCR**  
   Agar PDF **scanned** hai (image jaisa), to Tesseract OCR chalu hai jab text kam milta hai. Native digital PDF ke liye usually OCR nahi chalta; is case mein layout/text order fix karna zyada help karega.

---

**Short:**  
Ab bhi 9 isliye aa rahe hain kyunke PDF ka structure (tables/text order) abhi tak humari table + text + words logic ke saath fully match nahi ho raha.  
Log se pata chalega kaun sa source kaam kar raha hai; uske hisaab se next tuning ki ja sakti hai, ya phir ek sample page se exact format dekh kar rules tighten kiye ja sakte hain.
