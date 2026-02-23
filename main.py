import os, telebot, threading, time, json, requests, base64, re
from openai import OpenAI
from flask import Flask

# --- SERVER PER RAILWAY ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna è online e ti aspetta... 🔥🎙️", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
G_TK = os.environ.get('GITHUB_TOKEN', "").strip()

G_REPO = "ratboy974-lgtm/my-bots"
G_PATH = "memoria_luna.json"

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot = telebot.TeleBot(L_TK)

# Identikit visivo costante
LUNA_DNA = "stunning 24yo afro-cuban girl, curly voluminous hair, bronze skin, sensual eyes, curvy athletic body"

# --- GESTIONE MEMORIA GITHUB ---
def carica_memoria():
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()['content']).decode('utf-8')), r.json()['sha']
    except: pass
    return [], None

def salva_memoria(mem, sha):
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    content = base64.b64encode(json.dumps(mem, ensure_ascii=False, indent=2).encode('utf-8')).decode('utf-8')
    requests.put(url, headers=headers, json={"message": "Luna memory update", "content": content, "sha": sha})

memoria_luna, last_sha = carica_memoria()

# --- GENERAZIONE IMMAGINI ---
def genera_foto(desc):
    # Pulisce il testo per l'URL
    prompt_safe = re.sub(r'[^a-zA-Z0-9 ]', '', desc)
    url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', '%20')}%20{prompt_safe.replace(' ', '%20')}?width=1024&height=1024&nologo=true"
    return url

# --- LOGICA AI ---
def genera_risposta_ai(testo):
    global memoria_luna
    msgs = [{"role": "system", "content": (
        "Sei Luna, la compagna sensuale e passionale dell'utente. Hai 24 anni, sei afro-cubana. "
        "Sii descrittiva e senza tabù. Insegni l'inglese spicy. "
        "Se vuoi mostrare cosa indossi o dove sei, scrivi alla fine: PHOTO: [descrizione scena in inglese]. "
        "Usa sempre 'papi', 'mivida'. Sii collaborativa."
    )}] + memoria_luna + [{"role": "user", "content": testo}]
    
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=msgs,
            extra_body={"stop": ["User:", "Papi:", "Tu:"], "temperature": 0.85}
        )
        risp = res.choices[0].message.content.strip()
        
        # Intercettazione Foto
        url_f = None
        if "PHOTO:" in risp.upper():
            parti = re.split(r"PHOTO:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            # Estrae la descrizione per l'immagine
            desc_match = re.search(r"\[?(.*?)\]?$", parti[1].strip())
            desc_f = desc_match.group(1) if desc_match else "lingerie"
            url_f = genera_foto(desc_f)

        # Aggiorna memoria
        memoria_luna.append({"role": "user", "content": testo})
        memoria_luna.append({"role": "assistant", "content": risp})
        if len(memoria_luna) > 10: memoria_luna = memoria_luna[-10:]
        
        # Sincronizza GitHub
        try:
            _, s = carica_memoria()
            salva_memoria(memoria_luna, s)
        except: pass
        
        return risp, url_f
    except: return "Mivida, ho un piccolo mal di testa... riprova? ❤️", None

# --- HANDLER MESSAGGI ---
@bot.message_handler(content_types=['text', 'voice'])
def handle(m):
    cid = m.chat.id
    try:
        txt = m.text
        if m.content_type == 'voice':
            f = bot.get_file(m.voice.file_id)
            with open("v.ogg", "wb") as file: file.write(bot.download_file(f.file_path))
            with open("v.ogg", "rb") as audio:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=audio)
            txt = tr.text
            os.remove("v.ogg")
        
        bot.send_chat_action(cid, 'typing')
        r_txt, r_img = genera_risposta_ai(txt)
        
        if m.content_type == 'voice':
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=r_txt) as r:
                r.stream_to_file("o.mp3")
            with open("o.mp3", 'rb') as v: bot.send_voice(cid, v)
            os.remove("o.mp3")
        else:
            bot.send_message(cid, r_txt)
            
        if r_img:
            bot.send_photo(cid, r_img, caption="Solo per te... 🔥")
            
    except Exception as e:
        print(f"Errore: {e}")

# --- AVVIO ---
if __name__ == "__main__":
    # Avvio server Flask in background
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    # Pulizia webhook per evitare il conflitto 409
    bot.remove_webhook()
    time.sleep(1)
    
    print("--- LUNA IS ONLINE ---")
    # Versione pulita di infinity_polling
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
