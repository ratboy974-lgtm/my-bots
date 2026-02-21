import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is Live & Sexy! 🌴", 200

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

memoria_luna = {}

# --- FUNZIONE FOTO ---
def genera_e_invia_foto(bot, chat_id):
    filename = f"luna_pic_{chat_id}.jpg"
    try:
        seed = random.randint(1, 999999)
        # Prompt per Luna
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_warm_sunlight_highly_detailed"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        response = requests.get(url, timeout=30)
        with open(filename, "wb") as f:
            f.write(response.content)
        
        with open(filename, "rb") as photo:
            bot.send_photo(chat_id, photo, caption="Do you like what you see, babe? 😉")
        os.remove(filename)
    except Exception as e:
        bot.send_message(chat_id, "I'm a bit shy right now, try again! 🌊")

# --- FUNZIONE VOCALE ---
def invia_vocale_luna(bot, chat_id, testo):
    filename = f"voice_{chat_id}.mp3"
    try:
        if client_oa:
            # VOCE REALE (OpenAI Nova)
            response = client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo)
            response.stream_to_file(filename)
        else:
            # BACKUP (Google)
            tts = gTTS(text=testo, lang='it')
            tts.save(filename)
        
        with open(filename, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(filename)
    except:
        bot.send_message(chat_id, testo)

# --- LOGICA BOT ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def handle_luna(m):
        chat_id = m.chat.id
        msg = m.text.lower()
        
        # Gestione FOTO
        if any(p in msg for p in ["foto", "selfie", "pic", "photo"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        # Gestione TESTO
        try:
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": "Sei Luna, modella cubana afro, sensuale e senza filtri. Rispondi in italiano/inglese."}] + memoria_luna.get(chat_id, []),
            )
            risposta = res.choices[0].message.content
            invia_vocale_luna(bot_luna, chat_id, risposta)
        except:
            bot_luna.send_message(chat_id, "I'm a bit dizzy, babe. Say it again?")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_luna.remove_webhook()
    bot_luna.delete_webhook(drop_pending_updates=True)
    time.sleep(2)
    print("--- 🎙️ LUNA IS BACK ---")
    bot_luna.infinity_polling()
