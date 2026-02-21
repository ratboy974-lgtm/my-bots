import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

# --- 1. SERVER PER RENDER ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna & Cox are Online! 🌴🏥", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
C_TK = os.environ.get('TOKEN_COX', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot_luna = telebot.TeleBot(L_TK) if L_TK else None
bot_cox = telebot.TeleBot(C_TK) if C_TK else None

# Memorie separate
memoria_luna = {}
memoria_cox = {}

def aggiorna_memoria(database, chat_id, ruolo, testo):
    if chat_id not in database: database[chat_id] = []
    database[chat_id].append({"role": ruolo, "content": testo})
    if len(database[chat_id]) > 10: database[chat_id].pop(0)

# --- 3. FUNZIONI MULTIMEDIALI ---

def invia_vocale(bot, chat_id, testo, lang='it'):
    filename = f"voice_{chat_id}_{random.randint(1,999)}.mp3"
    try:
        tts = gTTS(text=testo, lang=lang)
        tts.save(filename)
        with open(filename, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(filename)
    except Exception as e:
        bot.send_message(chat_id, testo)

def genera_e_invia_foto(bot, chat_id):
    try:
        seed = random.randint(1, 1000000)
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_realistic_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        img_data = requests.get(url, timeout=30).content
        with open(f"thumb_{chat_id}.jpg", "wb") as f: f.write(img_data)
        with open(f"thumb_{chat_id}.jpg", "rb") as photo:
            bot.send_photo(chat_id, photo, caption="For you... 😉")
        os.remove(f"thumb_{chat_id}.jpg")
    except:
        bot.send_message(chat_id, "I'm a bit shy right now! 🌊")

# --- 4. LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        testo_u = m.text if m.content_type == 'text' else "Hi Luna!"
        if any(p in testo_u.lower() for p in ["foto", "selfie", "pic"]):
            genera_e_invia_foto(bot_luna, m.chat.id)
            return
        
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "system", "content": "Sei Luna, modella cubana afro e sensuale."}] + memoria_luna.get(m.chat.id, []),
            extra_headers={"X-Title": "Luna"}
        )
        risposta = res.choices[0].message.content
        aggiorna_memoria(memoria_luna, m.chat.id, "assistant", risposta)
        invia_vocale(bot_luna, m.chat.id, risposta)

# --- 5. LOGICA COX ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text'])
    def handle_cox(m):
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "system", "content": "Sei il Dr. Cox di Scrubs, acido e sarcastico."}] + memoria_cox.get(m.chat.id, []),
            extra_headers={"X-Title": "Cox"}
        )
        risposta = res.choices[0].message.content
        bot_cox.reply_to(m, risposta)

# --- 6. AVVIO MULTI-THREAD (SOLUZIONE AL CONFLITTO) ---
def start_polling(bot, name):
    print(f"--- 🎙️ {name} sta partendo... ---")
    try:
        bot.remove_webhook()
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
        bot.infinity_polling(timeout=20, long_polling_timeout=5)
    except Exception as e:
        print(f"❌ Errore su {name}: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Avviamo i bot in thread separati per evitare che si blocchino a vicenda
    if bot_luna:
        threading.Thread(target=start_polling, args=(bot_luna, "LUNA"), daemon=True).start()
    
    if bot_cox:
        threading.Thread(target=start_polling, args=(bot_cox, "COX"), daemon=True).start()

    # Mantiene il programma principale in esecuzione
    while True:
        time.sleep(1)
