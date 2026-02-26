import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V81: Debug Mode Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- MOTORE FOTO (FAL) ---
def genera_immagine_fal(prompt_utente):
    print(f"📸 Generazione foto per prompt: {prompt_utente}")
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {"prompt": f"Professional photo of Luna, 24yo Italian girl, natural, {prompt_utente}", "image_size": "square", "sync_mode": True}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_data = requests.get(res.json()['images'][0]['url']).content
            bio = io.BytesIO(img_data)
            bio.name = 'luna.jpg'
            return bio
        print(f"❌ Errore FAL: {res.status_code} - {res.text}")
    except Exception as e: print(f"❌ Errore FAL Exception: {e}")
    return None

# --- AUDIO (WHISPER & TTS) ---
def trascrivi(file_id):
    print(f"🎤 Trascrizione vocale {file_id}...")
    try:
        f_info = bot_luna.get_file(file_id)
        f_data = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
        fname = f"/tmp/{file_id}.ogg"
        with open(fname, "wb") as f: f.write(f_data)
        with open(fname, "rb") as f:
            txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
        os.remove(fname)
        return txt
    except Exception as e: 
        print(f"❌ Errore Whisper: {e}")
        return None

def tts(testo):
    print(f"🗣️ Generazione voce per: {testo[:30]}...")
    try:
        res = client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=testo[:300])
        return res.content
    except Exception as e:
        print(f"❌ Errore TTS: {e}")
        return None

# --- LOGICA LLM ---
def chiedi_llm(user_content):
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001", 
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve."}, {"role": "user", "content": str(user_content)}]
        )
        return res.choices[0].message.content
    except Exception as e:
        print(f"❌ Errore LLM: {e}")
        return "Sono qui!"

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            if m.content_type == 'text' and any(k in m.text.lower() for k in ["foto", "vederti", "pic", "selfie"]):
                bot_luna.send_message(cid, "Mi metto carina... 😉")
                f = genera_immagine_fal(m.text)
                if f: bot_luna.send_photo(cid, f)
                else: bot_luna.send_message(cid, "La fotocamera scotta, riprova!")
                return

            if m.content_type == 'voice':
                txt = trascrivi(m.voice.file_id)
                if txt:
                    ans = chiedi_llm(txt)
                    v = tts(ans)
                    if v: bot_luna.send_voice(cid, v)
                    else: bot_luna.send_message(cid, ans)
                return

            if m.content_type == 'text':
                bot_luna.send_message(cid, chiedi_llm(m.text))
        except Exception as e: print(f"❌ Errore Generale: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(2)
        print("🚀 Luna V81 Online. Pronto ai test.")
        bot_luna.infinity_polling(timeout=20)
