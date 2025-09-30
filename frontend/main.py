import re
import os
import requests
import streamlit as st
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def clean_text(s: str) -> str:
    """Teljes AI segítséggel -> stream-elés megjelenítéséhez"""
    # több space → 1 space
    s = re.sub(r'\s+', ' ', s)
    # szóközök eltüntetése írásjelek előtt
    s = re.sub(r'\s+([,.:;!?])', r'\1', s)
    # kötőjelek körüli hézagok normalizálása
    s = re.sub(r'\s*-\s*', '-', s)
    # elejéről/végéről trim
    return s.strip()


def sse_events(resp):
    """Egyszerű SSE parser: (event, data_str) párokat yield-el. Teljes AI segítséggel"""
    # Ha a szerver nem küld charsetet, állítsuk be kézzel:
    resp.encoding = 'utf-8'
    event = 'message'
    data_buf = []

    for line in resp.iter_lines(decode_unicode=True):
        if line is None:
            continue
        line = line.strip()

        # Üres sor: esemény lezárása
        if line == "":
            if data_buf:
                yield event, "".join(data_buf)
            event = 'message'
            data_buf = []
            continue

        if line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_buf.append(line[len("data:"):])


st.set_page_config(page_title="Chatbot Starter",
                   page_icon="💬", layout="centered")

st.title("💬 Chatbot alap – Streamlit + Flask")

view = st.sidebar.radio("Nézet", ["Chat", "Chat stream", "Fájlfeltöltés"])

if view == "Chat":
    st.subheader("Chat")
    prompt = st.chat_input("Írj valamit…")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)

        query = {"user_query": prompt, "top_k": 5}
        # resp = requests.post(f"{BACKEND_URL}/search", json=query, timeout=30)
        resp = requests.post(f"{BACKEND_URL}/answer", json=query, timeout=(10,300))

        data = resp.json()

        with st.chat_message("assistant"):
            if resp.ok:
                st.markdown(data.get("answer", "Nincs válasz"))

                if data.get("sources"):
                    st.caption(
                        f"Források: {', '.join(str(s['file_name']) for s in data['sources'])}")
                else:
                    st.error(data)

if view == "Chat stream":
    st.subheader("Chat stream")
    prompt = st.chat_input("Írj valamit…")
    if prompt:
        """Teljes AI segítséggel"""
        with st.chat_message("user"):
            st.markdown(prompt)

        payload = {"user_query": prompt, "top_k": 5}

        with st.chat_message("assistant"):
            placeholder = st.empty()
            raw_parts = []
            try:
                payload = {"user_query": prompt, "top_k": 5}
                with requests.post(f"{BACKEND_URL}/answer_stream",
                                   json=payload, stream=True, timeout=(10,300)) as resp:
                    if resp.status_code != 200:
                        st.error(f"Hiba: {resp.status_code} {resp.text}")
                    else:
                        buffer = []
                        last_flush = time.time()
                        FLUSH_EVERY_SEC = 0.08

                        for evt, payload in sse_events(resp):
                            if evt == "meta":
                                continue
                            if evt == "done":
                                if buffer:
                                    raw_parts.append("".join(buffer))
                                    buffer = []
                                    placeholder.markdown("".join(raw_parts))
                                break

                            # normál szövegchunk
                            buffer.append(payload)

                            if (" " in payload) or (time.time() - last_flush > FLUSH_EVERY_SEC):
                                raw_parts.append("".join(buffer))
                                buffer = []
                                placeholder.markdown("".join(raw_parts))
                                last_flush = time.time()

            except Exception as e:
                st.error(f"Stream hiba: {e}")

        final = clean_text("".join(raw_parts))
        placeholder.markdown(final if final else "_(nincs válasz)_")


elif view == "Fájlfeltöltés":
    st.subheader("Fájlfeltöltés")
    st.caption("Válassz ki egy fájlt és küldd a Flask backendnek.")

    # set type=["pdf","txt","docx"] ha akarsz
    file = st.file_uploader("Fájl kiválasztása", type=None)
    if file is not None:
        if st.button("Feltöltés"):
            try:
                files = {"file": (file.name, file.getvalue(), file.type)}
                resp = requests.post(
                    f"{BACKEND_URL}/upload", files=files, timeout=60)
                if resp.status_code == 201:
                    st.success(f"Sikeres feltöltés: {file.name}")
                    st.json(resp.json())
                else:
                    st.error(f"Sikertelen feltöltés ({resp.status_code})")
                    try:
                        st.json(resp.json())
                    except Exception:
                        st.write(resp.text)
            except Exception as e:
                st.error(f"Hiba a feltöltés során: {e}")

st.sidebar.markdown("---")
st.sidebar.caption(f"Backend: {BACKEND_URL}")
