import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V72: Compatibility Active 🚀", 200

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip().replace("'", "").replace('"', "")
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- GENERAZIONE FLUX ---
def genera_immagine_fal(prompt_utente):
    if not FAL_K: return None, "Manca FAL_KEY"
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {"prompt": f"Professional RAW photo of Luna, 24yo Italian girl, natural, {prompt_utente}", "image_size": "square", "sync_mode": True, "enable_safety_checker": False}
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

# --- LOGICA LLM ---
def chiedi_llm(user_content):
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001", 
            messages=[{"role": "system", "content": "Sei Luna, la donna audace di Papi. Rispondi breve (max 150 car)."}, {"role": "user", "content": str(user_content)[:400]}]
        )
        return res.choices[0].message.content[:350]
    except: return "Eccomi papi!"

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        testo_l = m.text.lower() if m.text else ""
        try:
            if m.content_type == 'text' and any(k in testo_l for k in ["foto", "vederti", "selfie"]):
                bot_luna.send_message(cid, "Arrivo subito papi... 😉")
                img_bio, errore = genera_immagine_fal(m.text)
                if img_bio: bot_luna.send_photo(cid, img_bio)
                else: bot_luna.send_message(cid, f"Ouch: {errore}")
            else:
                bot_luna.send_message(cid, chiedi_llm(m.text if m.text else "Ciao"))
        except Exception as e: print(f"Err: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    if bot_luna:
        print("🧹 Pulizia universale...")
        # Metodo compatibile con tutte le versioni di telebot
        bot_luna.remove_webhook()
        time.sleep(2)
        print("🚀 Luna V72 Online.")
        # Usiamo infinity_polling che è più stabile contro i 409
        bot_luna.infinity_polling(timeout=10, long_polling_timeout=5)
