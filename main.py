import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V92.5: Anti-Ghost Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (FIX FOTO NERE) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, realistic, 8k"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "seed": random.randint(1, 999999)}, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            # Attendiamo che il server FAL finisca di scrivere il file
            time.sleep(3)
            img_res = requests.get(img_url, timeout=30)
            # Verifichiamo che l'immagine sia valida e pesi più di 5KB (evita file neri/vuoti)
            if img_res.status_code == 200 and len(img_res.content) > 5000:
                return img_res.content
    except Exception as e:
        print(f"DEBUG Errore Foto: {e}")
    return None

# --- GESTIONE AUDIO & CHAT ---
def trascrivi_vocale(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
        audio_io = io.BytesIO(audio); audio_io.name = "audio.ogg"
        return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    except: return None

def genera_vocale_luna(testo):
    try:
        res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=re.sub(r'[^\w\s,.!?]', '', testo)[:400])
        return res.content
    except: return None

@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    is_voice = (m.content_type == 'voice')
    text = trascrivi_vocale(m.voice.file_id) if is_voice else m.text
    if not text: return

    if any(k in text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Mi preparo e arrivo... 😉")
        img = genera_foto_luna(text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "La fotocamera scotta, riprova!")
        return

    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace. Rispondi breve."}, {"role": "user", "content": text}]
        )
        risposta = res.choices[0].message.content
        if is_voice:
            audio = genera_vocale_luna(risposta)
            bot_luna.send_voice(cid, audio) if audio else bot_luna.send_message(cid, risposta)
        else: bot_luna.send_message(cid, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # Reset webhook per pulire conflitti 409
    print("🧹 Pulizia sessioni...")
    bot_luna.remove_webhook()
    time.sleep(3)
    
    print("🚀 Luna V92.5 Online.")
    bot_luna.infinity_polling(timeout=20, long_polling_timeout=10)
