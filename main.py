import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V92.2: Stability & Photo Fix 🚀", 200

# --- CONFIGURAZIONE (Assicurati che le variabili su Railway siano corrette) ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- FUNZIONE VOCE DI LUNA (TTS) ---
def genera_vocale_luna(testo):
    try:
        # Puliamo il testo da emoji e simboli per il sintetizzatore
        clean_text = re.sub(r'[^\w\s,.!?]', '', testo)
        response = client_oa.audio.speech.create(
            model="tts-1",
            voice="shimmer", 
            input=clean_text[:400]
        )
        return response.content
    except Exception as e:
        print(f"DEBUG TTS Error: {e}")
        return None

# --- FUNZIONE TRASCRIZIONE (ASCOLTO) ---
def trascrivi_vocale(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
        audio_res = requests.get(f_url)
        if audio_res.status_code == 200:
            audio_io = io.BytesIO(audio_res.content)
            audio_io.name = "input.ogg"
            transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io)
            print(f"DEBUG Sentito: {transcript.text}")
            return transcript.text
    except Exception as e:
        print(f"DEBUG Whisper Error: {e}")
    return None

# --- MOTORE FOTO (FLUX DEV) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    # Pulizia prompt
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").replace("mandami", "").strip()
    
    # Logica Inquadratura
    is_action = any(verb in prompt_puro for verb in ["corre", "corsa", "cammina", "spiaggia", "mare", "palestra", "balla", "salta"])
    vista = "Full body shot, wide angle, action pose" if is_action else random.choice(["Upper body shot", "Full body shot"])
    
    full_prompt = f"{vista} of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, bright lighting, masterpiece, realistic, 8k"
    
    try:
        print(f"DEBUG Generando foto con prompt: {full_prompt}")
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "seed": random.randint(1, 999999)}, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            return requests.get(img_url).content
        else:
            print(f"DEBUG FAL Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"DEBUG Connection Error: {e}")
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    input_luna = ""
    is_voice = False

    if m.content_type == 'voice':
        bot_luna.send_chat_action(cid, 'record_audio')
        input_luna = trascrivi_vocale(m.voice.file_id)
        is_voice = True
        if not input_luna: return
    else:
        input_luna = m.text

    # Logica Foto
    if any(k in input_luna.lower() for k in ["foto", "selfie", "vederti", "scatto"]):
        bot_luna.send_message(cid, "Mi sistemo e arrivo... 😉")
        img = genera_foto_luna(input_luna)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera scotta, riprova tra un attimo!")
        return

    # Logica Risposta Testo/Voce
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve (max 20 parole)."},
                      {"role": "user", "content": input_luna}]
        )
        risposta_testo = res.choices[0].message.content
        
        if is_voice:
            audio_reply = genera_vocale_luna(risposta_testo)
            if audio_reply:
                bot_luna.send_voice(cid, audio_reply)
            else:
                bot_luna.send_message(cid, risposta_testo)
        else:
            bot_luna.send_message(cid, risposta_testo)
    except Exception as e:
        print(f"DEBUG Gemini/OR Error: {e}")
        bot_luna.send_message(cid, "Sono qui papi...")

if __name__ == "__main__":
    # Avvio Flask per Railway
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # --- FIX 409: Pulizia Webhook e attesa ---
    print("🧹 Pulizia sessioni precedenti...")
    bot_luna.remove_webhook()
    # Cancella i messaggi rimasti in coda mentre il bot era spento
    bot_luna.delete_webhook(drop_pending_updates=True) 
    time.sleep(2)
    
    print("🚀 Luna V92.2 Online. Pronto all'ascolto.")
    bot_luna.infinity_polling(timeout=20, long_polling_timeout=10)
