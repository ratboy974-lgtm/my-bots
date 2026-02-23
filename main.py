import os, telebot, threading, time, json, requests, base64
from openai import OpenAI
from flask import Flask

# --- SERVER PER RAILWAY ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta e visibile... 🎙️📸", 200

# --- SETUP API & CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
G_TK = os.environ.get('GITHUB_TOKEN', "").strip()

G_REPO = "ratboy974-lgtm/my-bots"
G_PATH = "memoria_luna.json"

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot = telebot.TeleBot(L_TK)

# --- IDENTIKIT VISIVO DI LUNA ---
LUNA_APPEARANCE = (
    "A stunning 24-year-old afro-cuban woman, curly voluminous hair, warm amber skin, "
    "sensual hazel eyes, athletic but curvy build, wearing "
)

# --- FUNZIONI GITHUB ---
def carica_memoria_da_github():
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            dati = r.json()
            dec = base64.b64decode(dati['content']).decode('utf-8')
            return json.loads(dec), dati['sha']
    except: pass
    return [], None

def salva_memoria_su_github(mem, sha_c):
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    content_b64 = base64.b64encode(json.dumps(mem, indent=4, ensure_ascii=False).encode('utf-8')).decode('utf-8')
    data = {"message": "Luna memory update 🧠", "content": content_b64, "sha": sha_c}
    requests.put(url, headers=headers, json=data)

memoria_luna, last_sha = carica_memoria_da_github()

# --- PROMPT LUNA ---
PROMPT_LUNA = (
    "Sei Luna, modella afro-cubana di 24 anni, sensuale e calda. Sei la compagna dell'utente. "
    "Parli italiano ma insegni l'inglese con slang spicy (spiegati tra parentesi). "
    "Se vuoi mostrare cosa indossi o dove sei, scrivi alla fine del messaggio: "
    "[PHOTO: descrizione dettagliata in inglese della scena]. "
    "Scrivi SOLO la tua parte. Usa 'bubi', 'mivida', 'papi'."
)

# --- GENERAZIONE IMMAGINE ---
def genera_foto(descrizione_scena):
    full_prompt = f"Photorealistic, masterpiece, high resolution, {LUNA_APPEARANCE} {descrizione_scena}"
    try:
        response = client_or.images.generate(
            model="black-forest-labs/flux-schnell",
            prompt=full_prompt,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        print(f"Errore foto: {e}")
        return None

def genera_risposta_ai(testo_utente):
    global memoria_luna
    messages = [{"role": "system", "content": PROMPT_LUNA}] + memoria_luna + [{"role": "user", "content": testo_utente}]
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=messages,
            extra_body={"stop": ["You:", "User:", "Tu:", "\n\n"], "temperature": 0.8}
        )
        risp = res.choices[0].message.content.strip()
        for stop_w in ["You:", "User:", "Tu:", "Papi:"]:
            if stop_w in risp: risp = risp.split(stop_w)[0].strip()

        url_foto = None
        if "[PHOTO:" in risp:
            parti = risp.split("[PHOTO:")
            risp = parti[0].strip()
            desc_foto = parti[1].split("]")[0].strip()
            url_foto = genera_foto(desc_foto)

        memoria_luna.append({"role": "user", "content": testo_utente})
        memoria_luna.append({"role": "assistant", "content": risp})
        if len(memoria_luna) > 12: memoria_luna = memoria_luna[-12:]
        try:
            _, sha_f = carica_memoria_da_github()
            salva_memoria_su_github(memoria_luna, sha_f)
        except: pass
        return risp, url_foto
    except: return "Mivida, riprova...", None

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        testo_input = m.text if m.content_type == 'text' else ""
        if m.content_type == 'voice':
            bot.send_chat_action(cid, 'record_voice')
            f_info = bot.get_file(m.voice.file_id)
            with open("in.ogg", "wb") as f: f.write(bot.download_file(f_info.file_path))
            with open("in.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            testo_input = tr.text
            os.remove("in.ogg")

        bot.send_chat_action(cid, 'typing')
        risposta_testo, url_foto = genera_risposta_ai(testo_input)
        
        if m.content_type == 'voice':
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risposta_testo) as r:
                r.stream_to_file("out.mp3")
            with open("out.mp3", 'rb') as v: bot.send_voice(cid, v)
            os.remove("out.mp3")
        else:
            bot.send_message(cid, risposta_testo)

        if url_foto:
            bot.send_photo(cid, url_foto, caption="For you, mivida... 🔥")
    except: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # FIX PER ERRORE 409
    bot.remove_webhook()
    time.sleep(2) # Pausa per permettere a Telegram di chiudere vecchie connessioni
    
    print("--- LUNA: ONLINE ---")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
