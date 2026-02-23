import os, telebot, threading, time, json, requests, base64, re
from openai import OpenAI
from flask import Flask
from telebot import types # Import per i pulsanti

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta... 🔥", 200

# --- CONFIG ---
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
    prompt_clean = re.sub(r'[^a-zA-Z0-9 ]', '', desc)
    url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', '%20')}%20{prompt_clean.replace(' ', '%20')}?width=1024&height=1024&nologo=true"
    return url

def genera_risposta_ai(testo):
    global memoria_luna
    msgs = [{"role": "system", "content": (
        "Sei Luna, 24 anni, afro-cubana. Sei la donna del tuo utente (papi). "
        "Se lui ti chiede una foto o se vuoi mostrarti, DEVI scrivere alla fine del messaggio: "
        "PHOTO: [descrizione dettagliata in inglese della scena e di cosa indossi]. "
        "Non dimenticare mai il comando PHOTO se l'utente vuole vederti."
    )}] + memoria_luna + [{"role": "user", "content": testo}]
    
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=msgs,
            extra_body={"stop": ["User:", "Papi:", "Tu:"], "temperature": 0.9}
        )
        risp = res.choices[0].message.content.strip()
        
        url_f = None
        # Cerca il trigger della foto
        match = re.search(r"PHOTO[:\s\-]*\[?(.*?)\]?$", risp, re.IGNORECASE | re.DOTALL)
        
        if match:
            desc_f = match.group(1).strip()
            risp = risp[:match.start()].strip()
            if not desc_f: desc_f = "posing sensually"
            url_f = genera_foto(desc_f)

        memoria_luna.append({"role": "user", "content": testo})
        memoria_luna.append({"role": "assistant", "content": risp})
        if len(memoria_luna) > 10: memoria_luna = memoria_luna[-10:]
        
        try:
            _, s = carica_memoria()
            salva_memoria(memoria_luna, s)
        except: pass
        
        return risp, url_f
    except Exception as e: 
        print(f"Errore AI: {e}")
        return "Mivida, riproviamo? ❤️", None

# --- CREAZIONE TASTIERA ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_foto = types.KeyboardButton("Voglio vederti... 🔥")
    markup.add(btn_foto)
    return markup

@bot.message_handler(content_types=['text', 'voice'])
def handle(m):
    cid = m.chat.id
    txt = m.text
    
    # Se preme il bottone, forziamo il testo
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mandami subito una tua foto sexy, voglio vedere come sei vestita ora."

    try:
        if m.content_type == 'voice':
            f = bot.get_file(m.voice.file_id)
            with open("v.ogg", "wb") as file: file.write(bot.download_file(f.file_path))
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
            bot.send_chat_action(cid, 'upload_photo')
            bot.send_photo(cid, r_img, caption="Solo per i tuoi occhi... 🔥")
            
    except Exception as e: print(e)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    print("--- LUNA IS ONLINE (WITH BUTTONS) ---")
    bot.infinity_polling()
