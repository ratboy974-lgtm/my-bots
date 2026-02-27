import os, telebot, threading, time, requests, io, json, base64
from openai import OpenAI
from flask import Flask

# --- 1. QUESTO È QUELLO CHE MANCAVA ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna V99.6: Alive & Kicking 🫦", 200

# --- 2. CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- 3. MOTORE FOTO & VOCALE (FIXED) ---
def genera_foto_luna(testo):
    url = "https://fal.run/fal-ai/flux/schnell"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt = f"Hyper-realistic 8k photo, stunning 24yo italian girl Luna, {testo}, seductive silk nightwear, bedroom lighting"
    try:
        res = requests.post(url, headers=headers, json={"prompt": prompt, "image_size": "portrait_4_3"}, timeout=60)
        img_url = res.json()['images'][0]['url']
        return base64.b64decode(img_url.split(",")[1]) if img_url.startswith("data:") else requests.get(img_url).content
    except: return None

def genera_voce_luna(testo):
    try:
        return client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo).content
    except: return None

# --- 4. GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    text = m.text if m.content_type == 'text' else ""
    if m.content_type == 'voice':
        try:
            f = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "v.ogg"
            text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except: return

    if any(k in text.lower() for k in ["foto", "selfie"]):
        bot_luna.send_message(cid, "Mi metto in posa... 🫦")
        img = genera_foto_luna(text)
        if img: bot_luna.send_photo(cid, io.BytesIO(img))
        return

    res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace."}, {"role": "user", "content": text}])
    risposta = res.choices[0].message.content
    if any(k in text.lower() for k in ["vocale", "voce", "parla"]):
        v = genera_voce_luna(risposta)
        if v: bot_luna.send_voice(cid, v)
    else: bot_luna.send_message(cid, risposta)

# --- 5. AVVIO THREAD ---
def run_bot():
    time.sleep(5)
    while True:
        try:
            bot_luna.remove_webhook()
            bot_luna.polling(none_stop=True)
        except: time.sleep(10)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
