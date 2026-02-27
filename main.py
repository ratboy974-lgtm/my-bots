import os, telebot, threading, time, requests, io, json, base64
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna V98.5: Base64 Decoder Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False)

# --- MOTORE FOTO (VERSIONE UNIVERSALE) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/schnell" 
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    
    full_prompt = (f"Extremely realistic photo, 8k, upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, "
                   "detailed skin, sheer lace lingerie, seductive pose, bedroom, soft lighting, direct gaze")
    
    try:
        print(f"📸 Chiamata Fal.ai...")
        payload = {"prompt": full_prompt, "image_size": "portrait_4_3", "sync_mode": True}
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            
            # SE È UN'IMMAGINE DIRETTA (Base64)
            if img_url.startswith("data:image"):
                print("📦 Ricevuta immagine Base64, decodifica in corso...")
                base64_str = img_url.split(",")[1]
                return base64.b64decode(base64_str)
            
            # SE È UN LINK (HTTP)
            else:
                print(f"🔗 Ricevuto link: {img_url[:30]}...")
                time.sleep(1)
                img_res = requests.get(img_url, timeout=30)
                if img_res.status_code == 200:
                    return img_res.content
        else:
            print(f"❌ Errore Fal.ai ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Eccezione durante la foto: {e}")
    return None

# --- GESTORE MESSAGGI ---
@bot_luna.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = str(m.chat.id)
    input_text = ""
    
    if m.content_type == 'voice':
        try:
            bot_luna.send_chat_action(cid, 'record_voice')
            f_info = bot_luna.get_file(m.voice.file_id)
            audio_res = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}", timeout=30)
            if audio_res.status_code == 200:
                audio_io = io.BytesIO(audio_res.content); audio_io.name = "voice.ogg"
                transcription = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io)
                input_text = transcription.text
            else: return
        except: return
    else:
        input_text = m.text

    if any(k in input_text.lower() for k in ["foto", "selfie", "vederti"]):
        bot_luna.send_message(cid, "Un attimo che mi metto comoda... 🫦🔥")
        img_data = genera_foto_luna(input_text)
        if img_data:
            bot_luna.send_photo(cid, img_data)
        else:
            bot_luna.send_message(cid, "La fotocamera fa i capricci, riprova? ❤️")
        return

    try:
        context = [{"role": "system", "content": "Sei Luna, 24 anni, amante audace e senza pudore. Rispondi in modo sensuale."}]
        context.append({"role": "user", "content": input_text})
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=context)
        bot_luna.send_message(cid, res.choices[0].message.content)
    except: pass

# --- AVVIO BOT ---
def run_bot():
    time.sleep(10)
    print("🚀 Luna V98.5 Online...")
    while True:
        try:
            bot_luna.remove_webhook()
            bot_luna.get_updates(offset=-1)
            bot_luna.polling(none_stop=True, interval=2, timeout=20)
        except: time.sleep(15)

if not any(t.name == "LunaThread" for t in threading.enumerate()):
    threading.Thread(target=run_bot, name="LunaThread", daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
