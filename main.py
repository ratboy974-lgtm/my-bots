import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

# --- SERVER HEALTH CHECK ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Companion Active! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 1. SETUP API E BOT ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() # Opzionale per voce Nova

# Client per Testo (OpenRouter - Uncensored)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)

# Client per Voce (OpenAI - Per voce femminile 'Nova')
client_oa = OpenAI(api_key=OA_K) if OA_K else None

bot_luna = telebot.TeleBot(L_TK) if L_TK else None
memoria_luna = {}

def aggiorna_memoria(database, chat_id, ruolo, testo):
    if chat_id not in database: database[chat_id] = []
    database[chat_id].append({"role": ruolo, "content": testo})
    if len(database[chat_id]) > 10: database[chat_id].pop(0)

# --- 2. FUNZIONI MULTIMEDIALI ---

def invia_vocale_luna(bot, chat_id, testo):
    """Genera voce femminile"""
    filename = f"luna_voice_{chat_id}.mp3"
    try:
        if client_oa:
            # VOCE TOP: Femminile, naturale (OpenAI Nova)
            response = client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo)
            response.stream_to_file(filename)
        else:
            # VOCE BASE: gTTS (Gratis) - Usiamo 'en' o 'es' per un tono più femminile dell'italiano
            tts = gTTS(text=testo, lang='it') 
            tts.save(filename)
        
        with open(filename, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(filename)
    except Exception as e:
        bot.send_message(chat_id, testo)

def genera_e_invia_foto(bot, chat_id):
    """Genera foto con Pollinations (Gratis & Uncensored)"""
    try:
        seed = random.randint(1, 1000000)
        prompt = "stunning_afro_cuban_model_surfer_bikini_beach_sunlight_highly_detailed_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true&model=flux"
        
        # Download e invio
        img_data = requests.get(url, timeout=30).content
        with open("luna_pic.jpg", "wb") as f: f.write(img_data)
        with open("luna_pic.jpg", "rb") as photo:
            bot.send_photo(chat_id, photo, caption="Do you like it, babe? 😉", timeout=60)
        os.remove("luna_pic.jpg")
    except Exception as e:
        bot.send_message(chat_id, "I'm a bit shy right now, try again! 🌊")

# --- 3. LOGICA BOT ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        chat_id = m.chat.id
        testo_u = m.text if m.content_type == 'text' else "Mandami un saluto sexy"
        
        if any(p in testo_u.lower() for p in ["foto", "selfie", "pic", "photo"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        p_luna = (
            "Sei Luna, una modella cubana afro, surfista, passionale e senza filtri. "
            "Il tuo tono è caldo, flirtante e sensuale. Rispondi in italiano con frasi in inglese."
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
            print(f"Errore: {e}")

# --- 4. AVVIO ANTI-CONFLITTO ---
if __name__ == "__main__":
    if bot_luna:
        bot_luna.remove_webhook()
        bot_luna.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
        threading.Thread(target=run_flask, daemon=True).start()
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=5)
