import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

# --- 1. SERVER HEALTH CHECK ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Solo Test is Live! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. SETUP API ---
# Prendi solo il token di Luna
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
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
        # Usiamo gTTS per il test (gratis e veloce)
        tts = gTTS(text=testo, lang='it')
        tts.save(filename)
        with open(filename, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(filename)
    except Exception as e:
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
            bot.send_photo(chat_id, photo, caption="Do you like it, babe? 😉", timeout=60)
        os.remove(fname)
    except Exception as e:
        bot.send_message(chat_id, "I'm a bit shy right now, try again! 🌊")

# --- 4. LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        chat_id = m.chat.id
        testo_u = m.text if m.content_type == 'text' else "Ciao Luna!"
        msg_low = testo_u.lower()
        
        # Trigger Foto
        if any(p in msg_low for p in ["foto", "selfie", "pic", "photo"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        # Prompt Personalità
        p_luna = (
            "Sei Luna, una modella cubana afro, surfista e passionale. "
            "Sei senza filtri e flirtante. Rispondi in italiano con frasi in inglese."
        )

        try:
            aggiorna_memoria(memoria_luna, chat_id, "user", testo_u)
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": p_luna}] + memoria_luna[chat_id],
                extra_headers={"X-Title": "Luna_Companion"}
            )
            risposta = res.choices[0].message.content
            aggiorna_memoria(memoria_luna, chat_id, "assistant", risposta)
            invia_vocale_luna(bot_luna, chat_id, risposta)
        except Exception as e:
            print(f"Errore: {e}")

# --- 5. AVVIO SINGOLO (PROVA DEL NOVE) ---
if __name__ == "__main__":
    print("--- 🚀 STARTING LUNA SOLO TEST ---")
    
    if bot_luna:
        try:
            # RESET TOTALE
            bot_luna.remove_webhook()
            time.sleep(1)
            bot_luna.delete_webhook(drop_pending_updates=True)
            print("✅ Connessione pulita.")
            time.sleep(3) # Pausa di sicurezza
        except: pass

        threading.Thread(target=run_flask, daemon=True).start()
        
        print("--- 🎙️ LUNA IS ONLINE (SOLO MODE) ---")
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=5)
