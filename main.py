import os, telebot, threading, time, requests
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna & Cox V35: Active 🔥", 200

def clean_token(token_name):
    t = os.environ.get(token_name, "").strip()
    return t.replace("'", "").replace('"', "")

# --- CONFIGURAZIONE ---
L_TK = clean_token('TOKEN_LUNA')
C_TK = clean_token('TOKEN_COX')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

# --- INIZIALIZZAZIONE BOT ---
bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None
bot_cox  = telebot.TeleBot(C_TK) if ":" in C_TK else None

# --- PROMPTS ---
LUNA_DNA   = "stunning 24yo woman, long dark hair, tanned skin, hazel eyes, elegant but sensual, photorealistic, high quality portrait"
PROMPT_LUNA = "Tu sei Luna, 24 anni. Sei la donna di Papi. Insegnali inglese con stile sexy."
PROMPT_COX  = "Sei il Dottor Perry Cox. Sei un genio veterinario brutale e acido. Usa nomignoli femminili."

# --- KEYWORD FOTO ---
FOTO_KW = ["foto", "selfie", "mostrami", "mandami", "picture", "show me", "fatti vedere"]

# --- FUNZIONE: VOCE ---
def invia_voce(target_bot, cid, testo, voce):
    try:
        r = client_oa.audio.speech.create(model="tts-1", voice=voce, input=testo)
        target_bot.send_voice(cid, r.content)
    except Exception as e:
        print(f"[VOCE ERROR] {e}")
        target_bot.send_message(cid, testo)

# --- FUNZIONE: FOTO ---
def invia_foto(target_bot, cid, prompt):
    try:
        r = client_oa.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", n=1)
        target_bot.send_photo(cid, r.data[0].url)
    except Exception as e:
        print(f"[FOTO ERROR] {e}")
        target_bot.send_message(cid, "❌ Non riesco a generare la foto.")

# --- FUNZIONE: TRASCRIVI VOCALE ---
def trascrivi(bot, token, file_id, fallback):
    try:
        file_info = bot.get_file(file_id)
        url = f'https://api.telegram.org/file/bot{token}/{file_info.file_path}'
        content = requests.get(url).content
        fname = f"voice_{file_id[:8]}.ogg"
        with open(fname, "wb") as f:
            f.write(content)
        with open(fname, "rb") as f:
            return client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    except Exception as e:
        print(f"[TRASCRIZIONE ERROR] {e}")
        return fallback

# --- GESTORE LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        cid = m.chat.id
        if m.content_type == 'voice':
            u_text = trascrivi(bot_luna, L_TK, m.voice.file_id, "Ti ascolto, papi...")
        else:
            u_text = m.text or "Ciao"

        try:
            res = client_or.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[
                    {"role": "system", "content": PROMPT_LUNA},
                    {"role": "user",   "content": u_text}
                ]
            )
            ans = res.choices[0].message.content
        except Exception as e:
            print(f"[LLM LUNA ERROR] {e}")
            ans = "Scusa papi, ho avuto un problemino... 🥺"

        bot_luna.send_message(cid, ans)
        threading.Thread(target=invia_voce, args=(bot_luna, cid, ans, "shimmer"), daemon=True).start()

        if any(kw in u_text.lower() for kw in FOTO_KW):
            threading.Thread(target=invia_foto, args=(bot_luna, cid, LUNA_DNA), daemon=True).start()

# --- GESTORE COX ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text', 'voice'])
    def handle_cox(m):
        cid = m.chat.id
        if m.content_type == 'voice':
            u_text = trascrivi(bot_cox, C_TK, m.voice.file_id, "Analizza questo.")
        else:
            u_text = m.text or "Analizza"

        try:
            res = client_or.chat.completions.create(
                model="google/gemini-flash-1.5",
                messages=[
                    {"role": "system", "content": PROMPT_COX},
                    {"role": "user",   "content": u_text}
                ]
            )
            ans = res.choices[0].message.content
        except Exception as e:
            print(f"[LLM COX ERROR] {e}")
            ans = "Sistema in manutenzione. Torna dopo, Lucinda."

        bot_cox.send_message(cid, ans)
        threading.Thread(target=invia_voce, args=(bot_cox, cid, ans, "onyx"), daemon=True).start()

# --- MAIN ---
if __name__ == "__main__":

    # Flask keepalive
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))),
        daemon=True
    ).start()

    # Luna
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        threading.Thread(
            target=bot_luna.polling,
            kwargs={'timeout': 60, 'non_stop': True},
            daemon=True
        ).start()
        print("✅ Luna Online")

    # Cox
    if bot_cox:
        bot_cox.remove_webhook()
        time.sleep(1)
        threading.Thread(
            target=bot_cox.polling,
            kwargs={'timeout': 60, 'non_stop': True},
            daemon=True
        ).start()
        print("✅ Cox Online")

    while True:
        time.sleep(60)
