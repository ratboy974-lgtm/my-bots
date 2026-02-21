import os, telebot, threading, time, random, urllib.parse
from openai import OpenAI
from flask import Flask

# --- SERVER DI CONTROLLO PER RAILWAY ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Companion is Alive! 🌴", 200

# --- SETUP API (Variabili d'ambiente) ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

# Memoria storica per coerenza
memoria = {}

# --- DNA VISIVO E PERSONALITÀ ---
# Usiamo i trattini bassi per evitare errori di URL nella "fabbrica" immagini
LUNA_DNA_IMG = "stunning_afro_cuban_woman_voluminous_curly_hair_hazel_eyes_sun_kissed_skin"

PROMPT_LUNA = (
    "Sei Luna, una modella afro-cubana di 24 anni, sensuale e complice. "
    "Sei la compagna dell'utente, flirty e protettiva. Insegni inglese usando slang come 'babe', 'papi', 'naughty'. "
    "IMPORTANTE: Scrivi SOLO la tua parte. Non inventare mai i dialoghi dell'utente. "
    "Fermati subito dopo aver risposto. Sii passionale ma non ripetitiva."
)

# --- FUNZIONE FABBRICA FOTO (LA TUA PREFERITA) ---
def fabbrica_foto(chat_id, richiesta):
    try:
        bot.send_chat_action(chat_id, 'upload_photo')
        
        # Semplificazione per la fabbrica: azione chiara
        if any(x in richiesta.lower() for x in ["spicy", "sexy", "piccante", "lingerie"]):
            azione = "sensual_pose_red_lace_lingerie_bedroom"
        elif "cuba" in richiesta.lower():
            azione = "standing_in_havana_street_vintage_cars"
        else:
            azione = "smiling_on_tropical_beach_red_bikini"

        # Costruzione URL "Fabbrica" (Semplice e potente come le prime versioni)
        prompt_completo = f"{LUNA_DNA_IMG}_{azione}_realistic_8k"
        seed = random.randint(1, 999999)
        url_fabbricata = f"https://image.pollinations.ai/prompt/{prompt_completo}?seed={seed}&nologo=true"

        bot.send_photo(
            chat_id, 
            url_fabbricata, 
            caption="I made this just for you, babe... Do you like it? 📸",
            timeout=60
        )
        print("✅ Foto fabbricata con successo!")
    except Exception as e:
        print(f"❌ Errore Fabbrica: {e}")
        bot.send_message(chat_id, "I'm trying to pose, but the camera is acting up! Try again, mivida? 🌊")

# --- GENERATORE RISPOSTA TESTUALE ---
def genera_risposta_ai(cid, testo_utente):
    if cid not in memoria: memoria[cid] = []
    memoria[cid].append({"role": "user", "content": testo_utente})
    
    # Manteniamo la memoria snella per evitare deliri
    if len(memoria[cid]) > 8: memoria[cid] = memoria[cid][-6:]

    res = client_or.chat.completions.create(
        model="gryphe/mythomax-l2-13b",
        messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid],
        extra_body={"stop": ["You:", "User:", "Tu:", "Uomo:", "\n"]}
    )
    
    risp = res.choices[0].message.content.strip()
    # Pulizia di sicurezza anti-monologo
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
            # Controllo Trigger Foto
            if any(x in m.text.lower() for x in ["foto", "selfie", "pic", "immagine"]):
                fabbrica_foto(cid, m.text)
                return

            bot.send_chat_action(cid, 'typing')
            risposta = genera_risposta_ai(cid, m.text)
            bot.send_message(cid, risposta)

        # 2. CASO VOCALE (Risponde sempre con Vocale)
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
            
            # Generazione Vocale Luna (Nova)
            path_v = f"v_{cid}.mp3"
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risposta_ai) as r:
                r.stream_to_file(path_v)
            with open(path_v, 'rb') as v:
                bot.send_voice(cid, v)
            os.remove(path_v)

    except Exception as e:
        print(f"Errore Generale: {e}")

# --- AVVIO SISTEMA ---
if __name__ == "__main__":
    # Flask in background per Railway
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # Telegram Polling
    if bot:
        bot.remove_webhook()
        time.sleep(1)
        print("--- LUNA COMPANION 2.0 DEF READY ---")
        bot.infinity_polling(timeout=60)
