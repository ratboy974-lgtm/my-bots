import os, telebot, threading, time, requests, json, re  # <--- FIX: aggiunto 're'
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna & Cox V41: Memory & Voice Fixed 🔥", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
C_TK = clean_token('TOKEN_COX')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None
bot_cox  = telebot.TeleBot(C_TK) if ":" in C_TK else None

# --- FILE DI MEMORIA ---
MEMORY_FILE = "luna_memory.json"

def carica_memoria():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f: return json.load(f)
        except: return {"inglese_progressi": []}
    return {"inglese_progressi": []}

def salva_memoria(nuova_parola):
    mem = carica_memoria()
    if nuova_parola not in mem["inglese_progressi"]:
        mem["inglese_progressi"].append(nuova_parola)
        with open(MEMORY_FILE, "w") as f: json.dump(mem, f)

# --- PROMPTS ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Insegni inglese in modo sexy. "
    "Quando insegni una parola nuova, scrivila esattamente così: 'Word of the day: [parola]'. "
    "Rispondi in massimo 150 parole."
)
PROMPT_COX = (
    "Sei il Dr. Perry Cox. Genio veterinario acido e brutale. "
    "Se ricevi una foto, analizzala tecnicamente. Max 150 parole."
)

# --- FUNZIONI CORE ---
def chiedi_llm(system_prompt, user_content, model):
    # Gestione per contenuti misti (testo + immagini per Cox)
    res = client_or.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

def trascrivi(bot, token, file_id):
    fname = f"/tmp/voice_{file_id}.ogg"
    try:
        file_info = bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{token}/{file_info.file_path}"
        with open(fname, "wb") as f: f.write(requests.get(url).content)
        with open(fname, "rb") as f:
            return client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    finally:
        if os.path.exists(fname): os.remove(fname)

def tts(testo, voce):
    # Rimuoviamo eventuali tag ART o descrizioni tecniche dal parlato
    testo_voce = re.sub(r'Word of the day: \w+', '', testo)
    return client_oa.audio.speech.create(model="tts-1", voice=voce, input=testo_voce[:1000]).content

# --- GESTORE LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            u_text = trascrivi(bot_luna, L_TK, m.voice.file_id) if m.content_type == 'voice' else m.text
            ans = chiedi_llm(PROMPT_LUNA, u_text, "mistralai/mistral-7b-instruct")
            
            # Salvataggio parola nella memoria
            match = re.search(r'Word of the day: (\w+)', ans, re.IGNORECASE)
            if match: salva_memoria(match.group(1))
            
            if m.content_type == 'voice':
                bot_luna.send_voice(cid, tts(ans, "shimmer"))
            else:
                bot_luna.send_message(cid, ans)
        except Exception as e:
            print(f"Errore Luna: {e}")

# --- GESTORE COX ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_cox(m):
        cid = m.chat.id
        try:
            if m.content_type == 'photo':
                file_info = bot_cox.get_file(m.photo[-1].file_id)
                img_url = f"https://api.telegram.org/file/bot{C_TK}/{file_info.file_path}"
                content = [
                    {"type": "text", "text": "Analizza questa immagine clinica, Boia!"}, 
                    {"type": "image_url", "image_url": {"url": img_url}}
                ]
                ans = chiedi_llm(PROMPT_COX, content, "google/gemini-flash-1.5")
            else:
                u_text = trascrivi(bot_cox, C_TK, m.voice.file_id) if m.content_type == 'voice' else m.text
                ans = chiedi_llm(PROMPT_COX, u_text, "google/gemini-flash-1.5")

            if m.content_type == 'voice':
                bot_cox.send_voice(cid, tts(ans, "onyx"))
            else:
                bot_cox.send_message(cid, ans)
        except Exception as e:
            print(f"Errore Cox: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    # Pulizia Webhook all'avvio per evitare Conflict 409
    for b in [bot_luna, bot_cox]:
        if b:
            try: b.remove_webhook()
            except: pass
            time.sleep(1)
            threading.Thread(target=b.infinity_polling, kwargs={'timeout': 60, 'non_stop': True}).start()
    
    while True: time.sleep(60)
