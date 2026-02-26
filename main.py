import os, telebot, threading, time, requests, io, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V91: Audio & Light Fix Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (PIÙ LUCE & VARIETÀ) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").replace("mandami", "").strip()
    
    # Gestione Inquadratura e Azione
    is_action = any(verb in prompt_puro for verb in ["corre", "corsa", "cammina", "spiaggia", "mare", "palestra", "balla", "salta"])
    
    if is_action:
        vista = "Full body shot, wide angle, action pose"
    else:
        vista = random.choice(["Upper body shot", "Full body shot", "Sitting pose"])

    # Forziamo luce brillante per evitare foto scure
    full_prompt = f"{vista} of Luna, stunning 24yo italian girl, {prompt_puro}, highly detailed skin, soft cinematic lighting, bright environment, masterpiece, 8k, extremely realistic"
    
    payload = {
        "prompt": full_prompt,
        "image_size": "square",
        "seed": random.randint(1, 9999999) 
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
    except Exception as e:
        print(f"DEBUG: Errore FAL: {e}")
    return None

# --- GESTIONE AUDIO (IL NUOVO FIX) ---
def trascrivi_vocale(file_id):
    try:
        # 1. Recupera il percorso del file
        f_info = bot_luna.get_file(file_id)
        f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
        
        # 2. Scarica il file audio
        print(f"DEBUG: Scaricando audio da {f_url}")
        audio_res = requests.get(f_url)
        
        if audio_res.status_code == 200:
            # 3. Crea un file "virtuale" per OpenAI
            audio_io = io.BytesIO(audio_res.content)
            audio_io.name = "input.ogg" # Estensione obbligatoria per Whisper
            
            # 4. Trascrizione
            transcript = client_oa.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_io
            )
            print(f"DEBUG: Trascrizione riuscita: {transcript.text}")
            return transcript.text
        else:
            print(f"DEBUG: Fallito scaricamento audio. Status: {audio_res.status_code}")
    except Exception as e:
        print(f"DEBUG: Errore Whisper totale: {e}")
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    input_luna = ""

    # Se riceve un vocale
    if m.content_type == 'voice':
        bot_luna.send_chat_action(cid, 'typing')
        input_luna = trascrivi_vocale(m.voice.file_id)
        if not input_luna:
            bot_luna.send_message(cid, "Papi, non ho capito cosa hai detto... riprova? 🫦")
            return
    else:
        input_luna = m.text

    # Logica Risposta
    if any(k in input_luna.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Mi preparo e arrivo... 😉")
        img = genera_foto_luna(input_luna)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera non va, riprova papi!")
    else:
        # Risposta da Gemini
        try:
            res = client_or.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace. Rispondi breve."},
                          {"role": "user", "content": input_luna}]
            )
            bot_luna.send_message(cid, res.choices[0].message.content)
        except:
            bot_luna.send_message(cid, "Sono qui papi.")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    print("🚀 Luna V91 Online: Audio Fix & Bright Photos.")
    bot_luna.infinity_polling()
