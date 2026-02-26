import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V79: Full Power Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- MOTORE FOTO (FAL/FLUX) ---
def genera_immagine_fal(prompt_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {"prompt": f"A beautiful 24yo Italian girl, natural, {prompt_utente}", "image_size": "square", "sync_mode": True}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_data = requests.get(res.json()['images'][0]['url']).content
            bio = io.BytesIO(img_data)
            bio.name = 'luna.jpg'
            return bio
    except: return None

# --- AUDIO (TRASCRIZIONE E VOCE) ---
def trascrivi(file_id):
    f_info = bot_luna.get_file(file_id)
    f_data = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
    fname = f"/tmp/{file_id}.ogg"
    with open(fname, "wb") as f: f.write(f_data)
    with open(fname, "rb") as f:
        txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    os.remove(fname)
    return txt

def tts(testo):
    p = re.sub(r'Word: \w+', '', testo).strip()[:300]
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=p).content

# --- LOGICA LLM ---
def chiedi_llm(user_content):
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001", 
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve (max 30 parole)."}, {"role": "user", "content": str(user_content)}]
        )
        return res.choices[0].message.content
    except: return "Sono qui papi!"

# --- GESTORE ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            # GESTIONE FOTO
            if m.content_type == 'text' and any(k in m.text.lower() for k in ["foto", "vederti", "pic"]):
                bot_luna.send_message(cid, "Mi metto in posa... un attimo! 😉")
                f = genera_immagine_fal(m.text)
                if f: bot_luna.send_photo(cid, f)
                return

            # GESTIONE VOCALI
            if m.content_type == 'voice':
                bot_luna.send_chat_action(cid, 'record_audio')
                txt = trascrivi(m.voice.file_id)
                ans = chiedi_llm(txt)
                bot_luna.send_voice(cid, tts(ans))
            
            # GESTIONE VISIONE FOTO
            elif m.content_type == 'photo':
                f_id = m.photo[-1].file_id
                f_path = bot_luna.get_file(f_id).file_path
                i_url = f"https://api.telegram.org/file/bot{L_TK}/{f_path}"
                ans = chiedi_llm([{"type": "text", "text": "Guarda."}, {"type": "image_url", "image_url": {"url": i_url}}])
                bot_luna.send_message(cid, ans)
            
            # TESTO
            elif m.content_type == 'text':
                bot_luna.send_message(cid, chiedi_llm(m.text))
        except Exception as e: print(f"Err: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        # PULIZIA AGGRESSIVA
        bot_luna.remove_webhook()
        time.sleep(3)
        print("🚀 Luna V79 Online. Full Power.")
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=5)
