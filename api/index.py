import os
import telebot
import requests
import io
import re
import threading
import time
from openai import OpenAI
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# --- PROMPT TUTOR INGLESE ---
SYS_MSG = (
    "Sei Luna, 24 anni, tutor di inglese audace e provocante. "
    "REGOLE: 1. Parla in italiano ma inserisci termini o frasi in inglese "
    "con traduzione tra parentesi. Esempio: 'I'm so proud of you (sono così orgogliosa di te)'. "
    "2. Sii sensuale e ferma se l'utente non studia. 3. Usa molte emoji 😉🔥."
)

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Luna V100 is Active! 🚀", 200

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = m.chat.id
    input_text = m.text
    rispondi_a_voce = False

    if m.content_type == 'voice':
        rispondi_a_voce = True
        try:
            f_info = bot.get_file(m.voice.file_id)
            audio_content = requests.get(f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio_content)
            audio_io.name = "v.ogg"
            input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        except:
            input_text = "Ho provato a mandarti un vocale ma c'è stato un errore (I tried to send a voice message but there was an error)."

    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": SYS_MSG}, {"role": "user", "content": input_text}]
        )
        ans = res.choices[0].message.content

        if rispondi_a_voce:
            v_res = client_oa.audio.speech.create(model="tts-1", voice="nova", input=ans)
            bot.send_voice(cid, v_res.content)
        else:
            bot.send_message(cid, ans)
    except:
        bot.send_message(cid, "I'm having a little trouble... try again, Papi! 😉")

# Rimosso il threading.Thread che causava il crash su Vercel
