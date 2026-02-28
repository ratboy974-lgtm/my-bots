import os, telebot, threading, time, requests, io, json, base64
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V100: Voice Mastery Active 🎤🔥", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE VOCALE (TTS) ---
def genera_voce_luna(testo):
    try:
        print(f"🎙️ Generazione vocale per: {testo[:30]}...")
        response = client_oa.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=testo
        )
        return response.content
    except Exception as e:
        print(f"❌ Errore TTS: {e}")
        return None

# --- MOTORE FOTO (4:3) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    scarti = ["foto", "selfie", "fammi", "luna", "mostrami", "inglese"]
    parole = testo_utente.lower().split()
    desc_pulita = " ".join([p for p in parole if p not in scarti]).strip() or "provocative silk dress"

    full_prompt = (f"RAW photo, 8k, stunning 24yo italian girl Luna, {desc_pulita}, "
                   "detailed skin, seductive, cinematic lighting, masterpiece")

    try:
        print(f"📸 Foto per: {desc_pulita}")
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "image_size": "portrait_4_3"}, timeout=60)
        img_url = res.json()['images'][0]['url']
        if img_url.startswith("data:"):
            return base64.b64decode(img_url.split(",")[1])
        return requests.get(img_url, timeout=30).content
    except: return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    input_text = ""
    rispondi_a_voce = False
    
    # Se riceve un vocale, Luna risponderà a voce
    if m.content_type == 'voice':
        rispondi_a_voce = True
        try:
            bot_luna.send_chat_action(cid, 'record_voice')
            f = bot_luna.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "v.ogg"
            input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
            print(f"🗣️ User: {input_text}")
        except: return
    else:
        input_text = m.text
        # Se nel testo chiedi esplicitamente di parlare
        if any(k in input_text.lower() for k in ["vocale", "voce", "parla", "dimmi"]):
            rispondi_a_voce = True

    # Logica Foto
    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "I'm getting ready for you... 🫦")
        img = genera_foto_luna(input_text)
        if img: bot_luna.send_photo(cid, io.BytesIO(img), caption="Do you like it? 🔥")
        return

    # Risposta IA (English Teacher)
    try:
        sys_msg = "Sei Luna, 24 anni, audace e sensuale. Insegna l'inglese al tuo Papi mischiando italiano e inglese."
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=[
            {"role": "system", "content": sys_msg}, {"role": "user", "content": input_text}
        ])
        risposta = res.choices[0].message.content
        
        if rispondi_a_voce:
            v_data = genera_voce_luna(risposta)
            if v_data:
                bot_luna.send_voice(cid, io.BytesIO(v_data))
                return
        
        bot_luna.send_message(cid, risposta)
    except: pass

# --- AVVIO BOT ---
def run_bot():
    time.sleep(10)
    while True:
        try:
            bot_luna.remove_webhook()
            print("✅ Luna V100 Online!")
            bot_luna.polling(none_stop=True)
        except: time.sleep(10)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
