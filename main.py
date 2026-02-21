import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask

# --- 1. SERVER PER RENDER ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna High Quality is Live! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot_luna = telebot.TeleBot(L_TK) if L_TK else None

memoria_luna = {}

# --- 3. FUNZIONE FOTO (METODO DOWNLOAD SICURO) ---

def genera_e_invia_foto(bot, chat_id):
    filename = f"luna_pic_{chat_id}.jpg"
    try:
        seed = random.randint(1, 1000000)
        # Prompt ottimizzato per evitare errori di generazione
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_warm_sunlight_highly_detailed_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        # Scarichiamo l'immagine sul server
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            
            # Inviamo il file fisico invece del link
            with open(filename, "rb") as photo:
                bot.send_photo(chat_id, photo, caption="Do you like it, babe? 😉", timeout=60)
            
            os.remove(filename) # Pulizia
        else:
            bot.send_message(chat_id, "I'm a bit shy right now, try again in a second! 🌊")
    except Exception as e:
        print(f"Errore foto: {e}")
        bot.send_message(chat_id, "Sorry, my camera is acting up! 📸")

# --- 4. FUNZIONE VOCALE NOVA ---

def invia_vocale_luna(bot, chat_id, testo):
    filename = f"luna_voice_{chat_id}.mp3"
    try:
        if client_oa:
            response = client_oa.audio.speech.create(model="tts-1", voice="nova", input=testo)
            response.stream_to_file(filename)
            with open(filename, 'rb') as audio:
                bot.send_voice(chat_id, audio)
            os.remove(filename)
        else:
            bot.send_message(chat_id, "Babe, I need my OpenAI key for my real voice! 🎙️\n\n" + testo)
    except Exception as e:
        bot.send_message(chat_id, testo)

# --- 5. LOGICA MESSAGGI ---

if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def handle_luna(m):
        chat_id = m.chat.id
        msg_low = m.text.lower()
        
        # Trigger per le foto
        if any(p in msg_low for p in ["foto", "selfie", "pic", "photo", "immagine"]):
            bot_luna.send_message(chat_id, "Wait, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, chat_id)
            return

        try:
            # Memoria
            if chat_id not in memoria_luna: memoria_luna[chat_id] = []
            memoria_luna[chat_id].append({"role": "user", "content": m.text})
            if len(memoria_luna[chat_id]) > 10: memoria_luna[chat_id].pop(0)

            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": "Sei Luna, modella cubana sensuale. Rispondi in italiano/inglese."}] + memoria_luna[chat_id],
            )
            risposta = res.choices[0].message.content
            memoria_luna[chat_id].append({"role": "assistant", "content": risposta})
            
            invia_vocale_luna(bot_luna, chat_id, risposta)
        except Exception as e:
            print(f"Errore AI: {e}")

# --- 6. AVVIO ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_luna.remove_webhook()
    bot_luna.delete_webhook(drop_pending_updates=True)
    time.sleep(2)
    print("--- 🎙️ LUNA ONLINE ---")
    bot_luna.infinity_polling()
