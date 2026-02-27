import os, telebot, threading, time, requests, io, random, re, json
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V95.2: Persistence & Anti-Black-Fix Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- GESTIONE MEMORIA JSON ---
# Nota: Su Railway il file system è effimero. Per memoria reale servirebbe un DB, 
# ma usiamo il JSON come richiesto per le sessioni correnti.
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

# --- MOTORE FOTO (ANTI-NERO REINFORCED) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, realistic, 8k masterpiece"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt}, timeout=30)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            
            # Controllo qualità: riprova finché il file non è > 40KB
            for i in range(3):
                time.sleep(2 + i)
                img_res = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
                if img_res.status_code == 200:
                    peso = len(img_res.content)
                    if peso > 40000: # 40KB minimo per evitare il nero
                        return img_res.content
                    print(f"⚠️ Foto troppo leggera ({peso} bytes), riprovo...")
    except: pass
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    input_text = ""
    
    # 1. Trascrizione Audio
    if m.content_type == 'voice':
        try:
            f_info = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "audio.ogg"
            input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except: return
    else:
        input_text = m.text

    # 2. Logica Foto
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti", "scatto"]):
        bot_luna.send_message(cid, "Mi metto in posa, un istante... 🫦")
        img = genera_foto_luna(input_text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera non ha messo a fuoco, riprova?")
        return

    # 3. Chat con Memoria
    if cid not in user_memory: user_memory[cid] = []
    user_memory[cid].append({"role": "user", "content": input_text})
    
    # Context window: ultimi 6 messaggi
    history = user_memory[cid][-6:]
    messages = [{"role": "system", "content": "Sei Luna, 24 anni, audace. Ricorda quello che ti dice l'utente."}]
    messages.extend(history)

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        risposta = res.choices[0].message.content
        user_memory[cid].append({"role": "assistant", "content": risposta})
        salva_memoria(user_memory)
        
        bot_luna.send_message(cid, risposta)
    except:
        bot_luna.send_message(cid, "Sono qui papi...")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    time.sleep(2)
    print("🚀 Luna V95.2 Online. Memoria e Anti-Black attivi.")
    bot_luna.infinity_polling(timeout=25)
