import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V76: V64 Core + FAL Engine Active 🚀", 200

# --- CONFIGURAZIONE (Stile V64) ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- NUOVO MOTORE FAL (Integrato nella struttura V64) ---
def genera_immagine_fal(prompt_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {
        "prompt": f"Hyper-realistic photo of Luna, 24yo Italian girl, natural skin, charismatic, {prompt_utente}",
        "image_size": "square", # Mantengo square per stabilità
        "sync_mode": True
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            # Scarico l'immagine per mandarla come file (Metodo V64)
            img_data = requests.get(img_url).content
            bio = io.BytesIO(img_data)
            bio.name = 'luna.jpg'
            return bio
        return None
    except: return None

# --- LOGICA PERSONAGGIO (V64 ORIGINALE) ---
PROMPT_LUNA = "Sei Luna, 24 anni, la donna di Papi. Sei simpatica, audace e complice. Rispondi breve."

def chiedi_llm(user_content):
    res = client_or.chat.completions.create(
        model="google/gemini-2.0-flash-001", 
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

# --- GESTORE MESSAGGI (V64 ORIGINALE) ---
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
                bot_luna.send_message(cid, "Papi, la fotocamera ha fatto cilecca, riprova!")
        else:
            bot_luna.send_message(cid, chiedi_llm(m.text))

# --- AVVIO (V64 ORIGINALE) ---
if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        print("🚀 Luna V76 (V64+FAL) Online.")
        bot_luna.polling(none_stop=True)
