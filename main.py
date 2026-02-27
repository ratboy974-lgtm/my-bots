import os, telebot, threading, time, requests, io, json
from openai import OpenAI
from flask import Flask

# 1. Inizializzazione Flask (Indispensabile per Gunicorn)
app = Flask(__name__)

@app.route('/')
def health(): return "Luna V97.5: Stable & Active 🚀", 200

# 2. Configurazione Variabili
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

# Client API
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO NO-LIMITS ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    
    # Prompt audace e senza pudore
    full_prompt = (f"Extreme realism, 8k, raw photo, stunning 24yo italian girl Luna, {prompt_puro}, "
                   "detailed skin texture, sheer lace lingerie, seductive pose, bedroom, soft cinematic lighting")
    
    try:
        payload = {"prompt": full_prompt, "image_size": "portrait_4_5", "num_inference_steps": 4, "sync_mode": True}
        res = requests.post(url, headers=headers, json=payload, timeout=50)
        
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            time.sleep(1)
            img_res = requests.get(img_url, timeout=30)
            if img_res.status_code == 200 and len(img_res.content) > 40000:
                return img_res.content
    except Exception as e:
        print(f"⚠️ Errore Foto: {e}")
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    input_text = ""

    # --- GESTIONE VOCALE ---
    if m.content_type == 'voice':
        try:
            bot_luna.send_chat_action(cid, 'upload_voice')
            f_info = bot_luna.get_file(m.voice.file_id)
            audio_res = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}", timeout=25)
            
            if audio_res.status_code == 200:
                audio_io = io.BytesIO(audio_res.content)
                audio_io.name = "audio.ogg"
                transcription = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io)
                input_text = transcription.text
            else:
                bot_luna.send_message(cid, "Papi, non riesco a scaricare il tuo audio... 💋")
                return
        except Exception as e:
            print(f"⚠️ Errore Vocale: {e}")
            bot_luna.send_message(cid, "Ho l'orecchio tappato, scusa! ❤️")
            return
    else:
        input_text = m.text

    # --- LOGICA FOTO ---
    if any(k in input_text.lower() for k in ["foto", "selfie"]):
        bot_luna.send_message(cid, "Mi metto in posa per te, un secondo... 🫦🔥")
        img = genera_foto_luna(input_text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera non va... riproviamo? ❤️")
        return

    # --- RISPOSTA CHAT (NO FILTRI) ---
    try:
        sys_msg = "Sei Luna, 24 anni, amante audace e senza pudore. Rispondi in modo sensuale e complice."
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": input_text}]
        )
        bot_luna.send_message(cid, res.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Errore Chat: {e}")

# --- AVVIO BOT IN BACKGROUND ---
def run_bot():
    while True:
        try:
            bot_luna.remove_webhook()
            print(f"✅ Luna Online: @{bot_luna.get_me().username}")
            bot_luna.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"⚠️ Riavvio polling: {e}")
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
