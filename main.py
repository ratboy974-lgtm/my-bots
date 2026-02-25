import os, telebot, threading, time, requests, json
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna & Cox V40: Vision & Memory Active 🔥", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
C_TK = clean_token('TOKEN_COX')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK) if ":" in L_TK else None
bot_cox  = telebot.TeleBot(C_TK) if ":" in C_TK else None

# --- FILE DI MEMORIA ---
MEMORY_FILE = "luna_memory.json"

def carica_memoria():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f: return json.load(f)
    return {"inglese_progressi": []}

def salva_memoria(nuova_parola):
    mem = carica_memoria()
    if nuova_parola not in mem["inglese_progressi"]:
        mem["inglese_progressi"].append(nuova_parola)
        with open(MEMORY_FILE, "w") as f: json.dump(mem, f)

# --- PROMPTS ---
PROMPT_LUNA = "Sei Luna, 24 anni, la donna di Papi. Insegni inglese in modo sexy. Salva le parole nuove. Max 150 parole."
PROMPT_COX  = "Sei il Dr. Perry Cox. Genio veterinario acido. Se ricevi una foto, analizzala clinicamente. Max 150 parole."

# --- FUNZIONI CORE ---
def chiedi_llm(system_prompt, user_content, model):
    res = client_or.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    )
    return res.choices[0].message.content

def trascrivi(bot, token, file_id):
    fname = f"/tmp/voice_{file_id}.ogg"
    file_info = bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{token}/{file_info.file_path}"
    with open(fname, "wb") as f: f.write(requests.get(url).content)
    with open(fname, "rb") as f:
        return client_oa.audio.transcriptions.create(model="whisper-1", file=f).text

def tts(testo, voce):
    return client_oa.audio.speech.create(model="tts-1", voice=voce, input=testo[:1000]).content

# --- GESTORE LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice'])
    def handle_luna(m):
        cid = m.chat.id
        u_text = trascrivi(bot_luna, L_TK, m.voice.file_id) if m.content_type == 'voice' else m.text
        ans = chiedi_llm(PROMPT_LUNA, u_text, "mistralai/mistral-7b-instruct")
        
        # Logica per estrarre parole inglesi (esempio semplice)
        match = re.search(r'word of the day: (\w+)', ans.lower())
        if match: salva_memoria(match.group(1))
        
        if m.content_type == 'voice':
            bot_luna.send_voice(cid, tts(ans, "shimmer"))
        else:
            bot_luna.send_message(cid, ans)

# --- GESTORE COX (Con Vision) ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_cox(m):
        cid = m.chat.id
        content = []
        
        if m.content_type == 'photo':
            file_info = bot_cox.get_file(m.photo[-1].file_id)
            img_url = f"https://api.telegram.org/file/bot{C_TK}/{file_info.file_path}"
            content = [{"type": "text", "text": "Analizza questa immagine clinica, Boia!"}, 
                       {"type": "image_url", "image_url": {"url": img_url}}]
        else:
            u_text = trascrivi(bot_cox, C_TK, m.voice.file_id) if m.content_type == 'voice' else m.text
            content = u_text

        ans = chiedi_llm(PROMPT_COX, content, "google/gemini-flash-1.5")
        
        if m.content_type == 'voice':
            bot_cox.send_voice(cid, tts(ans, "onyx"))
        else:
            bot_cox.send_message(cid, ans)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna: threading.Thread(target=bot_luna.infinity_polling).start()
    if bot_cox: threading.Thread(target=bot_cox.infinity_polling).start()
    while True: time.sleep(60)
