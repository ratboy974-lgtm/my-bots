import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

# --- 1. SERVER PER RENDER ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Solo is Live! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- 2. SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() # Se c'è, avrai la voce Nova

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot_luna = telebot.TeleBot(L_TK) if L_TK else None

memoria_luna = {}

def aggiorna_memoria(chat_id, ruolo, testo):
    if chat_id not in memoria_luna: memoria_luna[chat_id] = []
    memoria_luna[chat_id].append({"role": ruolo, "content": testo})
    if len(memoria_luna[chat_id]) > 10: memoria_luna[chat_id].pop(0)

# --- 3. FUNZIONI MULTIMEDIALI ---

def invia_vocale_luna(bot, chat_id, testo):
    filename = f"luna_voice_{chat_id}.mp3"
    try:
        if client_oa:
            # VOCE TOP: Femminile reale (OpenAI Nova)
            response = client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo)
            response.stream_to_file(filename)
        else:
            # VOCE GRATIS: Spagnolo (Molto più femminile dell'italiano di Google)
            tts = gTTS(text=testo, lang='es') 
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
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_warm_sunlight_realistic_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        img_data = requests.get(url, timeout=30).content
        fname = f"luna_pic_{chat_id}.jpg"
        with open(fname, "wb") as f: f.write(img_data)
        with open(fname, "rb") as photo:
            bot.send_photo(chat_id, photo, caption="Do you like my look? 😉", timeout=60)
        os.remove(fname)
    except:
        bot.send_message(chat_id, "I'm a bit shy right now, try again! 🌊")

# --- 4. LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        chat_id = m.chat.id
        testo_u = m.text if m.content_type == 'text' else "Hi Luna!"
        msg_low = testo_u.lower()
        
        if any(p in msg_low for p in ["foto", "selfie", "pic", "photo"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        p_luna = (
            "Sei Luna, una modella cubana afro, surfista e passionale. "
            "Il tuo tono è caldo e flirtante. Rispondi in italiano con un tocco cubano."
        )

        try:
            aggiorna_memoria(chat_id, "user", testo_u)
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": p_luna}] + memoria_luna[chat_id],
                extra_headers={"X-Title": "Luna_Companion"}
            )
            risposta = res.choices[0].message.content
            aggiorna_memoria(chat_id, "assistant", risposta)
            invia_vocale_luna(bot_luna, chat_id, risposta)
        except Exception as e:
            print(f"Errore AI: {e}")

# --- 5. AVVIO SICURO ---
if __name__ == "__main__":
    if bot_luna:
        try:
            bot_luna.remove_webhook()
            time.sleep(1)
            bot_luna.delete_webhook(drop_pending_updates=True)
            time.sleep(3)
        except: pass

        threading.Thread(target=run_flask, daemon=True).start()
        print("--- 🎙️ LUNA SOLO MODE ONLINE ---")
        bot_luna.infinity_polling(timeout=25, long_polling_timeout=10)
