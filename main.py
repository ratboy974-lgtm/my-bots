import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V94: Memory & Photo Fix Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MEMORIA VOLATILE (Per ora in RAM, poi faremo .json) ---
user_memory = {}

def aggiorna_memoria(cid, ruolo, testo):
    if cid not in user_memory: user_memory[cid] = []
    user_memory[cid].append({"role": ruolo, "content": testo})
    if len(user_memory[cid]) > 10: user_memory[cid].pop(0) # Ricorda gli ultimi 10 messaggi

# --- MOTORE FOTO (DOWNLOAD ROBUSTO) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, realistic, 8k masterpiece"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "seed": random.randint(1, 999999)}, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            # Loop di recupero: aspetta che l'immagine sia effettivamente generata
            for i in range(4):
                time.sleep(2 + i)
                img_res = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                if img_res.status_code == 200 and len(img_res.content) > 50000:
                    return img_res.content
    except: pass
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    is_voice = (m.content_type == 'voice')
    
    # Ascolto
    if is_voice:
        try:
            f_info = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "audio.ogg"
            text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except: return
    else: text = m.text

    # Logica Foto
    if any(k in text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Mi metto in posa per te... 🫦")
        img = genera_foto_luna(text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "La fotocamera ha fatto cilecca, riprova!")
        return

    # Logica Chat con Memoria
    aggiorna_memoria(cid, "user", text)
    messages = [{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Segui il filo del discorso."}]
    messages.extend(user_memory.get(cid, []))

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        risposta = res.choices[0].message.content
        aggiorna_memoria(cid, "assistant", risposta)
        
        if is_voice:
            audio_res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=risposta[:400])
            bot_luna.send_voice(cid, audio_res.content)
        else:
            bot_luna.send_message(cid, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    time.sleep(2)
    print("🚀 Luna V94 Online: Memoria e Foto Fixati.")
    bot_luna.infinity_polling(timeout=20, long_polling_timeout=10)
