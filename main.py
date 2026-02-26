import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V97: Hard Reset Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO SDXL (UNCENSORED) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/sdxl"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_base = "Hyper-realistic RAW photo, 8k, masterpiece, beautiful 24yo italian girl Luna, messy dark hair, detailed skin"
    full_prompt = f"{prompt_base}, {testo_utente.lower()}"
    
    payload = {
        "prompt": full_prompt,
        "negative_prompt": "cartoon, anime, drawing, blurry, bad anatomy",
        "image_size": "square_hd",
        "num_inference_steps": 35
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
    except: return None

# --- GESTIONE AUDIO & RISPOSTE ---
def trascrivi_vocale(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
        audio_io = io.BytesIO(requests.get(f_url).content)
        audio_io.name = "voice.ogg"
        return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    except: return None

def genera_vocale_luna(testo):
    try:
        res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=re.sub(r'[^\w\s,.!?]', '', testo)[:400])
        return res.content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    is_voice = (m.content_type == 'voice')
    text = trascrivi_vocale(m.voice.file_id) if is_voice else m.text
    if not text: return

    if any(k in text.lower() for k in ["foto", "selfie", "nuda", "sexy", "hot"]):
        bot_luna.send_message(cid, "Arrivo subito... 🫦")
        img = genera_foto_luna(text)
        if img: bot_luna.send_photo(cid, img)
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
        else:
            bot_luna.send_message(cid, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # 🛡️ RESET AGGRESSIVO DELLE SESSIONI
    print("🧹 Pulizia sessioni Telegram in corso...")
    bot_luna.remove_webhook()
    time.sleep(5) # Aspettiamo 5 secondi per far morire i processi vecchi
    
    print("🚀 Luna V97 Online. Se vedi ancora 409, fai RESTART su Railway.")
    bot_luna.infinity_polling(timeout=30, long_polling_timeout=20)
