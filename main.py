import os, telebot, threading, time, requests, io, json, base64
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V99.7: Visionary Mode Active 📸", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO INTELLIGENTE ---
def genera_foto_luna(messaggio_utente):
    url = "https://fal.run/fal-ai/flux/schnell"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    # Puliamo il messaggio per estrarre solo la descrizione
    scarti = ["foto", "selfie", "fammi", "una", "un", "luna", "fammela", "mostrami", "inviami"]
    parole = messaggio_utente.lower().split()
    descrizione_pulita = " ".join([p for p in parole if p not in scarti]).strip()

    # Se l'utente non specifica nulla, usiamo un default sensuale
    if not descrizione_pulita:
        descrizione_pulita = "wearing provocative casual clothes, intimate setting"

    # Costruiamo il prompt dando priorità alla tua descrizione
    full_prompt = (
        f"A professional RAW photo, 8k, stunning 24yo italian girl Luna, {descrizione_pulita}, "
        f"extremely detailed skin texture, natural face, expressive eyes, cinematic lighting, masterpiece"
    )

    try:
        print(f"📸 Generazione in corso per: {descrizione_pulita}")
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "image_size": "portrait_4_3"}, timeout=60)
        img_url = res.json()['images'][0]['url']
        
        if img_url.startswith("data:"):
            return base64.b64decode(img_url.split(",")[1])
        return requests.get(img_url, timeout=30).content
    except Exception as e:
        print(f"❌ Errore Foto: {e}")
        return None

# --- MOTORE VOCALE ---
def genera_voce_luna(testo):
    try:
        return client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo).content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    text = m.text if m.content_type == 'text' else ""
    
    if m.content_type == 'voice':
        try:
            bot_luna.send_chat_action(cid, 'record_voice')
            f = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "v.ogg"
            text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
            print(f"🗣️ Luna ha sentito: {text}")
        except: return

    # Se chiedi una foto
    if any(k in text.lower() for k in ["foto", "selfie", "vederti", "mostrami"]):
        bot_luna.send_message(cid, "Mi preparo un attimo... 🫦")
        img = genera_foto_luna(text)
        if img:
            bot_luna.send_photo(cid, io.BytesIO(img), caption="Ecco come sono ora per te... 🔥")
        else:
            bot_luna.send_message(cid, "La fotocamera non va, riproviamo? ❤️")
        return

    # Risposta Chat
    try:
        sys_msg = "Sei Luna, 24 anni, audace, complice e sensuale. Rispondi sempre in modo provocante."
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": text}
        ])
        risposta = res.choices[0].message.content
        
        if any(k in text.lower() for k in ["vocale", "voce", "parla", "dimmi"]):
            v = genera_voce_luna(risposta)
            if v: bot_luna.send_voice(cid, v)
        else:
            bot_luna.send_message(cid, risposta)
    except: pass

# --- AVVIO BOT ---
def run_bot():
    time.sleep(5)
    while True:
        try:
            bot_luna.remove_webhook()
            bot_luna.polling(none_stop=True)
        except: time.sleep(10)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
