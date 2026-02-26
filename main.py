import os, telebot, threading, time, requests, io, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V90: Action & Wide View Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (ACTION & WIDE ANGLE) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").replace("mandami", "").strip()
    
    # LOGICA INQUADRATURA: Se l'utente chiede azioni, forziamo il "Full Body"
    is_action = any(verb in prompt_puro for verb in ["corre", "corsa", "cammina", "spiaggia", "mare", "palestra", "balla", "salta"])
    
    if is_action:
        # Inquadratura larga per vedere l'azione e il corpo intero
        vista = "Full body shot, wide angle, action shot, motion blur, masterpiece"
    else:
        # Inquadratura mista per richieste normali
        vista = random.choice(["Upper body shot", "Medium full shot", "Side profile"])

    full_prompt = f"{vista} of Luna, a stunning 24yo italian girl, {prompt_puro}, hyper-realistic, natural lighting, high resolution, 8k"
    
    payload = {
        "prompt": full_prompt,
        "image_size": "square",
        "seed": random.randint(1, 9999999) 
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            return requests.get(img_url).content
    except Exception as e:
        print(f"Errore FAL: {e}")
    return None

# --- GESTIONE AUDIO (FIXED) ---
def trascrivi_vocale(file_id):
    try:
        file_info = bot_luna.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}"
        response = requests.get(file_url)
        audio_data = io.BytesIO(response.content)
        audio_data.name = "voice.ogg"
        
        transcript = client_oa.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_data
        )
        return transcript.text
    except Exception as e:
        print(f"Errore Whisper: {e}")
        return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    testo_per_luna = ""

    if m.content_type == 'voice':
        bot_luna.send_chat_action(cid, 'typing')
        testo_per_luna = trascrivi_vocale(m.voice.file_id)
        if not testo_per_luna:
            bot_luna.send_message(cid, "Papi, non ho sentito bene, ripeti?")
            return
    else:
        testo_per_luna = m.text

    if any(k in testo_per_luna.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Corro a farmi uno scatto... 🫦")
        img = genera_foto_luna(testo_per_luna)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera scotta, riprova!")
    else:
        try:
            res = client_or.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve."},
                          {"role": "user", "content": testo_per_luna}]
            )
            bot_luna.send_message(cid, res.choices[0].message.content)
        except:
            bot_luna.send_message(cid, "Eccomi papi.")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    print("🚀 Luna V90 Online: Full Body & Action Fix.")
    bot_luna.infinity_polling()
