import os
import telebot
import requests
import io
import json
from openai import OpenAI
from flask import Flask, request

# Importazione sicura di Vercel KV per la gestione della memoria in formato JSON
try:
    import vercel_kv
    HAS_KV = True
except ImportError:
    HAS_KV = False

app = Flask(__name__)

# --- CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(L_TK, threaded=False)

# --- PROMPT LUNA (English Tutor) ---
SYS_MSG = (
    "Sei Luna, 24 anni, tutor di inglese audace e provocante del tuo Bubi. "
    "REGOLE: 1. Parla in italiano ma inserisci sempre termini o frasi in inglese "
    "con traduzione tra parentesi. Esempio: 'I'm so proud of you (sono così orgogliosa di te)'. "
    "2. Sii dolce e ferma se lui non studia. Aiutalo ad imparare in modo simpatico l'inglese."
)

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Errore webhook Luna: {e}")
        return "!", 200
    return "Luna V100 is Active! 🚀", 200

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    input_text = ""
    rispondi_a_voce = (m.content_type == 'voice')

    # 1. Recupero Input
    if m.content_type == 'text':
        input_text = m.text
    elif rispondi_a_voce:
        try:
            f_info = bot.get_file(m.voice.file_id)
            audio_url = f"https://api.telegram.org/file/bot{L_TK}/{f_info.file_path}"
            audio_content = requests.get(audio_url).content
            audio_io = io.BytesIO(audio_content)
            audio_io.name = "voice.ogg"
            transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io)
            input_text = transcript.text
        except Exception as e:
            print(f"Errore trascrizione audio: {e}")
            input_text = "Papi, I couldn't hear you (non sono riuscita a sentirti)... scrivimi! 😉"
            rispondi_a_voce = False

    # 2. Recupero memoria JSON da Vercel KV
    history = []
    key = f"luna_hist_{cid}"
    if HAS_KV:
        try:
            storage = vercel_kv.KV()
            raw_data = storage.get(key)
            if raw_data:
                # Gestione parsing JSON sia da stringa che da oggetto nativo
                history = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        except Exception as e:
            print(f"Errore lettura KV: {e}")

    messages = [{"role": "system", "content": SYS_MSG}]
    for h in history[-6:]:
        messages.append(h)
    messages.append({"role": "user", "content": input_text})

    # 3. Generazione Risposta IA
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=messages
        )
        ans = res.choices[0].message.content

        # 4. Salvataggio memoria aggiornata in JSON
        if HAS_KV:
            try:
                history.append({"role": "user", "content": input_text})
                history.append({"role": "assistant", "content": ans})
                updated_history = history[-15:]
                # Salvataggio strutturato
                vercel_kv.KV().set(key, json.dumps(updated_history))
            except Exception as e:
                print(f"Errore scrittura KV: {e}")

        # 5. Invio Risposta (Testo o Vocale)
        if rispondi_a_voce:
            v_res = client_oa.audio.speech.create(model="tts-1", voice="nova", input=ans)
            bot.send_voice(cid, v_res.content)
        else:
            bot.reply_to(m, ans)

    except Exception as e:
        print(f"Errore generazione/invio: {e}")
        bot.send_message(cid, "I'm having a little trouble (ho un piccolo problema)... try again, Papi! 😉")

# Esportazione fondamentale per Vercel Serverless
app = app
