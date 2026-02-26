import os, telebot, threading, time, requests, io, re
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

# --- MOTORE FOTO (FLUX STABILE) ---
def genera_foto(testo):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    # Prompt pulito e diretto per evitare blocchi
    prompt = f"Extreme realism, a beautiful 24yo italian girl named Luna, messy hair, looking at camera, {testo.lower()}, 8k resolution"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": prompt}, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    text = ""

    # Gestione Vocale
    if m.content_type == 'voice':
        bot_luna.send_chat_action(cid, 'typing')
        try:
            f_info = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "audio.ogg"
            text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except: return
    else:
        text = m.text

    # Logica Foto
    if any(k in text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Un attimo papi, mi sistemo... 😉")
        img = genera_foto(text)
        if img:
            bot_luna.send_photo(cid, img)
        else:
            bot_luna.send_message(cid, "La fotocamera scotta, riprova tra un po'!")
    
    # Risposta Testuale (sempre attiva)
    else:
        try:
            res = client_or.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve."},
                          {"role": "user", "content": text}]
            )
            risposta = res.choices[0].message.content
            # Se l'utente ha mandato un vocale, rispondi con un vocale
            if m.content_type == 'voice':
                audio_res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=risposta)
                bot_luna.send_voice(cid, audio_res.content)
            else:
                bot_luna.send_message(cid, risposta)
        except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # Reset webhook per evitare il 409
    bot_luna.remove_webhook()
    time.sleep(2)
    
    print("🚀 Luna Stable Online. Sistema ripristinato.")
    bot_luna.infinity_polling(timeout=20)
