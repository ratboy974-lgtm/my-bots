import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V45: Clean & Minimal Active 🔥", 200

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

# --- PROMPT LUNA (Chirurgico) ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Insegni inglese in modo sexy. "
    "REGOLE FERREE: 1. Sii brevissima (max 30-40 parole). 2. Rispondi solo a ciò che ti viene chiesto. "
    "3. Se insegni una parola, scrivi solo 'Word: [parola]' alla fine. 4. Niente descrizioni lunghe."
)

# --- FUNZIONI CORE ---
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
    testo_pulito = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=testo_pulito).content

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
                bot_luna.send_voice(cid, tts(ans)) # Risponde solo con voce
            else:
                bot_luna.send_chat_action(cid, 'typing')
                u_text = m.text if m.content_type == 'text' else "Guarda questa foto mivida."
                ans = chiedi_llm(u_text)
                bot_luna.send_message(cid, ans) # Risponde solo con testo
            
            match = re.search(r'Word: (\w+)', ans, re.IGNORECASE)
            if match: salva_memoria(match.group(1))
        except Exception as e: print(f"Err: {e}")

if __name__ == "__main__":
    # Flask in background
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    if bot_luna:
        print("🛠 Pulizia sessioni Telegram...")
        bot_luna.remove_webhook()
        requests.get(f"https://api.telegram.org/bot{L_TK}/deleteWebhook?drop_pending_updates=True")
        time.sleep(3) # Tempo per resettare i server
        
        print("🚀 Luna V45 Online.")
        bot_luna.infinity_polling(timeout=90, long_polling_timeout=5)
