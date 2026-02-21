import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna Live", 200

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

# --- FUNZIONE FOTO ---
def genera_e_invia_foto(bot, chat_id):
    try:
        seed = random.randint(1, 999999)
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_realistic_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        print(f"📸 Generazione foto per {chat_id}...")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            bot.send_photo(chat_id, response.content, caption="For you... 😉")
            print("✅ Foto inviata!")
        else:
            bot.send_message(chat_id, "I'm a bit shy right now... 🌊")
    except Exception as e:
        print(f"❌ Errore Foto: {e}")
        bot.send_message(chat_id, "Camera error, babe!")

# --- FUNZIONE VOCALE ---
def invia_vocale(bot, chat_id, testo):
    filename = f"v_{chat_id}.mp3"
    try:
        if client_oa:
            response = client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo)
            response.stream_to_file(filename)
            with open(filename, 'rb') as audio:
                bot.send_voice(chat_id, audio)
            os.remove(filename)
        else:
            bot.send_message(chat_id, testo)
    except Exception as e:
        print(f"❌ Errore Vocale: {e}")
        bot.send_message(chat_id, testo)

# --- LOGICA BOT ---
if bot_luna:
    @bot_luna.message_handler(func=lambda m: True)
    def handle_all(m):
        chat_id = m.chat.id
        print(f"📩 Messaggio ricevuto: {m.text}")
        
        if any(p in m.text.lower() for p in ["foto", "selfie", "pic"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        try:
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": "Sei Luna, modella cubana afro sensuale."}] + [{"role": "user", "content": m.text}],
            )
            risposta = res.choices[0].message.content
            invia_vocale(bot_luna, chat_id, risposta)
        except Exception as e:
            print(f"❌ Errore AI: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    # PULIZIA PRE-AVVIO
    if bot_luna:
        print("--- 🚀 LUNA RESTARTING ---")
        bot_luna.remove_webhook()
        time.sleep(2)
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=5)
