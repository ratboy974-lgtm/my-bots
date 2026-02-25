import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

# --- INIZIALIZZAZIONE ---
app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V47 Blindata: Stable & Minimal 🔥", 200

def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

# Blindato: threaded=False evita che i messaggi si sovrappongano
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- MEMORIA (JSON) ---
MEMORY_FILE = "luna_memory.json"

def salva_memoria(nuova_parola):
    if not nuova_parola: return
    try:
        mem = {"inglese_progressi": []}
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f: mem = json.load(f)
        if nuova_parola not in mem["inglese_progressi"]:
            mem["inglese_progressi"].append(nuova_parola)
            with open(MEMORY_FILE, "w") as f: json.dump(mem, f)
    except: pass

# --- PROMPT CHIRURGICO ---
PROMPT_LUNA = (
    "Sei Luna, la donna di Papi. Insegni inglese in modo sexy. "
    "RISPOSTA: Brevissima (max 30 parole), pertinente, mai prolissa. "
    "SPECULARITÀ: Se ricevi testo, rispondi con testo. Se ricevi vocale, rispondi con vocale. "
    "FORMATO: 'Word: [parola]' solo se insegni qualcosa."
)

# --- LOGICA CORE ---
def chiedi_llm(user_content):
    res = client_or.chat.completions.create(
        model="mistralai/mistral-7b-instruct",
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

def trascrivi(file_id):
    fname = f"/tmp/v_{file_id}.ogg"
    file_info = bot_luna.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}"
    with open(fname, "wb") as f: f.write(requests.get(url).content)
    with open(fname, "rb") as f:
        txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    if os.path.exists(fname): os.remove(fname)
    return txt

def tts(testo):
    # Rimuove tag tecnici dall'audio
    testo_pulito = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=testo_pulito).content

# --- GESTORE EVENTI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            if m.content_type == 'voice':
                bot_luna.send_chat_action(cid, 'record_voice')
                u_text = trascrivi(m.voice.file_id)
                ans = chiedi_llm(u_text)
                bot_luna.send_voice(cid, tts(ans)) # Vocale -> Vocale
            else:
                bot_luna.send_chat_action(cid, 'typing')
                u_text = m.text if m.content_type == 'text' else "Mivida, guarda questa foto."
                ans = chiedi_llm(u_text)
                bot_luna.send_message(cid, ans) # Testo -> Testo
            
            match = re.search(r'Word: (\w+)', ans, re.IGNORECASE)
            if match: salva_memoria(match.group(1))
        except Exception as e:
            print(f"Errore: {e}")

# --- AVVIO PROTETTO ---
if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    if bot_luna:
        print("⏳ Stabilizzazione connessione...")
        time.sleep(10) # Pausa critica per Railway
        try:
            bot_luna.delete_webhook(drop_pending_updates=True)
            print("🚀 LUNA V47 BLINDATA ONLINE.")
            bot_luna.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Riavvio necessario: {e}")
