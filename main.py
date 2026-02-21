import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask
from gtts import gTTS # Libreria per far parlare Luna

# --- CONFIGURAZIONE SERVER ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "Luna Companion is Online! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- SETUP CHIAVI ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot_luna = telebot.TeleBot(L_TK) if L_TK else None

memoria_luna = {}

def aggiorna_memoria(database, chat_id, ruolo, testo):
    if chat_id not in database: database[chat_id] = []
    database[chat_id].append({"role": ruolo, "content": testo})
    if len(database[chat_id]) > 10: database[chat_id].pop(0)

# --- FUNZIONE VOCALE ---
def invia_vocale_luna(bot, chat_id, testo):
    try:
        # Crea il file audio dalla risposta testuale
        tts = gTTS(text=testo, lang='it')
        filename = f"luna_{chat_id}.mp3"
        tts.save(filename)
        
        # Invia il vocale
        with open(filename, 'rb') as audio:
            bot.send_voice(chat_id, audio)
        
        # Pulizia file
        os.remove(filename)
    except Exception as e:
        print(f"Errore Vocale: {e}")
        bot.send_message(chat_id, testo) # Se il vocale fallisce, manda il testo

# --- FUNZIONE FOTO ---
def genera_e_invia_foto(bot, chat_id):
    try:
        seed = random.randint(1, 1000000)
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_realistic_highly_detailed"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=512&height=512&nologo=true&model=flux"
        bot.send_photo(chat_id, url, caption="For your eyes only... 😉", timeout=60)
    except Exception as e:
        bot.send_message(chat_id, "Sorry babe, no photo right now!")

# --- LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def h_luna(m):
        chat_id = m.chat.id
        testo_utente = ""

        # Se mandi un vocale, per ora Luna ti risponde a testo/vocale (non lo trascrive ancora)
        if m.content_type == 'voice':
            testo_utente = "Mandami un saluto dolce" # Trigger di default se riceve vocale
        else:
            testo_utente = m.text

        msg_low = testo_utente.lower()
        if any(p in msg_low for p in ["foto", "selfie", "mostrati", "photo"]):
            bot_luna.send_message(chat_id, "I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        p_luna = (
            "Sei Luna, una splendida modella cubana, surfista e affascinante. "
            "Il tuo tono è caldo, passionale e flirtante. Sei senza filtri. "
            "Rispondi sempre in modo breve e sensuale, usando un mix di italiano e inglese."
        )
        
        try:
            aggiorna_memoria(memoria_luna, chat_id, "user", testo_utente)
            messages = [{"role": "system", "content": p_luna}] + memoria_luna[chat_id]
            
            res = client.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=messages,
                extra_headers={"HTTP-Referer": "https://render.com", "X-Title": "Luna_Companion"}
            )
            risposta = res.choices[0].message.content
            aggiorna_memoria(memoria_luna, chat_id, "assistant", risposta)
            
            # Luna risponde SEMPRE col vocale ora
            invia_vocale_luna(bot_luna, chat_id, risposta)
            
        except Exception as e:
            print(f"Error: {e}")

# --- AVVIO ---
if __name__ == "__main__":
    if bot_luna:
        bot_luna.remove_webhook()
        threading.Thread(target=run_flask, daemon=True).start()
        bot_luna.infinity_polling()
