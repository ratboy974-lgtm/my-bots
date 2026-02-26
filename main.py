import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V65: Optimized Quality Active 🚀", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- GENERAZIONE FLUX OTTIMIZZATA (FAL.AI) ---
def genera_immagine_fal(prompt_utente):
    if not FAL_K: return None, "Manca FAL_KEY"
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    
    payload = {
        "prompt": (
            f"Hyper-realistic photo of Luna, 24yo Italian girl, natural, charismatic, {prompt_utente}"
        ),
        "image_size": "square", # QUALITÀ OTTIMIZZATA: Più leggero per Telegram
        "sync_mode": True,
        "enable_safety_checker": False
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            return img_url, None
        return None, f"Errore API {res.status_code}"
    except Exception as e: return None, str(e)

# --- FUNZIONI AUDIO ---
def trascrivi(file_id):
    fname = f"/tmp/v_{file_id}.ogg"
    file_info = bot_luna.get_file(file_id)
    with open(fname, "wb") as f: 
        f.write(requests.get(f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}").content)
    with open(fname, "rb") as f:
        txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    os.remove(fname)
    return txt

def tts(testo):
    p = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=p).content

# --- LOGICA CERVELLO ---
PROMPT_LUNA = "Sei Luna, 24 anni, la donna di Papi. Sei simpatica, audace e complice. Rispondi breve (max 35 parole)."

def chiedi_llm(user_content):
    res = client_or.chat.completions.create(
        model="google/gemini-2.0-flash-001", 
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        testo_l = m.text.lower() if m.text else ""
        keywords_foto = ["foto", "vederti", "pic", "photo", "immagine", "selfie"]
        
        try:
            # 1. Foto
            if m.content_type == 'text' and any(k in testo_l for k in keywords_foto):
                bot_luna.send_message(cid, "Mi preparo per te mivida... 😉")
                bot_luna.send_chat_action(cid, 'upload_photo')
                img_url, errore = genera_immagine_fal(m.text)
                if img_url:
                    bot_luna.send_photo(cid, img_url)
                else:
                    bot_luna.send_message(cid, f"Intopperello: {errore}")
                return

            # 2. Vocali
            if m.content_type == 'voice':
                bot_luna.send_chat_action(cid, 'record_audio')
                u_text = trascrivi(m.voice.file_id)
                ans = chiedi_llm(u_text)
                bot_luna.send_voice(cid, tts(ans))
            
            # 3. Vision
            elif m.content_type == 'photo':
                f_id = m.photo[-1].file_id
                f_path = bot_luna.get_file(f_id).file_path
                img_url = f"https://api.telegram.org/file/bot{L_TK}/{f_path}"
                ans = chiedi_llm([{"type": "text", "text": "Guarda."}, {"type": "image_url", "image_url": {"url": img_url}}])
                bot_luna.send_message(cid, ans)
            
            # 4. Testo
            elif m.content_type == 'text':
                bot_luna.send_message(cid, chiedi_llm(m.text))
                
        except Exception as e: print(f"Err V65: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        time.sleep(15)
        bot_luna.delete_webhook(drop_pending_updates=True)
        bot_luna.polling(none_stop=True)
