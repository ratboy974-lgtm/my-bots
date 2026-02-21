import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is Live! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot_luna = telebot.TeleBot(L_TK) if L_TK else None

# --- FUNZIONE FOTO (URL DIRETTO) ---
def genera_e_invia_foto(bot, chat_id):
    try:
        seed = random.randint(1, 999999)
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_warm_sunlight_realistic_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        # Invio diretto tramite URL (più veloce su Render)
        bot.send_photo(chat_id, url, caption="Do you like it, babe? 😉", timeout=60)
        print(f"✅ Foto inviata a {chat_id}")
    except Exception as e:
        print(f"❌ Errore Foto: {e}")
        bot.send_message(chat_id, "I'm a bit shy right now, try again! 🌊")

# --- FUNZIONE VOCALE (FIX PER OPENAI 1.0+) ---
def invia_vocale(bot, chat_id, testo):
    temp_voice = f"v_{chat_id}.mp3"
    try:
        if client_oa:
            # Nuovo metodo per salvare il file senza DeprecationWarning
            with client_oa.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice="nova",
                input=testo
            ) as response:
                response.stream_to_file(temp_voice)
            
            with open(temp_voice, 'rb') as audio:
                bot.send_voice(chat_id, audio)
            if os.path.exists(temp_voice): os.remove(temp_voice)
        else:
            bot.send_message(chat_id, testo)
    except Exception as e:
        print(f"❌ Errore Vocale: {e}")
        bot.send_message(chat_id, testo)

# --- LOGICA MESSAGGI ---
if bot_luna:
    @bot_luna.message_handler(func=lambda m: True)
    def handle_all(m):
        chat_id = m.chat.id
        msg_text = m.text if m.text else ""
        print(f"📩 Ricevuto: {msg_text}")
        
        if any(p in msg_text.lower() for p in ["foto", "selfie", "pic", "photo"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        try:
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": "Sei Luna, modella cubana sensuale."}] + [{"role": "user", "content": msg_text}],
            )
            risposta = res.choices[0].message.content
            invia_vocale(bot_luna, chat_id, risposta)
        except Exception as e:
            print(f"❌ Errore AI: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    if bot_luna:
        # Reset connessione
        bot_luna.remove_webhook()
        time.sleep(1)
        bot_luna.delete_webhook(drop_pending_updates=True)
        print("--- 🎙️ LUNA ONLINE ---")
        bot_luna.infinity_polling(timeout=30, long_polling_timeout=10)
