import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS

# --- 1. SERVER PER RENDER (Health Check) ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna Companion Active! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. SETUP API E BOT ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

# Configurazione OpenRouter (Senza filtri)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OR_K,
)

bot_luna = telebot.TeleBot(L_TK) if L_TK else None
memoria_luna = {}

def aggiorna_memoria(database, chat_id, ruolo, testo):
    if chat_id not in database: database[chat_id] = []
    database[chat_id].append({"role": ruolo, "content": testo})
    if len(database[chat_id]) > 10: database[chat_id].pop(0)

# --- 3. FUNZIONI MULTIMEDIALI ---

def invia_vocale_luna(bot, chat_id, testo):
    """Trasforma il testo in un messaggio vocale di Luna"""
    try:
        tts = gTTS(text=testo, lang='it')
        filename = f"voice_{chat_id}.mp3"
        tts.save(filename)
        with open(filename, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        os.remove(filename)
    except Exception as e:
        print(f"Errore Vocale: {e}")
        bot.send_message(chat_id, testo)

def genera_e_invia_foto(bot, chat_id):
    """Genera e invia foto istantanea di Luna"""
    try:
        seed = random.randint(1, 1000000)
        # Prompt per Luna: Cubana, Afro, Surfista, Bikini
        prompt = "stunning_afro_cuban_model_surfer_bikini_beach_sunlight_realistic_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true&model=flux"
        
        bot.send_photo(chat_id, url, caption="Do you like my look? 😉 (Ti piace come sto?)", timeout=60)
    except Exception as e:
        print(f"Errore foto: {e}")
        bot.send_message(chat_id, "Sorry babe, no photo right now! (Scusa tesoro, niente foto ora!)")

# --- 4. LOGICA DI RISPOSTA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        chat_id = m.chat.id
        
        # Se riceve un vocale, lei risponde come se avesse sentito
        testo_u = m.text if m.content_type == 'text' else "Mandami un saluto dolce"
        msg_low = testo_u.lower()
        
        # TRIGGER FOTO
        if any(p in msg_low for p in ["foto", "selfie", "mostrati", "photo", "pic"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        # PERSONALITÀ LUNA
        p_luna = (
            "Sei Luna, una modella cubana afro, surfista, passionale e senza filtri. "
            "Il tuo tono è caldo e sensuale. Rispondi sempre in un mix di italiano e inglese."
        )

        try:
            aggiorna_memoria(memoria_luna, chat_id, "user", testo_u)
            messages = [{"role": "system", "content": p_luna}] + memoria_luna[chat_id]
            
            res = client.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=messages,
                extra_headers={"HTTP-Referer": "https://render.com", "X-Title": "Luna_Companion"}
            )
            risposta = res.choices[0].message.content
            aggiorna_memoria(memoria_luna, chat_id, "assistant", risposta)
            
            # Luna risponde sempre con il vocale
            invia_vocale_luna(bot_luna, chat_id, risposta)
            
        except Exception as e:
            print(f"Errore AI: {e}")

# --- 5. AVVIO SICURO (ANTI-409 CONFLICT) ---
if __name__ == "__main__":
    print("--- 🚀 LUNA COMPANION IN PARTENZA ---")
    
    if bot_luna:
        try:
            # Pulizia preventiva dei webhook e messaggi pendenti
            bot_luna.remove_webhook()
            bot_luna.delete_webhook(drop_pending_updates=True)
            time.sleep(2) # Pausa di sicurezza per liberare il token
        except: pass

        # Avvio Server Health Check
        threading.Thread(target=run_flask, daemon=True).start()
        
        # Avvio Bot
        print("--- 🎙️ Luna è pronta e senza filtri! ---")
        bot_luna.infinity_polling(timeout=20, long_polling_timeout=5)
