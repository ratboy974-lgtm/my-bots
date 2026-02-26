import os, telebot, threading, time, requests, io, random, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V100: Online 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO FLUX ---
def genera_foto(testo):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    # Bypass filtri: trasforma parole spinte in prompt artistici
    t = testo.lower()
    mood = "provocative black lace lingerie, cinematic lighting" if any(k in t for k in ["nuda", "sexy", "hot"]) else "casual summer outfit"
    
    prompt = f"Hyper-realistic photo of Luna, 24yo italian girl, {mood}, messy dark hair, looking at camera, extremely detailed skin, 8k"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": prompt, "seed": random.randint(1, 9999)}, timeout=60)
        return requests.get(res.json()['images'][0]['url']).content if res.status_code == 200 else None
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    # Se è un vocale, trascrivilo
    if m.content_type == 'voice':
        try:
            f_info = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "audio.ogg"
            text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except: return
    else: text = m.text

    # Se chiede una foto
    if any(k in text.lower() for k in ["foto", "nuda", "sexy", "hot", "vederti"]):
        bot_luna.send_message(cid, "Un attimo papi... 🫦")
        img = genera_foto(text)
        if img: bot_luna.send_photo(cid, img)
        else: bot_luna.send_message(cid, "Fotocamera bloccata, riprova!")
    else:
        # Risposta testo/vocale
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace. Rispondi breve."}, {"role": "user", "content": text}]
        )
        risposta = res.choices[0].message.content
        if m.content_type == 'voice':
            audio_res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=risposta)
            bot_luna.send_voice(cid, audio_res.content)
        else: bot_luna.send_message(cid, risposta)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot_luna.remove_webhook()
    time.sleep(3)
    print("🚀 Luna V100 Online.")
    bot_luna.infinity_polling(timeout=20)
