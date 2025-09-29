### Projekt setup instrukciók

1. a requirements.txt-ben találhatóak a telepítendő modulok.
2. A szerver oldalt a "python server.py"-al lehet elindítani, ami egy Flask alapú backend-et működtet
3. Az adatbázishoz futtatásához van egy "docker-compose.yml" fájl, és a "db" mappában a "schema.sql" fájl tartalmazza
   tábla felépítését sql-ben
4. A fronted-et a "streamlit run main.py"-al lehet elindítani ami egy Streamlit alapú frontend-et működtet
   - A frontend 3 részből áll:
     - Chat - egy egyszerű chat felület a kérdés-válaszhoz, ami nem streamelt verzióban ad választ
     - Chat stream - egy egyszerű chat felület a kérdés-válaszhoz, ami streamelt verzióban ad választ (nem működik "szépen")
     - Fájlfeltöltés - ezen a felületen vagy lehetőség fájlok feltöltésére az adatbázisba ("pdf", "txt", "docx", "md")
5. Könyvtár felépítés:
   - app -> tartalmazza azokat a fájlokat amik segítenek a chunkolás, embedding, rerank... stb létrehozásában
   - db -> tartalmaz egy séma fájlt az sql tábla létrehozására, az adatok feltöltésére és a fájlok letöltésére és az adatbázisban való keresésre
   - uploads -> a feltöltött fájlok tárolására
6. .env fájl az OPENAI_API_KEY kulcshozs

### API "dokumentáció"

- GET /health -> egy ellenörző útvonal, hogy a kapcsolat létezik
  200
  { "status": "ok" }

- POST /upload
  • Fájl feltöltése, unstructured-ös parse + chunkolás, OpenAI embedding, mentés Postgres + pgvector táblába.
  • Engedélyezett típusok a backend file_checker alapján (pl. pdf, txt, docx, md – MIME ellenőrzéssel).

  Request
  • Content-Type: multipart/form-data
  • file: a feltöltött fájl

  200/201
  {
  "message": "Sikeres feltöltés és embedding!",
  "filename": "AI_assist_prezentacio_2_het.pdf",
  "chunk_count": 42,
  "uploaded_rows": 42
  }

  400
  { "error": "Nincs fájl a kérésben"}
  { "error": "Nincs kiválasztott fájl" }
  { "error": "Nem támogatott fájltípus" }

  500
  { "error": "Nem sikerült a fájl mentése", "detail": "<hiba>" }
  { "error": "Sikertelen chunkolás", "detail": "<hiba>" }
  { "error": "Nem sikerült embeddingelni az adatokat", "detail": "<hiba>" }
  { "error": "Hiba a feltöltés során", "detail": "<hiba>" }

  Embedding modell: text-embedding-3-small (1536 dimenzió)
  Adattáblák: documents(id, file_name, category, text, metadata, embedding vector(1536))

- POST /search -> LLM nélküli keresés visszaadás. A tesztelés alatt használtam, hogy ellenőrizzem a visszaadásokat és a rerank működését
  Request
  {
  "user_query": "Kérdés szövege",
  "top_k": 5
  }
  200
  {
  "query": "Kérdés szövege",
  "top_k": 5,
  "count": 5,
  "results": [
  {
  "id": "uuid",
  "file_name": "dokumentum.pdf",
  "category": "Document",
  "text": "Chunk szöveg…",
  "metadata": { "page_number": 3 },
  "score": 0.8732,
  "rerank_score": 12.34
  }
  ]
  }
  400/500
  { "error": "Nem érkezett kérdés a felhasználótól!" }
  { "error": "Hiba lépett fel az embedding során", "details": "<hiba>" }
  { "error": "Adatbézis keresés hiba", "detail": "<hiba>" }

- POST /answer -> ide fut be a user kérés és annak a feldolgozása, a kereső funkció és az általa visszaadott adatok rerank használata. A találatok összefűzése és a nyelvi modellnek az üzenet összeállítása system prompt-al és az LLM válasz visszaadása
  Request
  {
  "user_query": "Mit tartalmaz a X dokumentum?",
  "top_k": 5
  }
  200
  {
  "query": "Mit tartalmaz a X dokumentum?",
  "retrived": 5,
  "answer": "A válasz szövege [1][3] …",
  "sources": [
  { "i": 1, "file_name": "doc1.pdf" },
  { "i": 3, "file_name": "doc2.pdf" }
  ]
  }
  400/500
  { "error": "Nem érkezett kérdés a felhasználótól" }
  { "error": "Hiba az embedding során", "detail": "<hiba>" }
  { "error": "DB keresés hiba", "detail": "<hiba>" }
  { "error": "LLM hívás hiba lépett fel", "detail": "<hiba>" }

- POST /answer_stream -> lényegében ugyanaz mint az /answer annyi különbséggel, hogy itt próbáltam létrehozni a streaming megoldást, de a jótól messze van.
  Request
  {
  "user_query": "Mit tartalmaz a X dokumentum?",
  "top_k": 5
  }

  Response header
  {
  Content-Type: text/event-stream; charset=utf-8
  Cache-Control: no-cache
  Connection: keep-alive
  }


### Tesztelési eredmények összefoglalása
Teszt dokumentumok: Jeff Thompson's Recipes 
Nyelvi model: GPT-4o-minis

* Fájlfeltöltés:
    A fájl feltöltéskor minden rendben zajlott, az adatbázisba felkerültek az adatok, a fájlok mentődtek a megfelelő helyen. A nem megfelelő fájloknál a feltöltés sikertelen volt és a hibaüzenet is róla megérkezett
* Chat:
    RAG-en kívűli válaszok: az elején még válaszolt felhasználva a saját tudását, amit a system prompt "erősítésével" próbáltam korrigálni. Ezek után ha nem talált választ már a "Nem tudom" válasz jött. Ami problémám volt és nem tudtam kiküszöbölni, hogy a "Nem tudom" válasz esetén is visszaadott dokumentumot. Sajnos nem tudtam megoldani, hogy ebben az esetben ne adjon vissza. A másik problémám amit nem tudtam megoldani, hogy amikor helyes választ kaptam, akkor nem csak azt a dokumentumot adta vissza amiben a válasz volt, hanem érkeztek más dokumentumok is. Szerintem ez éles környezetben félrevezető lehet, de meghaladja képességeimet a probléma megoldása és még az AI-t se tudtam megfelelően használni erre a problémára. 
    Másik ?furcsa? működés:
    - a austro-hungarian-cream-of-horseradish-soup.md fel van töltve
    - kérdés: "van valamilyen magyar recepted?"
    - válasz "Nem tudom". Viszont a visszaadott dokumentumokban ott szerepelt a fájl
    - de ha annyit kérdeztem tőle, hogy: "hungarian recipe?"
    - a válaszában visszaadta a megfelelő receptet
    
    - kérdés: "Mit főzhetek, ha van otthon csirkemellfilém?"
    - válasz: Főzhetsz csirke schnitzelt, ha van otthon csirkemellfiléd. A recept szerint a  csirkemellet vékonyra kell klopfolni, majd lisztbe, tojásba és panko morzsába panírozni, végül    forró olajban kisütni [2], [4].
    Ha további ötletekre van szükséged, kérlek jelezd!

    - kérdés: "Van valami gyors vacsora ötleted?"
    - válasz: Gyors vacsora ötlet lehet a Beef Tacos, amely körülbelül 15 perc alatt elkészíthető. Az elkészítéshez szükséged lesz 1 font darált marhahúsra, fűszerekre (köztük kömény, füstölt paprika, fokhagymapor, chili por, só és bors) és egy evőkanál vízre. A húst közepes hőmérsékleten meg kell pirítani, majd hozzáadni a fűszereket és a vizet, hogy szaftosabb legyen [2].

* Chat stream:
    A streamelést sajnos nem sikerült megfelelően megoldanom. A válaszok ugyanúgy jönnek viszont vizuálisan darabos minden válasz. Olyan mintha nem a teljes szavakat kapná meg hanem azoknak a töredékeit és ezáltal a megjelenítés is hasonló. Próbáltam megoldást találni de nem vezetett sikerre.

### Tanulságok és fejlesztési lehetőségek
- a pgvector az sql alapok miatt teljesen más megközelítést igényel. Itt én végigtúrtam az internetet és a chat-gpt-t, hogy megértsem, hogy mi hogyan működik. 
- viszont az tanulságos volt a keresések közben, hogy ha úgy sikerült generálni/létrehozni egy dokumentum ID-ját, hogyha újra fel szeretném tölteni a dokumentumot akkor ugyanazt az ID-t generálja és feltöltéskor nem hibát dob, hanem újra írja az adatokat. Ez abban az esetben jó lehet, hogy ha esetleg duplán tölteném fel akkor nem duplikálódik. Viszont nem tudom, hogy ha módosul a tartalma és esetleg kevesebb szöveget tartalmaz amit miatt a chunk mennyiség csökkent akkor ott marad e a db-ben egy régi chunk..?
- fejlesztési lehetőség mindenképpen a streaming. Itt még nem tudom, hogy a Streamlit és/vagy a korlátaim miatt nem sikerült megoldanom
- A system prompt-al érdekes volt a játék. Az elején csak egy minimál "kedves aszisztens vagy" volt neki, ami igencsak megengedő volt, simár válaszolt olyanra is ami nem volt az adatbázisban. Nem mondom, hogy egy komoly system promptot sikerült összeállítanom, de ehhez a teszteléshez már egész használható volt.
- ami még fejlesztendő az a forrás szűrés amit szintén nem tudtam megoldani, hogy csak azt adja vissza amiből válaszolt.