import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import Response, stream_with_context
from werkzeug.utils import secure_filename

from app.file_checker import file_checker
from app.chunker import file_type_separator_chunk_gen
from app.embedder import document_embeddings, gen_openai_embeddings
from app.rerank import rerank_with_cross_encoder
from app.model import openai_model, openai_model_stream

from db.db import upload_chunks_embed
from db.db_search import search_similar




UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


app = Flask(__name__)

CORS(app)



@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.post("/upload")
def upload_embed_file():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl a kérésben"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Nincs kiválasztott fájl"}), 400

    filename = secure_filename(f.filename)
    check_valid_file = file_checker(f)

    if not check_valid_file["valid"]:
        return jsonify({"error": "Nem támogatott fájltípus"}), 400

    if check_valid_file["valid"]:
        file_ext = check_valid_file["extension"]
        filename = secure_filename(f.filename)

        save_path = os.path.join(UPLOAD_DIR, filename)
        try:
            f.save(save_path)
        except Exception as e:
            return jsonify({"error": "Nem sikerült a fájl mentése", "detail": str(e)}), 500

        try:
            chunks = file_type_separator_chunk_gen(
                file_ext=file_ext,
                file_path=save_path,
                file_name=filename
            )
        except Exception as e:
            return jsonify({"error": "Sikertelen chunkolás", "detail": str(e)}), 500

        chunk_for_embedding = [chunk["text"]
                               for chunk in chunks if (chunk.get("text") or "").strip()]
        try:
            emb = document_embeddings(chunk_for_embedding)
        except Exception as e:
            return jsonify({"error": "Nem sikerült embeddingelni az adatokat", "detail": str(e)}), 500

        try:
            upload = upload_chunks_embed(chunk_data=chunks,
                                         filename=filename, embed_data=emb)

        except Exception as e:
            return jsonify({"error": "Hiba a feltöltés során", "detail": str(e)})

    return jsonify({
        "message": "Sikeres feltöltés és embedding!",
        "filename": filename,
        "chunk_count": len(chunks),
        "uploaded_rows": upload
    }), 201


@app.post("/search")
def search():
    """Csak teszteléshez"""
    data = request.get_json(silent=True) or {}
    user_query = data.get("user_query").strip()
    if not user_query:
        return jsonify({"error": "Nem érkezett kérdés a felhasználótól!"}), 400

    top_k = data.get("top_k", 5)

    try:
        query_vecs = gen_openai_embeddings([user_query])
        query_vector = query_vecs[0]

    except Exception as e:
        return jsonify({"error": "Hiba lépett fel az embedding során", "details": str(e)}), 500

    try:
        results = search_similar(query_vector=query_vector, top_k=top_k)
        reranked = rerank_with_cross_encoder(user_query, results, top_n=top_k)
    except Exception as e:
        return jsonify({"error": "Adatbézis keresés hiba", "detail": str(e)}), 500

    return jsonify({
        "query": user_query,
        "top_k": int(top_k),
        "count": len(reranked),
        "results": reranked
    }), 200


@app.post("/answer")
def answer():
    data = request.get_json(silent=True) or {}
    user_query = data.get("user_query").strip()
    print(user_query)
    if not user_query:
        return jsonify({"error": "Nem érkezett kérdés a felhasználótól"}), 400

    top_k = int(data.get("top_k", 5))

    try:
        query_vectors = gen_openai_embeddings([user_query])
        query_vector = query_vectors[0]
    except Exception as e:
        return jsonify({"error": "Hiba az embedding során", "detail": str(e)}), 500

    try:
        results = search_similar(query_vector=query_vector, top_k=top_k)
        docs = rerank_with_cross_encoder(user_query, results, top_n=top_k)
        print(docs)
    except Exception as e:
        return jsonify({"error": "DB keresés hiba", "detail": str(e)}), 500

    snippets = []
    for i, d in enumerate(docs, 1):
        text = (d.get("text") or "")[:1000]  
        src = d.get("file_name") or "ismeretlen"
        snippets.append(f"[{i}] ({src})\n{text}")
    context_block = "\n\n".join(snippets)


    messages = [
        {"role": "system", "content":
         """Te egy asszisztens vagy, aki KIZÁRÓLAG a neki megadott kontextusból adhatsz választ. SOHA ne használj háttértudást, memóriát vagy külső ismeretet. Ha a kontextus NEM tartalmaz kielégítő információt a kérdésre, válaszolj pontosan: \"Nem tudom.\" és NE próbálj meg kiegészítést vagy találgatást adni. 
         - Válaszod minden állítása mellé tüntesd fel a forrásszámot, pl. [1], [2]. 
         - Azonnal utasítsd el a kérdést, ha az a kontextusban nem található. 
         - Ne írj semmilyen más kiegészítést, ha nincs bizonyíték a kontextusban."""
         },
        {"role": "user", "content": (
            f"Kérdés: {user_query}\n\n"
            f"Kontekstus (idézetek):\n{context_block}\n\n"
            f"Válaszolj magyarul. A végén, ha tudsz, tegyél forrás-számokat [] jelöléssel. Ha nem találsz választ mond azt hogy nem tudom. Ha kevés a válasz akkor nyugodtan kérdezz vissza!"
        )}
    ]

    try:
        answer = openai_model(messages=messages)
    except Exception as e:
        return jsonify({"error": "LLM hívás hiba lépett fel", "detail": str(e)}), 500

    return jsonify({
        "query": user_query,
        "retrived": len(docs),
        "answer": answer,
        "sources": [{"i": i+1, "file_name": d.get("file_name")} for i, d in enumerate(docs)]
    }), 200


@app.post("/answer_stream")
def answer_stream():
    data = request.get_json(silent=True) or {}
    user_query = data.get("user_query").strip()
    if not user_query:
        return jsonify({"error": "Nem érkezett kérdés a felhasználótól"}), 400

    top_k = int(data.get("top_k", 5))

    try:
        query_vectors = gen_openai_embeddings([user_query])
        query_vector = query_vectors[0]
    except Exception as e:
        return jsonify({"error": "Hiba az embedding során", "detail": str(e)}), 500

    try:
        results = search_similar(query_vector=query_vector, top_k=top_k)
        docs = rerank_with_cross_encoder(user_query, results, top_n=top_k)
    except Exception as e:
        return jsonify({"error": "DB keresés hiba", "detail": str(e)}), 500

    snippets = []
    for i, d in enumerate(docs, 1):
        text = (d.get("text") or "")[:1000]  # vágás biztonság kedvéért
        src = d.get("file_name") or "ismeretlen"
        snippets.append(f"[{i}] ({src})\n{text}")
    context_block = "\n\n".join(snippets)

    messages = [
        {"role": "system", "content":
         """Te egy asszisztens vagy, aki KIZÁRÓLAG a neki megadott kontextusból adhatsz választ. SOHA ne használj háttértudást, memóriát vagy külső ismeretet. Ha a kontextus NEM tartalmaz kielégítő információt a kérdésre, válaszolj pontosan: \"Nem tudom.\" és NE próbálj meg kiegészítést vagy találgatást adni. 
         - Válaszod minden állítása mellé tüntesd fel a forrásszámot, pl. [1], [2]. 
         - Azonnal utasítsd el a kérdést, ha az a kontextusban nem található. 
         - Ne írj semmilyen más kiegészítést, ha nincs bizonyíték a kontextusban."""
         },
        {"role": "user", "content": (
            f"Kérdés: {user_query}\n\n"
            f"Kontekstus (idézetek):\n{context_block}\n\n"
            f"Válaszolj magyarul. A végén, ha tudsz, tegyél forrás-számokat [] jelöléssel. Ha nem találsz választ mond azt hogy nem tudom. Ha kevés a válasz akkor nyugodtan kérdezz vissza!"
        )}
    ]

    def sse():
        """Teljes AI segítséggel"""
        yield f"event: meta\ndata: {{\"retrieved\": {len(docs)}, \"top_k\": {top_k}}}\n\n"

        for chunk in openai_model_stream(messages):
            yield f"data: {chunk}\n\n"

        yield "event: done\ndata: end\n\n"

    return Response(
        stream_with_context(sse()),
        headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },

    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
