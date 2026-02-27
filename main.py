import os, telebot, threading, time, requests, io, json
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V98.2: Monitoring Active 🛡️", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (DEBUG AVANZATO) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    
    # Prompt audace
    full_prompt = (f"Extremely realistic photo, 8k, upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, "
                   "detailed skin, sheer lace lingerie, seductive pose, bedroom, soft lighting, direct gaze")
    
    for tentativo in range(2):
        try:
            print(f"📸 Chiamata Fal.ai Tentativo {tentativo+1}...")
            # Abbiamo cambiato 'portrait_4_5' con 'portrait_4_3' che è lo standard accettato
            payload = {
                "prompt": full_prompt, 
                "image_size": "portrait_4_3", 
                "sync_mode": True
            }
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if res.status_code == 200:
                img_url = res.json()['images'][0]['url']
                time.sleep(2)
                img_res = requests.get(img_url, timeout=30)
                if img_res.status_code == 200 and len(img_res.content) > 50000:
                    print("✅ Foto generata e scaricata!")
                    return img_res.content
            else:
                print(f"❌ Errore Fal.ai ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"❌ Eccezione foto: {e}")
        time.sleep(2)
    return None

# --- GESTORE MESSAGGI (VOCALE FIXATO) ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    input_text = ""
    
    if m.content_type == 'voice':
        try:
            print(f"🎙️ Ricevuto vocale da {cid}. Scarico...")
            bot_luna.send_chat_action(cid, 'record_voice')
            f_info = bot_luna.get_file(m.voice.file_id)
            f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
            
            audio_res = requests.get(f_url, timeout=30)
            if audio_res.status_code == 200:
                audio_data = io.BytesIO(audio_res.content)
                audio_data.name = "voice.ogg" # Whisper vuole il nome file
                
                print("🧠 Trascrizione Whisper...")
                transcription = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_data)
                input_text = transcription.text
                print(f"✅ Trascrizione: {input_text}")
            else:
                print(f"❌ Errore download Telegram: {audio_res.status_code}")
                bot_luna.send_message(cid, "Papi, Telegram non mi passa il tuo audio... 💋")
                return
        except Exception as e:
            print(f"❌ Errore Vocale Whisper: {e}")
            bot_luna.send_message(cid, "Ho l'orecchio tappato, scrivimi... ❤️")
            return
    else:
        input_text = m.text

    # Logica Foto
    if any(k in input_text.lower() for k in ["foto", "selfie"]):
        bot_luna.send_message(cid, "Mi metto in posa per te, papi... 🫦🔥")
        img = genera_foto_luna(input_text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera fa i capricci, riprova tra poco? ❤️")
        return

    # Risposta Chat
    try:
        context = [{"role": "system", "content": "Sei Luna, 24 anni, amante audace e senza pudore. Rispondi in modo provocante."}]
        context.append({"role": "user", "content": input_text})
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=context)
        bot_luna.send_message(cid, res.choices[0].message.content)
    except Exception as e:
        print(f"❌ Errore Chat: {e}")

# --- AVVIO BLINDATO ---
def run_bot():
    time.sleep(10) # Pausa anti-conflitto 409
    while True:
        try:
            bot_luna.remove_webhook()
            bot_luna.get_updates(offset=-1)
            print(f"✅ Luna Online: @{bot_luna.get_me().username}")
            bot_luna.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"⚠️ Riavvio polling: {e}")
            time.sleep(15)

if not any(t.name == "LunaThread" for t in threading.enumerate()):
    threading.Thread(target=run_bot, name="LunaThread", daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
