import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V78: Fresh Token Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- MOTORE FOTO (FAL) ---
def genera_immagine_fal(prompt_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {
        "prompt": f"Professional RAW photo of Luna, a beautiful 24yo Italian girl, natural skin, charismatic, {prompt_utente}",
        "image_size": "square",
        "sync_mode": True
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            img_data = requests.get(img_url).content
            bio = io.BytesIO(img_data)
            bio.name = 'luna.jpg'
            return bio
    except: return None

# --- LOGICA LLM ---
def chiedi_llm(user_content):
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001", 
            messages=[
                {"role": "system", "content": "Sei Luna, la donna audace di Papi. Hai 24 anni. Rispondi breve e complice."},
                {"role": "user", "content": user_content}
            ]
        )
        return res.choices[0].message.content
    except: return "Eccomi papi!"

# --- GESTORE ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def handle_luna(m):
        cid = m.chat.id
        t = m.text.lower() if m.text else ""
        if any(k in t for k in ["foto", "vederti", "pic", "selfie"]):
            bot_luna.send_message(cid, "Un attimo che mi sistemo... 😉")
            f = genera_immagine_fal(m.text)
            if f: bot_luna.send_photo(cid, f)
            else: bot_luna.send_message(cid, "La fotocamera scotta, riprova!")
        else:
            bot_luna.send_message(cid, chiedi_llm(m.text))

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        print("🚀 Luna V78 Online con Nuovo Token.")
        bot_luna.infinity_polling(timeout=20)
