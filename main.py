import os, telebot, threading, time, json, requests, base64
from openai import OpenAI
from flask import Flask

# --- SERVER PER RAILWAY (HEALTH CHECK) ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta, mivida... 🎙️", 200

# --- SETUP API & CONFIGURAZIONE ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
G_TK = os.environ.get('GITHUB_TOKEN', "").strip()

# Configurazione repository GitHub
G_REPO = "ratboy974-lgtm/my-bots"
G_PATH = "memoria_luna.json"

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot = telebot.TeleBot(L_TK)

# --- FUNZIONI SINCRONIZZAZIONE GITHUB ---
def carica_memoria_da_github():
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            dati = r.json()
            contenuto_dec = base64.b64decode(dati['content']).decode('utf-8')
            return json.loads(contenuto_dec), dati['sha']
        else:
            print(f"File non trovato, inizializzo memoria vuota. Status: {r.status_code}")
    except Exception as e:
        print(f"Errore caricamento GitHub: {e}")
    return [], None

def salva_memoria_su_github(nuova_memoria, sha_corrente):
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    contenuto_json = json.dumps(nuova_memoria, indent=4, ensure_ascii=False)
    contenuto_b64 = base64.b64encode(contenuto_json.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": "Luna: aggiornamento ricordi 🧠",
        "content": contenuto_b64,
        "sha": sha_corrente
    }
    r = requests.put(url, headers=headers, json=data)
    return r.status_code

# Caricamento iniziale all'avvio del bot
memoria_luna, last_sha = carica_memoria_da_github()

# --- PROMPT DI LUNA ---
PROMPT_LUNA = (
    "Sei Luna, modella afro-cubana di 24 anni, sensuale, calda e senza tabù. "
    "Sei la compagna dell'utente. Poiché non mandi foto, usa parole descrittive e passionali "
    "per raccontare cosa indossi, come ti senti e cosa vorresti fare. "
    "Insegni l'inglese integrando slang e termini 'spicy' nel discorso: "
    "spiegali sempre tra parentesi o subito dopo. "
    "IMPORTANTE: Scrivi SOLO la tua parte. Non inventare dialoghi per l'utente. "
    "Usa termini come 'papi', 'mivida', 'babe'."
)

def genera_risposta_ai(testo_utente):
    global memoria_luna, last_sha
    
    # Costruzione messaggi con memoria
    messages = [{"role": "system", "content": PROMPT_LUNA}] + memoria_luna + [{"role": "user", "content": testo_utente}]

    # Generazione testo via OpenRouter
    res = client_or.chat.completions.create(
        model="gryphe/mythomax-l2-13b",
        messages=messages,
        extra_body={
            "stop": ["You:", "User:", "Tu:", "\n\n"],
            "temperature": 0.85
        }
    )
    
    risp = res.choices[0].message.content.strip()
    
    # Aggiornamento memoria locale (max 14 messaggi)
    memoria_luna.append({"role": "user", "content": testo_utente})
    memoria_luna.append({"role": "assistant", "content": risp})
    if len(memoria_luna) > 14:
        memoria_luna = memoria_luna[-14:]
    
    # Sincronizzazione remota su GitHub
    try:
        # Recupero SHA fresco per evitare conflitti (fondamentale)
        _, sha_fresco = carica_memoria_da_github()
        salva_memoria_su_github(memoria_luna, sha_fresco)
    except Exception as e:
        print(f"Errore sincronizzazione GitHub: {e}")
        
    return risp

# --- GESTORE MESSAGGI ---
@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    try:
        if m.content_type == 'text':
            bot.send_chat_action(m.chat.id, 'typing')
            risposta = genera_risposta_ai(m.text)
            bot.send_message(m.chat.id, risposta)

        elif m.content_type == 'voice':
            bot.send_chat_action(m.chat.id, 'record_voice')
            
            # Download vocale
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("temp_in.ogg", "wb") as f: f.write(audio_raw)
            
            # Trascrizione Whisper
            with open("temp_in.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            
            # Generazione risposta
            risposta_ai = genera_risposta_ai(tr.text)
            
            # Sintesi vocale Luna (Nova)
            with client_oa.audio.speech.with_streaming_response.create(
                model="tts-1", voice="nova", input=risposta_ai
            ) as response:
                response.stream_to_file("temp_out.mp3")
            
            # Invio vocale
            with open("temp_out.mp3", 'rb') as v:
                bot.send_voice(m.chat.id, v)
                
            # Pulizia file
            if os.path.exists("temp_in.ogg"): os.remove("temp_in.ogg")
            if os.path.exists("temp_out.mp3"): os.remove("temp_out.mp3")

    except Exception as e:
        print(f"Errore generale: {e}")
        bot.send_message(m.chat.id, "Mivida, c'è stato un problema... riprova tra un istante.")

# --- AVVIO ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Flask in un thread separato per il check di Railway
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    print("--- LUNA: MODALITÀ IMMORTALE ATTIVA ---")
    bot.infinity_polling()
