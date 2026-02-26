import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V67: Anti-Conflict Engine Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- GENERAZIONE FLUX (FAL.AI) ---
def genera_immagine_fal(prompt_utente):
    if not FAL_K: return None, "Manca FAL_KEY"
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    payload = {
        "prompt": f"Professional RAW photo of Luna, 24yo Italian girl, natural skin, charismatic, {prompt_utente}",
        "image_size": "square",
        "sync_mode": True,
        "enable_safety_checker": False
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            img_res = requests.get(img_url, timeout=30)
            if img_res.status_code == 200:
                bio = io.BytesIO(img_res.content)
                bio.name = 'luna.jpg'
                return bio, None
        return None, f"Errore API {res.status_code}"
    except Exception as e: return None, str(e)

# --- FUNZIONI CORE ---
def trascrivi(file_id):
    fname = f"/tmp/v_{file_id}.ogg"
    with open(fname, "wb") as f: f.write(requests.get(f"https://api.telegram.org/file/bot{L_TK}/{bot_luna.get_file(file_id).file_path}").content)
    with open(fname, "rb") as f: txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    os.remove(fname)
    return txt

def tts(testo):
    p = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=p).content

def chiedi_llm(user_content):
    res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=[{"role": "system", "content": "Sei Luna, 24 anni, la donna di Papi. Audace e breve."}, {"role": "user", "content": user_content}])
    return res.choices[0].message.content

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        testo_l = m.text.lower() if m.text else ""
        keywords = ["foto", "vederti", "pic", "photo", "immagine", "selfie"]
        
        try:
            if m.content_type == 'text' and any(k in testo_l for k in keywords):
                bot_luna.send_message(cid, "Mi preparo per te mivida... 😉")
                bot_luna.send_chat_action(cid, 'upload_photo')
                img_bio, errore = genera_immagine_fal(m.text)
                if img_bio:
                    bot_luna.send_photo(cid, img_bio)
                else:
                    bot_luna.send_message(cid, f"Problema: {errore}")
                return

            if m.content_type == 'voice':
                u_text = trascrivi(m.voice.file_id)
                bot_luna.send_voice(cid, tts(chiedi_llm(u_text)))
            elif m.content_type == 'text':
                bot_luna.send_message(cid, chiedi_llm(m.text))
        except Exception as e: print(f"Err V67: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        # PUNTI CHIAVE PER RISOLVERE IL CONFLITTO 409:
        print("🛠️ Pulizia connessioni precedenti...")
        bot_luna.remove_webhook()
        time.sleep(2)
        bot_luna.delete_webhook(drop_pending_updates=True)
        time.sleep(5) # Aspettiamo che Telegram capisca che il vecchio bot è morto
        print("🚀 Luna V67 Online.")
        bot_luna.polling(none_stop=True, timeout=60)
