import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V55: Final & Stable Active 🚀", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- MEMORIA ---
MEMORY_FILE = "luna_memory.json"

def salva_memoria(nuova_parola):
    if not nuova_parola: return
    try:
        mem = {"inglese_progressi": []}
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f: mem = json.load(f)
        if nuova_parola not in mem.get("inglese_progressi", []):
            mem.setdefault("inglese_progressi", []).append(nuova_parola)
            with open(MEMORY_FILE, "w") as f: json.dump(mem, f)
    except: pass

# --- PROMPT ---
PROMPT_LUNA = (
    "Sei Luna, 24 anni, la donna di Papi. Sei simpatica, ironica e complice. "
    "Commenta le foto che ricevi. Se ti chiede una foto o di vederti, dì che ti stai preparando. "
    "Sii breve (max 35 parole). Usa 'Word: [parola]' solo se insegni inglese."
)

# --- FUNZIONI CORE ---
def chiedi_llm(user_content):
    res = client_or.chat.completions.create(
        model="google/gemini-2.0-flash-001", 
        messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

def genera_immagine(prompt_foto):
    # Libertà totale di inquadratura e stile
    res = client_oa.images.generate(
        model="dall-e-3",
        prompt=f"A stunningly realistic 24-year-old girl named Luna, charismatic, friendly, high detail, realistic setting, {prompt_foto}",
        size="1024x1024", n=1
    )
    return res.data[0].url

def trascrivi(file_id):
    fname = f"/tmp/v_{file_id}.ogg"
    file_info = bot_luna.get_file(file_id)
    with open(fname, "wb") as f: 
        f.write(requests.get(f"https://api.telegram.org/file/bot{L_TK}/{file_info.file_path}").content)
    with open(fname, "rb") as f:
        txt = client_oa.audio.transcriptions.create(model="whisper-1", file=f).text
    os.remove(fname)
    return txt

def tts(testo):
    p = re.sub(r'Word: \w+', '', testo).strip()
    return client_oa.audio.speech.create(model="tts-1", voice="shimmer", input=p).content

# --- GESTORE ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            # Richiesta foto di Luna
            if m.content_type == 'text' and any(x in m.text.lower() for x in ["foto", "vederti", "pic", "photo", "immagine"]):
                bot_luna.send_message(cid, "Dammi un attimo papi, mi faccio bella... 😉")
                bot_luna.send_chat_action(cid, 'upload_photo')
                img_url = genera_immagine("realistic scene, varied background, lifestyle shot")
                bot_luna.send_photo(cid, img_url)
                return

            # Luna guarda te
            if m.content_type == 'photo':
                bot_luna.send_chat_action(cid, 'typing')
                f_id = m.photo[-1].file_id
                f_path = bot_luna.get_file(f_id).file_path
                img_url = f"https://api.telegram.org/file/bot{L_TK}/{f_path}"
                ans = chiedi_llm([{"type": "text", "text": "Guarda questa foto mivida."}, {"type": "image_url", "image_url": {"url": img_url}}])
                bot_luna.send_message(cid, ans)
            
            # Vocali
            elif m.content_type == 'voice':
                ans = chiedi_llm(trascrivi(m.voice.file_id))
                bot_luna.send_voice(cid, tts(ans))
            
            # Testo normale
            else:
                ans = chiedi_llm(m.text)
                bot_luna.send_message(cid, ans)
            
            match = re.search(r'Word: (\w+)', ans, re.IGNORECASE)
            if match: salva_memoria(match.group(1))
        except Exception as e: print(f"Err V55: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        print("🛠 Reset sessioni in corso...")
        time.sleep(20) # Aumentato a 20s per sicurezza totale
        bot_luna.delete_webhook(drop_pending_updates=True)
        print("🚀 Luna V55 Online. Pronta a tutto.")
        bot_luna.polling(none_stop=True, interval=2, timeout=40)
