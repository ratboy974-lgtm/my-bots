import os, telebot, threading, time, requests, io, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V87: Fix Foto e Audio 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (STABILIZZATO) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    # Creazione prompt contestualizzato
    clean_text = testo_utente.lower().replace("foto", "").replace("selfie", "").replace("mandami", "").strip()
    full_prompt = f"Cinematic photo of Luna, 24yo italian girl, natural skin, highly detailed, {clean_text}"
    
    payload = {"prompt": full_prompt, "image_size": "square"}
    
    try:
        print(f"DEBUG: Invio richiesta a FAL con prompt: {full_prompt}")
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            print(f"DEBUG: Foto generata con successo: {img_url}")
            return requests.get(img_url).content
        else:
            print(f"DEBUG ERROR FAL: Status {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"DEBUG EXCEPTION: {e}")
        return None

# --- GESTIONE AUDIO ---
def trascrivi_audio(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        f_data = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
        audio_io = io.BytesIO(f_data)
        audio_io.name = "voice.ogg"
        return client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    except Exception as e:
        print(f"Errore trascrizione: {e}")
        return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    
    # Gestione Vocali
    if m.content_type == 'voice':
        bot_luna.send_chat_action(cid, 'record_audio')
        testo = trascrivi_audio(m.voice.file_id)
        if testo:
            # Qui Luna risponde via testo (se vuoi la voce, basta aggiungere il TTS di prima)
            res = client_or.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "system", "content": "Sei Luna, rispondi audace."}, {"role": "user", "content": testo}]
            )
            bot_luna.send_message(cid, res.choices[0].message.content)
        return

    # Gestione Testo e Foto
    text = m.text.lower()
    if any(k in text for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Un attimo papi, mi sistemo... 🫦")
        img_data = genera_foto_luna(m.text)
        if img_data:
            bot_luna.send_photo(cid, img_data)
        else:
            bot_luna.send_message(cid, "La fotocamera non va. Controlla i log!")
    else:
        # Risposta normale
        response = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace."}, {"role": "user", "content": m.text}]
        )
        bot_luna.send_message(cid, response.choices[0].message.content)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    time.sleep(1)
    print("🚀 Luna V87 Online.")
    bot_luna.infinity_polling()
