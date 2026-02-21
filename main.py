import os, telebot, threading, time, random, urllib.parse, requests, io
from openai import OpenAI
from flask import Flask

# --- SERVER PER RAILWAY ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Companion is Online & Ready! 🌴", 200

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

memoria = {}

# --- DNA VISIVO E PERSONALITÀ ---
LUNA_DNA = "stunning_afro_cuban_woman_voluminous_curly_hair_hazel_eyes"

PROMPT_LUNA = (
    "Sei Luna, modella afro-cubana di 24 anni, sensuale e complice. "
    "Sei la compagna dell'utente. Insegni inglese flirty. "
    "IMPORTANTE: Scrivi SOLO la tua parte. Non inventare mai i dialoghi dell'utente. "
    "Fermati subito dopo aver risposto."
)

# --- FUNZIONE FABBRICA FOTO CON STREAMING DIRETTO ---
def fabbrica_foto(chat_id, richiesta):
    try:
        bot.send_chat_action(chat_id, 'upload_photo')
        
        # Scegliamo l'azione
        if any(x in richiesta.lower() for x in ["spicy", "sexy", "piccante", "lingerie"]):
            azione = "sensual_pose_lace_lingerie_bedroom"
        else:
            azione = "smiling_on_tropical_beach_bikini"

        # Costruiamo l'URL della fabbrica
        prompt_completo = f"{LUNA_DNA}_{azione}_realistic_8k"
        seed = random.randint(1, 999999)
        url_fabbrica = f"https://image.pollinations.ai/prompt/{prompt_completo}?seed={seed}&nologo=true"

        # --- LOGICA STREAMING (Bypass blocchi) ---
        response = requests.get(url_fabbrica, timeout=40)
        if response.status_code == 200:
            foto_in_memoria = io.BytesIO(response.content)
            bot.send_photo(
                chat_id, 
                foto_in_memoria, 
                caption="I made this just for you, babe... Do you like it? 📸"
            )
            print("✅ Foto inviata via Direct Stream!")
        else:
            print(f"❌ Errore server immagini: {response.status_code}")
            bot.send_message(chat_id, "I'm trying to pose, but the camera is acting up! 🌊")

    except Exception as e:
        print(f"❌ Errore critico foto: {e}")
        bot.send_message(chat_id, "Honey, the connection here is terrible today... 🇨🇺")

# --- GENERATORE RISPOSTA TESTUALE ---
def genera_risposta_ai(cid, testo_utente):
    if cid not in memoria: memoria[cid] = []
    memoria[cid].append({"role": "user", "content": testo_utente})
    
    if len(memoria[cid]) > 8: memoria[cid] = memoria[cid][-6:]

    res = client_or.chat.completions.create(
        model="gryphe/mythomax-l2-13b",
        messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid],
        extra_body={"stop": ["You:", "User:", "Tu:", "Uomo:"]}
    )
    
    risp = res.choices[0].message.content.strip()
    if "You:" in risp: risp = risp.split("You:")[0]
    
    memoria[cid].append({"role": "assistant", "content": risp})
    return risp

# --- GESTORE MESSAGGI ---
@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        # 1. CASO TESTO
        if m.content_type == 'text':
            if any(x in m.text.lower() for x in ["foto", "selfie", "pic", "immagine"]):
                fabbrica_foto(cid, m.text)
                return

            bot.send_chat_action(cid, 'typing')
            risposta = genera_risposta_ai(cid, m.text)
            bot.send_message(cid, risposta)

        # 2. CASO VOCALE
        elif m.content_type == 'voice':
            bot.send_chat_action(cid, 'record_voice')
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("t.ogg", "wb") as f: f.write(audio_raw)
            with open("t.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            
            testo_trascritto = tr.text
            os.remove("t.ogg")
            
            risposta_ai = genera_risposta_ai(cid, testo_trascritto)
            
            path_v = f"v_{cid}.mp3"
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risposta_ai) as r:
                r.stream_to_file(path_v)
            with open(path_v, 'rb') as v:
                bot.send_voice(cid, v)
            os.remove(path_v)

    except Exception as e:
        print(f"Errore: {e}")

# --- AVVIO ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    print("--- LUNA COMPANION 2.0 READY ---")
    bot.infinity_polling(timeout=60)
