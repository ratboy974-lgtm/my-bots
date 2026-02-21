import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

# --- 1. SERVER HEALTH CHECK ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Solo is Online! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

# Client per Testo (OpenRouter)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
# Client per Voce (OpenAI)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot_luna = telebot.TeleBot(L_TK) if L_TK else None

memoria_luna = {}

# --- 3. FUNZIONE FOTO (DOWNLOAD LOCALE) ---
def genera_e_invia_foto(bot, chat_id):
    temp_photo = f"photo_{chat_id}.jpg"
    try:
        seed = random.randint(1, 999999)
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_warm_sunlight_highly_detailed_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(temp_photo, "wb") as f:
                f.write(response.content)
            with open(temp_photo, "rb") as photo:
                bot.send_photo(chat_id, photo, caption="For your eyes only... 😉")
            if os.path.exists(temp_photo): os.remove(temp_photo)
        else:
            bot.send_message(chat_id, "I'm a bit shy right now, babe. Try again! 🌊")
    except Exception as e:
        print(f"Errore Foto: {e}")
        bot.send_message(chat_id, "My camera is acting up! 📸")

# --- 4. FUNZIONE VOCALE (NOVA VOICE) ---
def invia_vocale_luna(bot, chat_id, testo):
    temp_voice = f"voice_{chat_id}.mp3"
    try:
        if client_oa:
            # VOCE FEMMINILE PROFESSIONALE
            response = client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo)
            response.stream_to_file(temp_voice)
        else:
            # BACKUP SE MANCA CHIAVE (Google - potrebbe essere maschile)
            tts = gTTS(text=testo, lang='it')
            tts.save(temp_voice)
        
        with open(temp_voice, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        if os.path.exists(temp_voice): os.remove(temp_voice)
    except Exception as e:
        print(f"Errore Vocale: {e}")
        bot.send_message(chat_id, testo)

# --- 5. LOGICA MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def handle_messages(m):
        chat_id = m.chat.id
        msg_text = m.text
        msg_low = msg_text.lower()
        
        # Trigger Foto
        if any(p in msg_low for p in ["foto", "selfie", "pic", "photo"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        # Risposta AI
        try:
            if chat_id not in memoria_luna: memoria_luna[chat_id] = []
            memoria_luna[chat_id].append({"role": "user", "content": msg_text})
            
            p_luna = "Sei Luna, modella cubana afro, sensuale e calda. Rispondi in italiano con frasi in inglese."
            
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": p_luna}] + memoria_luna[chat_id][-10:]
            )
            risposta = res.choices[0].message.content
            memoria_luna[chat_id].append({"role": "assistant", "content": risposta})
            
            invia_vocale_luna(bot_luna, chat_id, risposta)
        except Exception as e:
            print(f"Errore AI: {e}")

# --- 6. AVVIO ANTI-CONFLITTO 409 ---
if __name__ == "__main__":
    # Avvio Server Health Check
    threading.Thread(target=run_flask, daemon=True).start()
    
    if bot_luna:
        print("--- 🛠️ RESETTING CONNECTION ---")
        try:
            bot_luna.remove_webhook()
            bot_luna.delete_webhook(drop_pending_updates=True)
            time.sleep(3) # Pausa vitale per uccidere sessioni vecchie
        except: pass

        print("--- 🎙️ LUNA ONLINE ---")
        # Infinity polling con parametri di stabilità
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=5)
