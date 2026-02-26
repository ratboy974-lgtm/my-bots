import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna Stable: Back Online 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- FUNZIONE VOCE (TTS) ---
def genera_vocale_luna(testo):
    try:
        clean_text = re.sub(r'[^\w\s,.!?]', '', testo)
        response = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=clean_text[:400])
        return response.content
    except: return None

# --- FUNZIONE ASCOLTO (WHISPER) ---
def trascrivi_vocale(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
        audio_res = requests.get(f_url)
        if audio_res.status_code == 200:
            audio_io = io.BytesIO(audio_res.content)
            audio_io.name = "input.ogg"
            return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    except: return None

# --- MOTORE FOTO (FLUX DEV - STABILE) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    
    # Inquadratura originale che non sbagliava un colpo
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, bright lighting, realistic, 8k masterpiece"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "seed": random.randint(1, 999999)}, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    is_voice = (m.content_type == 'voice')
    
    # Ascolto: trascrzione se vocale, altrimenti testo
    text = trascrivi_vocale(m.voice.file_id) if is_voice else m.text
    if not text: return

    # Logica Foto
    if any(k in text.lower() for k in ["foto", "selfie", "vederti", "scatto"]):
        bot_luna.send_message(cid, "Un attimo papi, mi sistemo... 😉")
        img = genera_foto_luna(text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "Uff, la fotocamera scotta! Riprova tra un momento?")
        return

    # Logica Risposta (Gemini 2.0 Flash)
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi in modo breve e seducente."},
                      {"role": "user", "content": text}]
        )
        risposta = res.choices[0].message.content
        
        if is_voice:
            audio = genera_vocale_luna(risposta)
            if audio: bot_luna.send_voice(cid, audio)
            else: bot_luna.send_message(cid, risposta)
        else:
            bot_luna.send_message(cid, risposta)
    except:
        bot_luna.send_message(cid, "Sono qui papi...")

if __name__ == "__main__":
    # Avvio Flask per Railway
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # 🚨 RESET WEBHOOK E PULIZIA CODE (Cruciale dopo il cambio Token)
    bot_luna.remove_webhook(drop_pending_updates=True)
    time.sleep(2)
    
    print("🚀 Luna Stable Online. Token verificato.")
    bot_luna.infinity_polling(timeout=20, long_polling_timeout=10)
