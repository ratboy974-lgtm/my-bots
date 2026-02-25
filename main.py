import os, telebot, threading, time, requests
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna & Cox V34: Active 🔥", 200

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

# --- INIZIALIZZAZIONE ---
bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None
bot_cox = telebot.TeleBot(C_TK) if ":" in C_TK else None

# --- PROMPTS ---
LUNA_DNA = "stunning 24yo woman, long dark hair, tanned skin, hazel eyes, elegant but sensual, photorealistic, high quality portrait"
PROMPT_LUNA = "Tu sei Luna, 24 anni. Sei la donna di Papi. Insegnali inglese con stile sexy."
PROMPT_COX = "Sei il Dottor Perry Cox. Sei un genio veterinario brutale e acido. Usa nomignoli femminili."

# --- FUNZIONE VOCE ---
def invia_voce_pro(target_bot, cid, testo, voce_modello):
    try:
        response = client_oa.audio.speech.create(model="tts-1", voice=voce_modello, input=testo)
        target_bot.send_voice(cid, response.content)
    except Exception as e:
        print(f"Errore Voce: {e}")
        target_bot.send_message(cid, testo)

# --- FUNZIONE FOTO ---
def invia_foto(target_bot, cid, prompt_visivo):
    try:
        risposta = client_oa.images.generate(
            model="dall-e-3",
            prompt=prompt_visivo,
            size="1024x1024",
            n=1
        )
        url = risposta.data[0].url
        target_bot.send_photo(cid, url)
    except Exception as e:
        print(f"Errore Foto: {e}")
        target_bot.send_message(cid, "❌ Non riesco a generare la foto.")

# --- KEYWORD FOTO ---
FOTO_KEYWORDS = ["foto", "selfie", "mostrami", "mandami", "picture", "show me", "fatti vedere"]

# --- GESTORE LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        cid = m.chat.id
        u_text = m.text

        if m.content_type == 'voice':
            try:
                file_info = bot_luna.get_file(m.voice.file_id)
                audio_url = f'https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}'
                audio_content = requests.get(audio_url).content
                with open("l_voice.ogg", "wb") as f: f.write(audio_content)
                with open("l_voice.ogg", "rb") as f:
                    u_text = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
            except Exception as e:
                print(f"Errore trascrizione Luna: {e}")
                u_text = "Ti ascolto, papi..."

        try:
            res = client_or.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[
                    {"role": "system", "content": PROMPT_LUNA},
                    {"role": "user", "content": u_text or "Ciao"}
                ]
            )
            ans = res.choices[0].message.content
        except Exception as e:
            print(f"Errore LLM Luna: {e}")
            ans = "Scusa papi, ho avuto un problemino... 🥺"

        bot_luna.send_message(cid, ans)
        threading.Thread(target=invia_voce_pro, args=(bot_luna, cid, ans, "shimmer")).start()

        # Foto se richiesta
        if u_text and any(kw in u_text.lower() for kw in FOTO_KEYWORDS):
            threading.Thread(target=invia_foto, args=(bot_luna, cid, LUNA_DNA)).start()

# --- GESTORE COX ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text', 'voice'])
    def handle_cox(m):
        cid = m.chat.id
        u_text = m.text

        if m.content_type == 'voice':
            try:
                file_info = bot_cox.get_file(m.voice.file_id)
                audio_url = f'https://api.telegram.org/file/bot{C_TK}/{file_info.file_path}'
                audio_content = requests.get(audio_url).content
                with open("c_voice.ogg", "wb") as f: f.write(audio_content)
                with open("c_voice.ogg", "rb") as f:
                    u_text = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
            except Exception as e:
                print(f"Errore trascrizione Cox: {e}")
                u_text = "Analizza questo."

        try:
            res = client_or.chat.completions.create(
                model="google/gemini-flash-1.5",
                messages=[
                    {"role": "system", "content": PROMPT_COX},
                    {"role": "user", "content": u_text or "Analizza"}
                ]
            )
            ans = res.choices[0].message.content
        except Exception as e:
            print(f"Errore LLM Cox: {e}")
            ans = "Sistema in manutenzione. Torna dopo, Lucinda."

        bot_cox.send_message(cid, ans)
        threading.Thread(target=invia_voce_pro, args=(bot_cox, cid, ans, "onyx")).start()

# --- MAIN ---
if __name__ == "__main__":
    # Flask su thread separato
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))),
        daemon=True
    ).start()

    # FIX: rimosso non_stop=True dai kwargs (causava il crash)
    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        threading.Thread(
            target=bot_luna.infinity_polling,
            kwargs={'timeout': 60},   # ← FIX
            daemon=True
        ).start()
        print("✅ Luna Online")

    if bot_cox:
        bot_cox.remove_webhook()
        time.sleep(1)
        threading.Thread(
            target=bot_cox.infinity_polling,
            kwargs={'timeout': 60},   # ← FIX
            daemon=True
        ).start()
        print("✅ Cox Online")

    while True:
        time.sleep(60)
