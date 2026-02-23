import os, telebot, threading, time, json, requests, base64, re
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna con Llama 3 è pronta! 🔥", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
G_TK = os.environ.get('GITHUB_TOKEN', "").strip()

G_REPO = "ratboy974-lgtm/my-bots"
G_PATH = "memoria_luna.json"

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot = telebot.TeleBot(L_TK)

LUNA_DNA = "stunning 24yo afro-cuban girl, curly hair, bronze skin, sensual eyes, curvy athletic body"

def carica_memoria():
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()['content']).decode('utf-8')), r.json()['sha']
    except: pass
    return [], None

def salva_memoria(mem, sha):
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    content = base64.b64encode(json.dumps(mem, ensure_ascii=False, indent=2).encode('utf-8')).decode('utf-8')
    requests.put(url, headers=headers, json={"message": "Luna update", "content": content, "sha": sha})

memoria_luna, last_sha = carica_memoria()

def genera_foto(desc):
    clean = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip()
    # Usiamo Pollinations che è istantaneo
    url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', '%20')}%20{clean.replace(' ', '%20')}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
    return url

def genera_risposta_ai(testo):
    global memoria_luna
    # SISTEMA LUNA - Molto più diretto per Llama 3
    msgs = [{"role": "system", "content": (
        "You are Luna, a 24yo afro-cuban sensual woman. You are the user's lover (papi). "
        "Talk in Italian. Be passionate and spicy. Teach English slang. "
        "IMPORTANT: If you want to show a photo, you MUST end the message with exactly: PHOTO: [english description]. "
        "Example: 'Ti aspetto a letto, papi. PHOTO: posing on bed in silk lingerie'"
    )}] + memoria_luna + [{"role": "user", "content": testo}]
    
    try:
        # CAMBIO MODELLO: Usiamo Llama-3-8B (molto più ubbidiente)
        res = client_or.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=msgs,
            temperature=0.8
        )
        risp_raw = res.choices[0].message.content.strip()
        
        url_f = None
        # Cerchiamo il comando PHOTO nel testo
        if "PHOTO:" in risp_raw.upper():
            parti = re.split(r"PHOTO:", risp_raw, flags=re.IGNORECASE)
            risp_finale = parti[0].strip()
            desc_f = parti[1].strip().replace("[", "").replace("]", "")
            url_f = genera_foto(desc_f)
        else:
            risp_finale = risp_raw

        # Memoria
        memoria_luna.append({"role": "user", "content": testo})
        memoria_luna.append({"role": "assistant", "content": risp_finale})
        if len(memoria_luna) > 10: memoria_luna = memoria_luna[-10:]
        
        try:
            _, s = carica_memoria()
            salva_memoria(memoria_luna, s)
        except: pass
        
        return risp_finale, url_f
    except Exception as e:
        print(f"Errore: {e}")
        return "Mivida, c'è un piccolo problema... riprova?", None

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Voglio vederti... 🔥"))
    return markup

@bot.message_handler(content_types=['text', 'voice'])
def handle(m):
    cid = m.chat.id
    txt = m.text
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mandami subito una tua foto sexy, voglio vederti."

    try:
        if m.content_type == 'voice':
            f_info = bot.get_file(m.voice.file_id)
            with open("v.ogg", "wb") as f: f.write(bot.download_file(f_info.file_path))
            with open("v.ogg", "rb") as audio:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=audio)
            txt = tr.text
            os.remove("v.ogg")
        
        bot.send_chat_action(cid, 'typing')
        r_txt, r_img = genera_risposta_ai(txt)
        
        if m.content_type == 'voice':
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=r_txt) as r:
                r.stream_to_file("o.mp3")
            with open("o.mp3", 'rb') as v: bot.send_voice(cid, v, reply_markup=get_main_keyboard())
            os.remove("o.mp3")
        else:
            bot.send_message(cid, r_txt, reply_markup=get_main_keyboard())
            
        if r_img:
            time.sleep(1)
            bot.send_photo(cid, r_img, caption="Solo per te, papi... 🔥")
            
    except Exception as e: print(e)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    print("--- LUNA: ONLINE (LLAMA 3 VERSION) ---")
    bot.infinity_polling()
