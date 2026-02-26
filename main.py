import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V59: No-Refusal Engine Active 🚀", 200

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

# --- FUNZIONE GENERAZIONE FLUX (FAL.AI) ---
def genera_immagine_fal(prompt_utente):
    if not FAL_K: return "ERRORE: Configura FAL_KEY su Railway!"
    
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    payload = {
        "prompt": f"A hyper-realistic RAW photo of Luna, a beautiful 24-year-old Italian girl, natural skin, charismatic and bold, {prompt_utente}",
        "image_size": "portrait_4_5",
        "enable_safety_checker": False 
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        return res.json()['images'][0]['url'] if res.status_code == 200 else f"Errore API: {res.status_code}"
    except Exception as e: return f"Errore: {str(e)}"

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        # INTERCETTAZIONE IMMEDIATA: Se c'è la parola 'foto' o simili, non chiediamo a Gemini
        testo_lower = m.text.lower() if m.text else ""
        keywords_foto = ["foto", "vederti", "pic", "photo", "immagine", "selfie"]
        
        try:
            if m.content_type == 'text' and any(k in testo_lower for k in keywords_foto):
                bot_luna.send_message(cid, "Mi metto comoda per te mivida... arrivo subito. 😉")
                bot_luna.send_chat_action(cid, 'upload_photo')
                
                url_foto = genera_immagine_fal(m.text)
                if url_foto.startswith("http"):
                    bot_luna.send_photo(cid, url_foto)
                else:
                    bot_luna.send_message(cid, f"Papi, intoppo tecnico: {url_foto}")
                return

            # Per tutto il resto (chiacchiere, vocali, foto inviate da te), usiamo Gemini
            if m.content_type == 'voice':
                bot_luna.send_message(cid, "Ti sento mivida! Ma concentriamoci sulle foto ora.")
            elif m.content_type == 'text':
                res = client_or.chat.completions.create(
                    model="google/gemini-2.0-flash-001",
                    messages=[{"role": "system", "content": "Sei Luna, la donna audace di Papi. Complice e simpatica."}, {"role": "user", "content": m.text}]
                )
                bot_luna.send_message(cid, res.choices[0].message.content)

        except Exception as e: print(f"Err V59: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        time.sleep(15)
        bot_luna.delete_webhook(drop_pending_updates=True)
        print("🚀 Luna V59 Online. Refusal Bypassed.")
        bot_luna.polling(none_stop=True)
