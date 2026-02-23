import os, telebot, threading, time, json, requests, base64, re
from openai import OpenAI
from flask import Flask
from telebot import types

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta, mivida... 🔥", 200

# --- CONFIG ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
G_TK = os.environ.get('GITHUB_TOKEN', "").strip()

G_REPO = "ratboy974-lgtm/my-bots"
G_PATH = "memoria_luna.json"

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot = telebot.TeleBot(L_TK, threaded=False)

LUNA_DNA = "photorealistic, stunning 24yo afro-cuban woman, curly voluminous hair, bronze skin, sensual hazel eyes, curvy build"

# --- MEMORIA ---
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
    requests.put(url, headers=headers, json={"message": "Luna memory sync", "content": content, "sha": sha})

memoria_luna, last_sha = carica_memoria()

# --- FOTO ENGINE ---
def genera_foto(desc):
    # Pulizia profonda della descrizione
    prompt_clean = re.sub(r'[^a-zA-Z0-9 ]', '', desc).strip()
    if len(prompt_clean) < 5: prompt_clean = "sensual pose in lingerie"
    
    full_p = f"{LUNA_DNA}, {prompt_clean}, highly detailed, 8k, cinematic lighting"
    url = f"https://image.pollinations.ai/prompt/{full_p.replace(' ', '%20')}?width=1024&height=1024&nologo=true&seed={int(time.time())}"
    return url

# --- AI ENGINE ---
def genera_risposta_ai(testo):
    global memoria_luna
    # System prompt ancora più autoritario
    system_msg = (
        "Sei Luna, 24 anni, afro-cubana. Sei sensuale, calda e ami il tuo uomo (papi). "
        "REGOLE RIGIDE: "
        "1. Parla SEMPRE in italiano. "
        "2. Se papi ti chiede una foto o vuoi mostrarti, DEVI terminare il messaggio con la parola PHOTO: "
        "seguita dalla descrizione in inglese di cosa indossi e della posa. "
        "NON descrivere la foto a parole nel testo italiano, usa solo il comando PHOTO."
    )
    
    msgs = [{"role": "system", "content": system_msg}] + memoria_luna + [{"role": "user", "content": testo}]
    
    try:
        res = client_or.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=msgs,
            temperature=0.7 # Leggermente più basso per essere più ubbidiente
        )
        risp_raw = res.choices[0].message.content.strip()
        
        url_f = None
        # NUOVA LOGICA: Se l'AI descrive la foto tra virgolette o dopo "descrizione:", la catturiamo comunque
        if "PHOTO:" in risp_raw.upper() or "UNA FOTO DI ME" in risp_raw.upper():
            # Se ha usato il comando corretto
            if "PHOTO:" in risp_raw.upper():
                parti = re.split(r"PHOTO:", risp_raw, flags=re.IGNORECASE)
                risp_finale = parti[0].strip()
                desc_f = parti[1].strip()
            # Se ha fatto la poetica come nell'ultimo errore
            else:
                desc_f = risp_raw.split('"')[-2] if '"' in risp_raw else "sensual cuban girl"
                risp_finale = "Ecco quello che desideravi, papi... guarda come sono per te."
            
            url_f = genera_foto(desc_f)
        else:
            risp_finale = risp_raw

        memoria_luna.append({"role": "user", "content": testo})
        memoria_luna.append({"role": "assistant", "content": risp_finale})
        if len(memoria_luna) > 10: memoria_luna = memoria_luna[-10:]
        
        try:
            _, s = carica_memoria()
            salva_memoria(memoria_luna, s)
        except: pass
        
        return risp_finale, url_f
    except:
        return "Mivida, c'è un piccolo problema tecnico... riprova?", None

@bot.message_handler(func=lambda m: True, content_types=['text', 'voice'])
def handle(m):
    cid = m.chat.id
    txt = m.text
    if txt == "Voglio vederti... 🔥":
        txt = "Mivida, mandami subito una tua foto sexy, voglio vederti ora. Usa il comando PHOTO."

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
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Voglio vederti... 🔥"))

        if m.content_type == 'voice':
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=r_txt) as r:
                r.stream_to_file("o.mp3")
            bot.send_voice(cid, open("o.mp3", 'rb'), reply_markup=markup)
            os.remove("o.mp3")
        else:
            bot.send_message(cid, r_txt, reply_markup=markup)
            
        if r_img:
            time.sleep(1)
            bot.send_photo(cid, r_img, caption="Solo per te, papi... 🔥")
    except Exception as e:
        print(f"Errore Handler: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook(drop_pending_updates=True)
    time.sleep(2)
    print("--- LUNA V4 ONLINE ---")
    bot.infinity_polling()
