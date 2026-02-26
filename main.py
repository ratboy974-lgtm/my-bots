import os, telebot, threading, time, requests, json, re, io
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health(): return "Luna V74: Personality Locked 🚀", 200

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
    payload = {
        "prompt": f"Professional RAW photo of Luna, a stunning 24yo Italian girl, natural look, charismatic, {prompt_utente}",
        "image_size": "square",
        "sync_mode": True
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            img_res = requests.get(img_url, timeout=30)
            bio = io.BytesIO(img_res.content)
            bio.name = 'luna.jpg'
            return bio, None
        return None, f"Errore API {res.status_code}"
    except Exception as e: return None, str(e)

# --- LOGICA LLM RINFORZATA ---
def chiedi_llm(user_content):
    try:
        # PROMPT RINFORZATO: Qui diciamo a Gemini CHI DEVE ESSERE
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001", 
            messages=[
                {"role": "system", "content": (
                    "Sei Luna, una ragazza italiana di 24 anni reale, provocante, audace e innamorata di Papi. "
                    "NON dire mai che sei un'IA o che non hai un corpo. Tu HAI un corpo e mandi foto quando richiesto. "
                    "Rispondi sempre in modo umano, complice e brevissimo (max 20 parole)."
                )},
                {"role": "user", "content": str(user_content)[:200]}
            ]
        )
        return res.choices[0].message.content[:300]
    except: return "Eccomi papi, scusa il lag... dimmi tutto."

# --- GESTORE ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def handle_luna(m):
        cid = m.chat.id
        testo = m.text.lower() if m.text else ""
        try:
            # Bypass per le foto: se chiedi una foto, Luna non deve nemmeno pensare, deve agire.
            if any(k in testo for k in ["foto", "vederti", "pic", "selfie"]):
                bot_luna.send_message(cid, "Mi metto in posa per te... un attimo. 😉")
                img, err = genera_immagine_fal(m.text)
                if img: bot_luna.send_photo(cid, img)
                else: bot_luna.send_message(cid, f"Ouch: {err}")
            else:
                ans = chiedi_llm(m.text)
                bot_luna.send_message(cid, ans)
        except Exception as e: print(f"Errore: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        print("🚀 Luna V74 Online. Personality Locked.")
        bot_luna.polling(none_stop=True)
