import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V44: Minimal & Specular Active 🔥", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None

# --- MEMORIA ---
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

# --- PROMPT LUNA (Versione Snella) ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Insegni inglese in modo sexy e diretto. "
    "Sii concisa, pertinente e mai prolissa. Massimo 50 parole per risposta. "
    "Se insegni una parola, usa il formato: 'Word: [parola]'."
)

# --- FUNZIONI CORE ---
def chiedi_llm(user_content):
    res = client_or.chat.completions.create(
        model="mistralai/mistral-7b-instruct",
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

def trascrivi(file_id):
    fname = f"/tmp/voice_{file_id}.ogg"
    try:
        file_info = bot_luna.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}"
        with open(fname, "wb") as f: f.write(requests.get(url).content)
        with open(fname, "rb") as f:
            return client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    finally:
        if os.path.exists(fname): os.remove(fname)

def tts(testo):
    # Pulisce il testo da tag prima di parlare
    testo_pulito = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=testo_pulito[:500]).content

# --- GESTORE LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            if m.content_type == 'voice':
                bot_luna.send_chat_action(cid, 'record_voice')
                u_text = trascrivi(m.voice.file_id)
                ans = chiedi_llm(u_text)
                # Risposta VOCALE a messaggio VOCALE
                bot_luna.send_voice(cid, tts(ans))
            else:
                bot_luna.send_chat_action(cid, 'typing')
                u_text = m.text if m.content_type == 'text' else "Guarda questa foto mivida."
                ans = chiedi_llm(u_text)
                # Risposta TESTO a messaggio TESTO/FOTO
                bot_luna.send_message(cid, ans)
            
            # Estrazione parola per memoria
            match = re.search(r'Word: (\w+)', ans, re.IGNORECASE)
            if match: salva_memoria(match.group(1))
                
        except Exception as e: print(f"Errore Luna: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        bot_luna.infinity_polling(timeout=60)
