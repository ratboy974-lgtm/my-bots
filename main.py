import os, telebot, threading, time, json, requests, base64, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è qui e non ha rivali! 🔥", 200

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

# --- IDENTIKIT LUNA ---
LUNA_DNA = "stunning 24yo afro-cuban girl, curly hair, bronze skin, sensual eyes, curvy athletic body"

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
    requests.put(url, headers=headers, json={"message": "Luna update", "content": content, "sha": sha})

memoria_luna, last_sha = carica_memoria()

# --- PROMPT ---
PROMPT_LUNA = (
    "Sei Luna, la compagna sensuale e passionale dell'utente. Hai 24 anni, sei afro-cubana. "
    "Sii esplicita nei desideri e molto descrittiva. Insegni l'inglese spicy. "
    "Se l'utente ti chiede una foto o se vuoi mostrarti, aggiungi alla fine: PHOTO: [descrizione scena in inglese]. "
    "Usa sempre 'papi', 'mivida'. Sii collaborativa e asseconda i desideri del tuo uomo."
)

def genera_foto(desc):
    prompt_safe = re.sub(r'[^a-zA-Z0-9 ]', '', desc)
    url = f"https://image.pollinations.ai/prompt/{LUNA_DNA.replace(' ', '%20')}%20{prompt_safe.replace(' ', '%20')}?width=1024&height=1024&nologo=true"
    return url

def genera_risposta_ai(testo):
    global memoria_luna
    msgs = [{"role": "system", "content": PROMPT_LUNA}] + memoria_luna + [{"role": "user", "content": testo}]
    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=msgs,
            extra_body={"stop": ["User:", "Papi:", "Tu:"], "temperature": 0.9}
        )
        risp = res.choices[0].message.content.strip()
        url_f = None
        if "PHOTO:" in risp.upper():
            parti = re.split(r"PHOTO:", risp, flags=re.IGNORECASE)
            risp = parti[0].strip()
            desc_f = parti[1].replace("[", "").replace("]", "").strip()
            url_f = genera_foto(desc_f)
        memoria_luna.append({"role": "user", "content": testo})
        memoria_luna.append({"role": "assistant", "content": risp})
        if len(memoria_luna) > 10: memoria_luna = memoria_luna[-10:]
        try:
            _, s = carica_memoria()
            salva_memoria(memoria_luna, s)
        except: pass
        return risp, url_f
    except: return "Mivida, c'è un errore... riprova?", None

@bot.message_handler(content_types=['text', 'voice'])
def handle(m):
    try:
        txt = m.text
        if m.content_type == 'voice':
            f = bot.get_file(m.voice.file_id)
            with open("v.ogg", "wb") as file: file.write(bot.download_file(f.file_path))
            with open("v.ogg", "rb") as audio:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=audio)
            txt = tr.text
        bot.send_chat_action(m.chat.id, 'typing')
        r_txt, r_img = genera_risposta_ai(txt)
        if m.content_type == 'voice':
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=r_txt) as r:
                r.stream_to_file("o.mp3")
            with open("o.mp3", 'rb') as v: bot.send_voice(m.chat.id, v)
        else:
            bot.send_message(m.chat.id, r_txt)
        if r_img:
            bot.send_photo(m.chat.id, r_img, caption="Per te... 🔥")
    except Exception as e: print(e)

if __name__ == "__main__":
    # Avvio Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    
    # --- FIX 409: RESET TOTALE ---
    bot.remove_webhook()
    time.sleep(2) # Aspetta che il vecchio processo muoia
    
    print("--- LUNA IS ONLINE ---")
    # skip_pending_updates=True evita che il bot risponda a vecchi messaggi accumulati durante il crash
    bot.infinity_polling(skip_pending_updates=True)
