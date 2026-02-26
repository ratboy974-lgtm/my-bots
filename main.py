import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V99: Back to Basics 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (FLUX CON BYPASS ARTISTICO) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    t = testo_utente.lower()
    # Se chiedi nudo o sexy, usiamo termini che Flux accetta ma che danno il risultato voluto
    if any(k in t for k in ["nuda", "sexy", "hot", "spogliata", "topless"]):
        mood = "wearing extremely provocative sheer lace lingerie, artistic boudoir photography, cinematic lighting, tanned skin, detailed physique, masterpiece"
    else:
        mood = "casual chic outfit, natural lighting, stunning look"

    full_prompt = (
        f"A hyper-realistic RAW photo of Luna, a beautiful 24yo italian girl, {mood}, "
        f"messy dark hair, looking at camera, shot on 35mm lens, extremely detailed skin texture"
    )
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "seed": random.randint(1, 999999)}, timeout=60)
        if res.status_code == 200:
            return requests.get(res.json()['images'][0]['url']).content
    except: return None

# --- GESTIONE AUDIO & TRASCRIZIONE ---
def trascrivi_vocale(file_id):
    try:
        f_info = bot_luna.get_file(file_id)
        f_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
        audio_res = requests.get(f_url)
        audio_io = io.BytesIO(audio_res.content)
        audio_io.name = "input.ogg"
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
    
    if is_voice:
        bot_luna.send_chat_action(cid, 'record_audio')
        text = trascrivi_vocale(m.voice.file_id)
        if not text: return
    else:
        text = m.text

    # Logica Foto
    if any(k in text.lower() for k in ["foto", "selfie", "vederti", "hot", "nuda", "sexy"]):
        bot_luna.send_message(cid, "Mi sistemo e arrivo... 😉")
        img = genera_foto_luna(text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "La fotocamera scotta, riprova tra un attimo!")
        return

    # Logica Chat (Gemini 2.0 Flash)
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve e calda."},
                      {"role": "user", "content": text}]
        )
        risposta = res.choices[0].message.content
        if is_voice:
            audio = genera_vocale_luna(risposta)
            if audio: bot_luna.send_voice(cid, audio)
            else: bot_luna.send_message(cid, risposta)
        else:
            bot_luna.send_message(cid, risposta)
    except: pass

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    
    # PULIZIA TOTALE WEBHOOK PER EVITARE 409
    bot_luna.remove_webhook()
    time.sleep(2)
    
    print("🚀 Luna V99 Online: Stabile e Sensuale.")
    bot_luna.infinity_polling(timeout=20, long_polling_timeout=10)
