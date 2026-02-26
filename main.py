import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V57: Unfiltered Flux Engine Active 📸🔥", 200

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
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {
        "Authorization": f"Key {FAL_K}",
        "Content-Type": "application/json"
    }
    # Prompt ottimizzato per fotorealismo umano e libertà totale
    payload = {
        "prompt": (
            f"A hyper-realistic RAW photo of Luna, a beautiful 24-year-old Italian girl with natural skin texture, "
            f"messy hair, expressive eyes, charismatic and bold personality. "
            f"Cinematic lighting, candid shot, {prompt_utente}"
        ),
        "image_size": "portrait_4_5",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "enable_safety_checker": False # DISATTIVIAMO I FILTRI
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return res.json()['images'][0]['url']
        else:
            print(f"Errore Fal.ai: {res.text}")
            return None
    except Exception as e:
        print(f"Eccezione Fal.ai: {e}")
        return None

# --- PROMPT DI LUNA ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Sei simpatica, audace, complice e molto ironica. "
    "Non hai tabù, parla come una vera compagna. Se Papi ti manda una foto, commentala. "
    "Se ti chiede una foto o di vederti, dì che ti stai mettendo a tuo agio. "
    "Rispondi breve (max 35 parole). Se insegni inglese: 'Word: [parola]'."
)

def chiedi_llm(user_content):
    res = client_or.chat.completions.create(
        model="google/gemini-2.0-flash-001", 
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

# --- ALTRE FUNZIONI (TTS, TRASCRIZIONE) ---
def trascrivi(file_id):
    fname = f"/tmp/v_{file_id}.ogg"
    file_info = bot_luna.get_file(file_id)
    with open(fname, "wb") as f: 
        f.write(requests.get(f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}").content)
    with open(fname, "rb") as f:
        txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    os.remove(fname)
    return txt

def tts(testo):
    p = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=p).content

# --- GESTORE MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            # RICHIESTA FOTO
            if m.content_type == 'text' and any(x in m.text.lower() for x in ["foto", "vederti", "pic", "photo", "immagine"]):
                bot_luna.send_message(cid, "Mi metto comoda per te mivida... un attimo. 😉")
                bot_luna.send_chat_action(cid, 'upload_photo')
                img_url = genera_immagine_fal(m.text)
                if img_url:
                    bot_luna.send_photo(cid, img_url)
                else:
                    bot_luna.send_message(cid, "Scusa papi, la connessione con la mia macchina fotografica è saltata. Riprova?")
                return

            # VISION
            if m.content_type == 'photo':
                bot_luna.send_chat_action(cid, 'typing')
                f_id = m.photo[-1].file_id
                f_path = bot_luna.get_file(f_id).file_path
                img_url = f"https://api.telegram.org/file/bot{L_TK}/{f_path}"
                ans = chiedi_llm([{"type": "text", "text": "Commenta questa foto."}, {"type": "image_url", "image_url": {"url": img_url}}])
                bot_luna.send_message(cid, ans)
            
            # VOCALE
            elif m.content_type == 'voice':
                ans = chiedi_llm(trascrivi(m.voice.file_id))
                bot_luna.send_voice(cid, tts(ans))
            
            # TESTO
            else:
                ans = chiedi_llm(m.text)
                bot_luna.send_message(cid, ans)
                
        except Exception as e:
            print(f"Err V57: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        time.sleep(20) # Reset per evitare conflitti
        bot_luna.delete_webhook(drop_pending_updates=True)
        print("🚀 Luna V57 Online. Motore Flux Unfiltered caricato.")
        bot_luna.polling(none_stop=True, interval=2, timeout=40)
