import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V42: Single Mode Active 🔥", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

# Inizializziamo solo Luna
bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None

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

# --- PROMPT ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Insegni inglese in modo sexy e complice. "
    "Quando insegni una parola nuova, scrivi sempre 'Word of the day: [parola]'. "
    "Rispondi in massimo 150 parole."
)

# --- FUNZIONI CORE ---
def chiedi_llm(system_prompt, user_content, model):
    res = client_or.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
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

def tts(testo, voce):
    # Rimuove i tag tecnici per rendere il parlato naturale
    testo_voce = re.sub(r'Word of the day: \w+', '', testo)
    return client_oa.audio.speech.create(model="tts-1", voice=voce, input=testo_voce[:1000]).content

# --- GESTORE LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            bot_luna.send_chat_action(cid, 'typing')
            
            if m.content_type == 'voice':
                u_text = trascrivi(m.voice.file_id)
            elif m.content_type == 'photo':
                # Luna può ora "vedere" se le mandi una foto
                file_info = bot_luna.get_file(m.photo[-1].file_id)
                img_url = f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}"
                u_text = [
                    {"type": "text", "text": "Guarda questa foto che ti ho mandato, mivida."}, 
                    {"type": "image_url", "image_url": {"url": img_url}}
                ]
            else:
                u_text = m.text

            ans = chiedi_llm(PROMPT_LUNA, u_text, "mistralai/mistral-7b-instruct")
            
            # Memoria
            match = re.search(r'Word of the day: (\w+)', ans, re.IGNORECASE)
            if match: salva_memoria(match.group(1))
            
            # Risposta
            if m.content_type == 'voice':
                bot_luna.send_voice(cid, tts(ans, "shimmer"))
            else:
                bot_luna.send_message(cid, ans)
                # Se vuoi che parli sempre anche via testo, scommenta qui sotto:
                # bot_luna.send_voice(cid, tts(ans, "shimmer"))
                
        except Exception as e:
            print(f"Errore: {e}")

if __name__ == "__main__":
    # Avvio Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    # Avvio Luna pulito
    if bot_luna:
        try: bot_luna.remove_webhook()
        except: pass
        time.sleep(2)
        print("🚀 Luna V42 Online. Nessun conflitto rilevato.")
        bot_luna.infinity_polling(timeout=60, non_stop=True)
