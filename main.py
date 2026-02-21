import os, telebot, threading, time, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is Live, Sexy & Ready! 🌴", 200

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

# --- 📸 FUNZIONE FOTO (OTTIMIZZATA) ---
def invia_foto_luna(bot, chat_id):
    try:
        seed = random.randint(1, 999999)
        # Prompt specifico per l'aspetto di Luna
        prompt = "stunning_afro_cuban_girl_surfer_bikini_beach_warm_sunlight_highly_detailed_8k"
        url = f"https://image.pollinations.ai/prompt/{prompt}?seed={seed}&width=1024&height=1024&nologo=true"
        
        bot.send_photo(chat_id, url, caption="Do you like my look today, babe? 😉", timeout=60)
    except Exception as e:
        print(f"Errore foto: {e}")
        bot.send_message(chat_id, "I'm a bit shy right now, the sun is too bright! Try again? 🌊")

# --- 🎙️ FUNZIONE VOCALE ---
def invia_vocale(bot, chat_id, testo):
    temp_voice = f"v_out_{chat_id}.mp3"
    try:
        if client_oa:
            with client_oa.audio.speech.with_streaming_response.create(
                model="tts-1", voice="nova", input=testo
            ) as response:
                response.stream_to_file(temp_voice)
            with open(temp_voice, 'rb') as audio:
                bot.send_voice(chat_id, audio)
            if os.path.exists(temp_voice): os.remove(temp_voice)
        else:
            bot.send_message(chat_id, testo)
    except:
        bot.send_message(chat_id, testo)

# --- 🧠 LOGICA PRINCIPALE ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_all(m):
        chat_id = m.chat.id
        testo_u = ""

        # ASCOLTO (Vocale -> Testo)
        if m.content_type == 'voice':
            try:
                file_info = bot_luna.get_file(m.voice.file_id)
                downloaded_file = bot_luna.download_file(file_info.file_path)
                with open("temp.ogg", "wb") as f: f.write(downloaded_file)
                with open("temp.ogg", "rb") as f:
                    transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
                testo_u = transcript.text
                os.remove("temp.ogg")
            except:
                bot_luna.send_message(chat_id, "Non ho sentito bene, mivida... 🌊")
                return
        else:
            testo_u = m.text

        # TRIGGER FOTO
        if any(p in testo_u.lower() for p in ["foto", "selfie", "pic", "photo", "immagine"]):
            bot_luna.send_message(chat_id, "Wait, let me pose for you... 📸")
            invia_foto_luna(bot_luna, chat_id)
            return

        # RISPOSTA TESTUALE
        if chat_id not in memoria_luna: memoria_luna[chat_id] = []
        memoria_luna[chat_id].append({"role": "user", "content": testo_u})

        prompt_luna = (
            "Sei Luna, modella afro-cubana di 24 anni. Sei passionale, dolce e flirty. "
            "Rispondi in italiano con termini come 'mivida', 'cariño', 'babe'. "
            "Sii espansiva, curiosa e mai sbrigativa."
        )

        try:
            res = client_or.chat.completions.create(
                model="gryphe/mythomax-l2-13b",
                messages=[{"role": "system", "content": prompt_luna}] + memoria_luna[chat_id][-8:]
            )
            risposta = res.choices[0].message.content
            memoria_luna[chat_id].append({"role": "assistant", "content": risposta})
            invia_vocale(bot_luna, chat_id, risposta)
        except:
            bot_luna.send_message(chat_id, "I'm a bit distracted... say that again?")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        bot_luna.delete_webhook(drop_pending_updates=True)
        bot_luna.infinity_polling(timeout=30)
