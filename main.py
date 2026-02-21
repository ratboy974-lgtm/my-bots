import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

# --- 1. SERVER HEALTH CHECK ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Companion is Live! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() # Se vuota, usa gTTS

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot_luna = telebot.TeleBot(L_TK) if L_TK else None

memoria_luna = {}

def aggiorna_memoria(database, chat_id, ruolo, testo):
    if chat_id not in database: database[chat_id] = []
    database[chat_id].append({"role": ruolo, "content": testo})
    if len(database[chat_id]) > 10: database[chat_id].pop(0)

# --- 3. FUNZIONI MULTIMEDIALI ---

def invia_vocale_luna(bot, chat_id, testo):
    filename = f"luna_voice_{chat_id}.mp3"
    try:
        if client_oa:
            # Voce professionale (Nova)
            response = client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo)
            response.stream_to_file(filename)
        else:
            # Voce gratuita (gTTS)
            tts = gTTS(text=testo, lang='it')
            tts.save(filename)
        
        with open(filename, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(filename)
    except Exception as e:
        print(f"Errore vocale: {e}")
        bot.send_message(chat_id, testo)

def genera_e_invia_foto(bot, chat_id):
    try:
        seed = random.randint(1, 1000000)
        # Prompt focalizzato su Luna (Afro-Cubana, Surfer)
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_warm_sunlight_realistic_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        # Download immagine per evitare errori di timeout
        img_data = requests.get(url, timeout=30).content
        with open("luna_pic.jpg", "wb") as f: f.write(img_data)
        with open("luna_pic.jpg", "rb") as photo:
            bot.send_photo(chat_id, photo, caption="For your eyes only... 😉", timeout=60)
        os.remove("luna_pic.jpg")
    except Exception as e:
        print(f"Errore foto: {e}")
        bot.send_message(chat_id, "I'm a bit shy right now, try again in a second! 🌊")

# --- 4. LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        chat_id = m.chat.id
        testo_u = m.text if m.content_type == 'text' else "Mandami un saluto dolce"
        msg_low = testo_u.lower()
        
        if any(p in msg_low for p in ["foto", "selfie", "pic", "photo", "immagine"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        p_luna = (
            "Sei Luna, una modella cubana afro, surfista e molto passionale. "
            "Sei senza filtri, flirtante e calda. Parli italiano ma inserisci "
            "spesso parole o frasi in inglese (con traduzione tra parentesi)."
        )

        try:
            aggiorna_memoria(memoria_luna, chat_id, "user", testo_u)
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": p_luna}] + memoria_luna[chat_id],
                extra_headers={"HTTP-Referer": "https://render.com", "X-Title": "Luna_Companion"}
            )
            risposta = res.choices[0].message.content
            aggiorna_memoria(memoria_luna, chat_id, "assistant", risposta)
            invia_vocale_luna(bot_luna, chat_id, risposta)
        except Exception as e:
            print(f"Errore AI: {e}")

# --- 5. AVVIO AUTOMATICO E RESILIENTE ---
if __name__ == "__main__":
    print("--- 🚀 LUNA IS STARTING ---")
    
    if bot_luna:
        # 1. Pulizia drastica pre-avvio
        try:
            bot_luna.remove_webhook()
            bot_luna.delete_webhook(drop_pending_updates=True)
            print("✅ Webhook rimosso e coda pulita.")
            time.sleep(3) # Pausa vitale: dà tempo a Render di spegnere il vecchio bot
        except Exception as e:
            print(f"⚠️ Nota pulizia: {e}")

        # 2. Avvio Server Health Check
        threading.Thread(target=run_flask, daemon=True).start()
        
        # 3. Avvio Polling con gestione errori intelligente
        print("--- 🎙️ LUNA ONLINE E PRONTA ---")
        
        # infinity_polling con parametri di recupero
        bot_luna.infinity_polling(
            timeout=20, 
            long_polling_timeout=5,
            restart_on_change=True,
            logger_level=40 # Riduce i log inutili, mostra solo errori gravi
        )
