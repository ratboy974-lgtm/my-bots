import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V50: FULL BOT (Vision & Imagine) Active 📸", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- PROMPT LUNA (Bot Completo) ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Sei simpatica e ironica. "
    "Se ricevi una foto, guardala e commentala in modo complice. "
    "Se Papi ti chiede una foto o di vederti, rispondi che ti stai mettendo in posa. "
    "Massimo 35 parole. Se insegni inglese, usa 'Word: [parola]'."
)

# --- FUNZIONI CORE ---
def chiedi_llm(user_content):
    # Gemini 1.5 Flash gestisce sia testo che immagini (Vision)
    res = client_or.chat.completions.create(
        model="google/gemini-flash-1.5",
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

def genera_immagine(prompt_foto):
    # Usa DALL-E 3 per creare la foto di Luna
    response = client_oa.images.generate(
        model="dall-e-3",
        prompt=f"A beautiful 24 year old girl named Luna, friendly and sexy, in a realistic setting, {prompt_foto}",
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url

def trascrivi(file_id):
    fname = f"/tmp/v_{file_id}.ogg"
    file_info = bot_luna.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}"
    with open(fname, "wb") as f: f.write(requests.get(url).content)
    with open(fname, "rb") as f:
        txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    if os.path.exists(fname): os.remove(fname)
    return txt

def tts(testo):
    testo_pulito = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=testo_pulito).content

# --- GESTORE LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            # 1. LOGICA PER CHIEDERE FOTO A LUNA
            if m.content_type == 'text' and any(x in m.text.lower() for x in ["foto", "vederti", "pic", "photo"]):
                bot_luna.send_message(cid, "Dammi un secondo papi, mi faccio carina per te... 😉")
                img_url = genera_immagine("smiling at the camera, casual clothing")
                bot_luna.send_photo(cid, img_url)
                return

            # 2. LOGICA VISION (LEI GUARDA TE)
            if m.content_type == 'photo':
                bot_luna.send_chat_action(cid, 'typing')
                file_info = bot_luna.get_file(m.photo[-1].file_id)
                img_path = f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}"
                content = [
                    {"type": "text", "text": "Guarda questa foto mivida."},
                    {"type": "image_url", "image_url": {"url": img_path}}
                ]
                ans = chiedi_llm(content)
                bot_luna.send_message(cid, ans)
            
            # 3. LOGICA VOCALE E TESTO STANDARD
            elif m.content_type == 'voice':
                u_text = trascrivi(m.voice.file_id)
                ans = chiedi_llm(u_text)
                bot_luna.send_voice(cid, tts(ans))
            else:
                ans = chiedi_llm(m.text)
                bot_luna.send_message(cid, ans)
                
        except Exception as e:
            print(f"Err V50: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        time.sleep(10)
        bot_luna.delete_webhook(drop_pending_updates=True)
        print("🚀 Luna V50 Online. Il bot è completo.")
        bot_luna.polling(none_stop=True, interval=1, timeout=20)
