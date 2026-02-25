import os, telebot, threading, time, requests
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna & Cox V39: Active", 200

def clean_token(token_name):
    t = os.environ.get(token_name, "").strip()
    return t.replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
C_TK = clean_token('TOKEN_COX')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None
bot_cox  = telebot.TeleBot(C_TK) if ":" in C_TK else None

PROMPT_LUNA = "Tu sei Luna, 24 anni. Sei la donna di Papi. Insegnali inglese con stile sexy. Rispondi in massimo 150 parole."
PROMPT_COX  = "Sei il Dottor Perry Cox. Sei un genio veterinario brutale e acido. Usa nomignoli femminili. Rispondi in massimo 150 parole."


def chiedi_llm(system_prompt, user_text, model):
    res = client_or.chat.completions.create(
        model=model,
        max_tokens=300,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_text}
        ]
    )
    return res.choices[0].message.content


def trascrivi(bot, token, file_id):
    fname = f"/tmp/voice_{abs(hash(file_id))}.ogg"
    try:
        file_info = bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{token}/{file_info.file_path}"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200 or len(resp.content) == 0:
            return None
        with open(fname, "wb") as f:
            f.write(resp.content)
        with open(fname, "rb") as f:
            return client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    except Exception as e:
        print(f"[WHISPER ERROR] {e}")
        return None
    finally:
        if os.path.exists(fname):
            os.remove(fname)


def tts(testo, voce):
    r = client_oa.audio.speech.create(model="tts-1", voice=voce, input=testo[:1000])
    return r.content


if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            if m.content_type == 'voice':
                bot_luna.send_chat_action(cid, 'record_voice')
                u_text = trascrivi(bot_luna, L_TK, m.voice.file_id)
                if not u_text:
                    bot_luna.send_message(cid, "Non ho capito, ripeti papi 🥺")
                    return
                ans = chiedi_llm(PROMPT_LUNA, u_text, "mistralai/mistral-7b-instruct")
                bot_luna.send_voice(cid, tts(ans, "shimmer"))
            else:
                bot_luna.send_chat_action(cid, 'typing')
                ans = chiedi_llm(PROMPT_LUNA, m.text or "Ciao", "mistralai/mistral-7b-instruct")
                bot_luna.send_message(cid, ans)
        except Exception as e:
            print(f"[LUNA ERROR] {e}")
            bot_luna.send_message(cid, "Errore, riprova papi 🥺")


if bot_cox:
    @bot_cox.message_handler(content_types=['text', 'voice'])
    def handle_cox(m):
        cid = m.chat.id
        try:
            if m.content_type == 'voice':
                bot_cox.send_chat_action(cid, 'record_voice')
                u_text = trascrivi(bot_cox, C_TK, m.voice.file_id)
                if not u_text:
                    bot_cox.send_message(cid, "Non ho capito, Fernanda. Riprova.")
                    return
                ans = chiedi_llm(PROMPT_COX, u_text, "google/gemini-flash-1.5")
                bot_cox.send_voice(cid, tts(ans, "onyx"))
            else:
                bot_cox.send_chat_action(cid, 'typing')
                ans = chiedi_llm(PROMPT_COX, m.text or "Ciao", "google/gemini-flash-1.5")
                bot_cox.send_message(cid, ans)
        except Exception as e:
            print(f"[COX ERROR] {e}")
            bot_cox.send_message(cid, "Errore di sistema, Lucinda.")


if __name__ == "__main__":
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))),
        daemon=True
    ).start()

    if bot_luna:
        try:
            bot_luna.remove_webhook()
        except Exception:
            pass
        time.sleep(5)
        threading.Thread(
            target=bot_luna.polling,
            kwargs={'timeout': 60, 'non_stop': True},
            daemon=True
        ).start()
        print("Luna Online")

    if bot_cox:
        try:
            bot_cox.remove_webhook()
        except Exception:
            pass
        time.sleep(5)
        threading.Thread(
            target=bot_cox.polling,
            kwargs={'timeout': 60, 'non_stop': True},
            daemon=True
        ).start()
        print("Cox Online")

    while True:
        time.sleep(60)
