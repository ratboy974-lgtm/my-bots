import os, telebot, threading, time, requests
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna & Cox V36: Active", 200

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

LUNA_DNA    = "stunning 24yo woman, long dark hair, tanned skin, hazel eyes, elegant but sensual, photorealistic, high quality portrait"
PROMPT_LUNA = "Tu sei Luna, 24 anni. Sei la donna di Papi. Insegnali inglese con stile sexy."
PROMPT_COX  = "Sei il Dottor Perry Cox. Sei un genio veterinario brutale e acido. Usa nomignoli femminili."
FOTO_KW     = ["foto", "selfie", "mostrami", "mandami", "picture", "show me", "fatti vedere"]


def invia_voce(target_bot, cid, testo, voce):
    try:
        r = client_oa.audio.speech.create(model="tts-1", voice=voce, input=testo)
        target_bot.send_voice(cid, r.content)
    except Exception as e:
        print(f"[VOCE ERROR] {e}")


def invia_foto(target_bot, cid, prompt):
    try:
        r = client_oa.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", n=1)
        target_bot.send_photo(cid, r.data[0].url)
    except Exception as e:
        print(f"[FOTO ERROR] {e}")
        target_bot.send_message(cid, "Errore foto.")


def trascrivi(bot, token, file_id, fallback):
    fname = f"/tmp/voice_{abs(hash(file_id))}.ogg"
    try:
        file_info = bot.get_file(file_id)
        print(f"[VOICE] file_path: {file_info.file_path}")
        url = f"https://api.telegram.org/file/bot{token}/{file_info.file_path}"
        resp = requests.get(url, timeout=30)
        print(f"[VOICE] status: {resp.status_code}, size: {len(resp.content)}")
        if resp.status_code != 200 or len(resp.content) == 0:
            print("[VOICE] Download fallito")
            return fallback
        with open(fname, "wb") as f:
            f.write(resp.content)
        with open(fname, "rb") as f:
            result = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
        print(f"[VOICE] Trascrizione: {result.text}")
        return result.text
    except Exception as e:
        print(f"[TRASCRIZIONE ERROR] {type(e).__name__}: {e}")
        return fallback
    finally:
        if os.path.exists(fname):
            os.remove(fname)


if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        cid = m.chat.id
        print(f"[LUNA] tipo={m.content_type}")
        if m.content_type == 'voice':
            bot_luna.send_chat_action(cid, 'typing')
            u_text = trascrivi(bot_luna, L_TK, m.voice.file_id, "Ti ascolto, papi...")
        else:
            u_text = m.text or "Ciao"
        print(f"[LUNA] input: {u_text}")
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


if bot_cox:
    @bot_cox.message_handler(content_types=['text', 'voice'])
    def handle_cox(m):
        cid = m.chat.id
        print(f"[COX] tipo={m.content_type}")
        if m.content_type == 'voice':
            bot_cox.send_chat_action(cid, 'typing')
            u_text = trascrivi(bot_cox, C_TK, m.voice.file_id, "Analizza questo.")
        else:
            u_text = m.text or "Analizza"
        print(f"[COX] input: {u_text}")
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


if __name__ == "__main__":
    print(f"[INIT] Luna: {'OK' if bot_luna else 'MANCA TOKEN'}")
    print(f"[INIT] Cox:  {'OK' if bot_cox else 'MANCA TOKEN'}")
    print(f"[INIT] OpenAI: {'OK' if OA_K else 'MANCA KEY'}")
    print(f"[INIT] OpenRouter: {'OK' if OR_K else 'MANCA KEY'}")

    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))),
        daemon=True
    ).start()

    if bot_luna:
        bot_luna.remove_webhook()
        time.sleep(1)
        threading.Thread(
            target=bot_luna.polling,
            kwargs={'timeout': 60, 'non_stop': True},
            daemon=True
        ).start()
        print("Luna Online")

    if bot_cox:
        bot_cox.remove_webhook()
        time.sleep(1)
        threading.Thread(
            target=bot_cox.polling,
            kwargs={'timeout': 60, 'non_stop': True},
            daemon=True
        ).start()
        print("Cox Online")

    while True:
        time.sleep(60)
