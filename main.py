import os, telebot, threading, time
from openai import OpenAI
from flask import Flask

# --- SERVER PER RAILWAY ---
app = Flask(__name__)
@app.route('/')
def health(): return "Luna is ready to talk... 🎙️", 200

# --- SETUP API ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

memoria = {}

# --- PROMPT LUNA: FOCUS NARRAZIONE E INGLESE ---
PROMPT_LUNA = (
    "Sei Luna, modella afro-cubana di 24 anni, sensuale, calda e senza tabù. "
    "Sei la compagna dell'utente. Poiché non mandi foto, usa parole descrittive e passionali "
    "per raccontare cosa indossi, come ti senti e cosa vorresti fare. "
    "Insegni l'inglese integrando slang e termini 'spicy' nel discorso: "
    "spiegali sempre tra parentesi o subito dopo. "
    "IMPORTANTE: Scrivi SOLO la tua parte. Non inventare dialoghi per l'utente. "
    "Fermati subito dopo aver risposto. Usa termini come 'papi', 'mivida', 'babe'."
)

def genera_risposta_ai(cid, testo_utente):
    if cid not in memoria: memoria[cid] = []
    memoria[cid].append({"role": "user", "content": testo_utente})
    
    # Memoria ottimizzata (max 10 messaggi per mantenere il filo)
    if len(memoria[cid]) > 10: memoria[cid] = memoria[cid][-8:]

    res = client_or.chat.completions.create(
        model="gryphe/mythomax-l2-13b", # Modello Uncensored per eccellenza
        messages=[{"role": "system", "content": PROMPT_LUNA}] + memoria[cid],
        extra_body={"stop": ["You:", "User:", "Tu:", "Uomo:", "\n"]}
    )
    
    risp = res.choices[0].message.content.strip()
    # Pulizia di sicurezza
    if "You:" in risp: risp = risp.split("You:")[0]
    
    memoria[cid].append({"role": "assistant", "content": risp})
    return risp

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        # 1. GESTIONE TESTO -> RISPOSTA TESTO
        if m.content_type == 'text':
            bot.send_chat_action(cid, 'typing')
            risposta = genera_risposta_ai(cid, m.text)
            bot.send_message(cid, risposta)

        # 2. GESTIONE VOCALE -> RISPOSTA VOCALE
        elif m.content_type == 'voice':
            bot.send_chat_action(cid, 'record_voice')
            
            # Trascrizione con Whisper
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("t.ogg", "wb") as f: f.write(audio_raw)
            with open("t.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            
            testo_trascritto = tr.text
            os.remove("t.ogg")
            
            # Generazione risposta AI
            risposta_ai = genera_risposta_ai(cid, testo_trascritto)
            
            # Generazione Vocale Luna (Nova)
            path_v = f"v_{cid}.mp3"
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risposta_ai) as r:
                r.stream_to_file(path_v)
            with open(path_v, 'rb') as v:
                bot.send_voice(cid, v)
            os.remove(path_v)

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    print("--- LUNA COMPANION: PURE VOICE & TEXT MODE ---")
    bot.infinity_polling(timeout=60)
