import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V77: V64 Core + Anti-Conflict Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- MOTORE FAL (Struttura V64) ---
def genera_immagine_fal(prompt_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {
        "prompt": f"Professional RAW photo of Luna, 24yo Italian girl, natural skin, charismatic, {prompt_utente}",
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
        return None
    except: return None

# --- LOGICA PERSONAGGIO ---
PROMPT_LUNA = "Sei Luna, 24 anni, la donna di Papi. Sei simpatica, audace e complice. Rispondi breve."

def chiedi_llm(user_content):
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001", 
            messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
        )
        return res.choices[0].message.content
    except: return "Eccomi papi!"

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def handle_luna(m):
        cid = m.chat.id
        testo_l = m.text.lower() if m.text else ""
        
        if any(k in testo_l for k in ["foto", "vederti", "pic", "selfie"]):
            bot_luna.send_message(cid, "Mi metto in posa... un attimo! 😉")
            foto = genera_immagine_fal(m.text)
            if foto:
                bot_luna.send_photo(cid, foto)
            else:
                bot_luna.send_message(cid, "Papi, riprova tra un secondo!")
        else:
            bot_luna.send_message(cid, chiedi_llm(m.text))

# --- AVVIO CON PULIZIA PROFONDA ---
if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    if bot_luna:
        print("🛑 Uccido connessioni fantasma...")
        bot_luna.remove_webhook()
        time.sleep(5) # Pausa vitale per resettare Telegram
        print("🚀 Luna V77 Online.")
        # Usiamo infinity_polling per gestire i conflitti di rete automaticamente
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=5)
