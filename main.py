import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V82: Force Clean Active 🚀", 200

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
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {"prompt": f"Professional photo of Luna, 24yo Italian girl, natural skin, {prompt_utente}", "image_size": "square", "sync_mode": True}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_data = requests.get(res.json()['images'][0]['url']).content
            bio = io.BytesIO(img_data)
            bio.name = 'luna.jpg'
            return bio
    except Exception as e: print(f"❌ Errore FAL: {e}")
    return None

# --- LOGICA LLM ---
def chiedi_llm(user_content):
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001", 
            messages=[{"role": "system", "content": "Sei Luna, 24 anni, audace e complice. Rispondi breve."}, {"role": "user", "content": str(user_content)}]
        )
        return res.choices[0].message.content
    except Exception as e: return "Sono qui papi!"

# --- GESTORE ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            testo = m.text.lower() if m.text else ""
            if any(k in testo for k in ["foto", "vederti", "selfie"]):
                bot_luna.send_message(cid, "Mi metto in posa... 😉")
                f = genera_immagine_fal(m.text)
                if f: bot_luna.send_photo(cid, f)
                else: bot_luna.send_message(cid, "Fotocamera ko, riprova!")
                return
            bot_luna.send_message(cid, chiedi_llm(m.text))
        except Exception as e: print(f"❌ Errore: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        print("🧼 Tentativo di rimozione webhook e reset...")
        # Rimuoviamo il webhook e diciamo a Telegram di cancellare i messaggi pendenti
        requests.get(f"https://api.telegram.org/bot{L_TK}/deleteWebhook?drop_pending_updates=true")
        time.sleep(5)
        print("🚀 Luna V82 Online. Vediamo se il fantasma sparisce.")
        bot_luna.infinity_polling(timeout=10, long_polling_timeout=5)
