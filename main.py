import os, telebot, threading, time, requests, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V85: Standby 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- GENERAZIONE IMMAGINE (CORRETTA) ---
def genera_foto_luna(prompt_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {"prompt": f"Photo of Luna, 24yo italian girl, natural, {prompt_utente}", "image_size": "square"}
    
    try:
        # 1. Chiediamo l'immagine a FAL
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            # 2. Scarichiamo l'immagine dall'URL ricevuto (QUESTO risolve l'errore dei log)
            img_res = requests.get(img_url)
            if img_res.status_code == 200:
                return img_res.content
        print(f"DEBUG FAL: Status {res.status_code}")
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
    return None

# --- GESTORE ---
if bot_luna:
    @bot_luna.message_handler(func=lambda m: True)
    def handle_messages(m):
        cid = m.chat.id
        text = m.text.lower() if m.text else ""
        
        # Test Foto
        if any(k in text for k in ["foto", "selfie", "vederti"]):
            bot_luna.send_message(cid, "Mi metto in posa... 😉")
            img_data = genera_foto_luna(m.text)
            if img_data:
                bot_luna.send_photo(cid, img_data)
            else:
                bot_luna.send_message(cid, "La fotocamera scotta, riprova!")
        
        # Test Testo (Gemini)
        else:
            try:
                res = client_or.chat.completions.create(
                    model="google/gemini-2.0-flash-001",
                    messages=[{"role": "system", "content": "Sei Luna, 24 anni. Rispondi breve e complice."},
                              {"role": "user", "content": m.text}]
                )
                bot_luna.send_message(cid, res.choices[0].message.content)
            except:
                bot_luna.send_message(cid, "Eccomi papi!")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    if bot_luna:
        # Reset totale connessione
        bot_luna.remove_webhook()
        time.sleep(2)
        print("🚀 Luna V85 Online.")
        bot_luna.infinity_polling(timeout=20)
