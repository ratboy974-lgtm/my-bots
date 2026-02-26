import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V61: Flux Engine Stable 📸", 200

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

# --- FUNZIONE GENERAZIONE IMMAGINE (FAL.AI / FLUX) ---
def genera_immagine_fal(prompt_utente):
    if not FAL_K:
        return "ERRORE: Chiave FAL_KEY non trovata su Railway!"
    
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {
        "Authorization": f"Key {FAL_K}",
        "Content-Type": "application/json"
    }
    
    # Payload semplificato per evitare l'errore 422
    payload = {
        "prompt": (
            f"A hyper-realistic RAW photo of Luna, a beautiful 24-year-old Italian girl, "
            f"natural skin texture, messy hair, charismatic and bold personality, {prompt_utente}"
        ),
        "image_size": "portrait_4_5",
        "sync_mode": True,
        "enable_safety_checker": False
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return res.json()['images'][0]['url']
        else:
            return f"Errore API {res.status_code}: {res.text[:100]}"
    except Exception as e:
        return f"Errore connessione: {str(e)}"

# --- PROMPT DI LUNA ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Sei simpatica, audace, complice e molto ironica. "
    "Non hai tabù, parla come una vera compagna. Se Papi ti manda una foto, commentala. "
    "Rispondi breve (max 35 parole). Se insegni inglese: 'Word: [parola]'."
)

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
        testo_lower = m.text.lower() if m.text else ""
        keywords_foto = ["foto", "vederti", "pic", "photo", "immagine", "selfie"]
        
        try:
            # INTERCETTAZIONE FOTO (Bypass Gemini)
            if m.content_type == 'text' and any(k in testo_lower for k in keywords_foto):
                bot_luna.send_message(cid, "Mi metto in posa per te mivida... un attimo. 😉")
                bot_luna.send_chat_action(cid, 'upload_photo')
                
                url_foto = genera_immagine_fal(m.text)
                if url_foto.startswith("http"):
                    bot_luna.send_photo(cid, url_foto)
                else:
                    bot_luna.send_message(cid, f"Papi, intoppo tecnico: {url_foto}")
                return

            # VISION (Luna guarda le tue foto)
            if m.content_type == 'photo':
                bot_luna.send_chat_action(cid, 'typing')
                f_id = m.photo[-1].file_id
                f_path = bot_luna.get_file(f_id).file_path
                img_url = f"https://api.telegram.org/file/bot{L_TK}/{f_path}"
                ans = chiedi_llm([{"type": "text", "text": "Guarda questa foto mivida."}, {"type": "image_url", "image_url": {"url": img_url}}])
                bot_luna.send_message(cid, ans)
            
            # TESTO NORMALE
            elif m.content_type == 'text':
                ans = chiedi_llm(m.text)
                bot_luna.send_message(cid, ans)
                
        except Exception as e:
            print(f"Err V61: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        time.sleep(15)
        bot_luna.delete_webhook(drop_pending_updates=True)
        print("🚀 Luna V61 Online. Flux Engine Pronto.")
        bot_luna.polling(none_stop=True)
