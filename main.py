import os, telebot, threading, time, requests, io, json
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V96.0: Online & Stable 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

# Inizializzazione Client
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- GESTIONE MEMORIA JSON ---
MEM_FILE = "memoria_luna.json"

def carica_memoria():
    if os.path.exists(MEM_FILE):
        try:
            with open(MEM_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except: return {}
    return {}

def salva_memoria(mem):
    try:
        with open(MEM_FILE, 'w') as f:
            json.dump(mem, f)
    except: pass

user_memory = carica_memoria()

# --- MOTORE FOTO (FLUX SCHNELL) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, realistic, 8k masterpiece"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt}, timeout=30)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            time.sleep(2)
            img_res = requests.get(img_url, timeout=20)
            if img_res.status_code == 200 and len(img_res.content) > 30000:
                return img_res.content
    except: pass
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    global user_memory
    cid = str(m.chat.id)
    input_text = ""
    
    if m.content_type == 'voice':
        try:
            f_info = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "audio.ogg"
            input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except: return
    else:
        input_text = m.text

    # Logica Foto
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Mi metto in posa per te... 🫦")
        img = genera_foto_luna(input_text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "Uff, la fotocamera è capricciosa. Riprova?")
        return

    # Logica Memoria & Risposta
    if cid not in user_memory: user_memory[cid] = []
    user_memory[cid].append({"role": "user", "content": input_text})
    
    context = [{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Ricorda i dettagli dell'utente."}]
    context.extend(user_memory[cid][-8:])

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=context)
        risposta = res.choices[0].message.content
        user_memory[cid].append({"role": "assistant", "content": risposta})
        salva_memoria(user_memory)
        bot_luna.send_message(cid, risposta)
    except: pass

# --- AVVIO MULTI-THREAD (PER GUNICORN) ---
def start_polling():
    print("⏳ Pulizia sessioni e avvio Bot...")
    try:
        # Il segreto è 'drop_pending_updates=True' per pulire la coda ed evitare il 409
        bot_luna.remove_webhook(drop_pending_updates=True)
        time.sleep(3) # Diamo tempo a Telegram di resettarsi
        me = bot_luna.get_me()
        print(f"✅ Luna Online: @{me.username}")
        # infinity_polling con parametri di sicurezza
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=10, restart_on_change=True)
    except Exception as e:
        print(f"❌ Errore Polling: {e}")
        time.sleep(5) # Se fallisce, aspetta prima di riprovare

# Il thread parte all'avvio del modulo
polling_thread = threading.Thread(target=start_polling, daemon=True)
polling_thread.start()

if __name__ == "__main__":
    # Solo per test locale, Railway usa Gunicorn
    app.run(host='0.0.0.0', port=8080)
