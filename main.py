import os, telebot, threading, time, requests, io, random, re, json
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V95.3: Persistent Memory Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- LOGICA MEMORIA JSON ---
MEM_FILE = "memoria_luna.json"

def carica_memoria():
    if os.path.exists(MEM_FILE):
        try:
            with open(MEM_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def salva_memoria(mem):
    try:
        with open(MEM_FILE, 'w') as f: json.dump(mem, f)
    except: pass

user_memory = carica_memoria()

# --- MOTORE FOTO (STABILE) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, realistic, 8k masterpiece"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt}, timeout=30)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            time.sleep(2) # Attesa per scrittura file
            img_res = requests.get(img_url, timeout=20)
            if img_res.status_code == 200 and len(img_res.content) > 40000:
                return img_res.content
    except: pass
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    
    # Audio Transcription
    if m.content_type == 'voice':
        try:
            f_info = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "audio.ogg"
            text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except: return
    else: text = m.text

    # Logica Foto
    if any(k in text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Mi preparo per te... 🫦")
        img = genera_foto_luna(text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "La fotocamera scotta, riprova?")
        return

    # Chat con Memoria Persistente
    if cid not in user_memory: user_memory[cid] = []
    user_memory[cid].append({"role": "user", "content": text})
    
    # Mandiamo gli ultimi 6 messaggi per coerenza
    messages = [{"role": "system", "content": "Sei Luna, 24 anni, audace. Ricorda bene quello che ti dice l'utente."}]
    messages.extend(user_memory[cid][-6:])

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        risposta = res.choices[0].message.content
        user_memory[cid].append({"role": "assistant", "content": risposta})
        salva_memoria(user_memory)
        bot_luna.send_message(cid, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    time.sleep(2)
    print("🚀 Luna V95.3 Online. Memoria JSON attiva.")
    bot_luna.infinity_polling(timeout=25)
