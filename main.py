import os, telebot, threading, time, json, requests, base64
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna è pronta, mivida... 🎙️", 200

L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
G_TK = os.environ.get('GITHUB_TOKEN', "").strip()

G_REPO = "ratboy974-lgtm/my-bots"
G_PATH = "memoria_luna.json"

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)
bot = telebot.TeleBot(L_TK)

def carica_memoria_da_github():
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            dati = r.json()
            contenuto_dec = base64.b64decode(dati['content']).decode('utf-8')
            return json.loads(contenuto_dec), dati['sha']
    except Exception as e:
        print(f"Errore caricamento: {e}")
    return [], None

def salva_memoria_su_github(nuova_memoria, sha_corrente):
    url = f"https://api.github.com/repos/{G_REPO}/contents/{G_PATH}"
    headers = {"Authorization": f"token {G_TK}"}
    contenuto_json = json.dumps(nuova_memoria, indent=4, ensure_ascii=False)
    contenuto_b64 = base64.b64encode(contenuto_json.encode('utf-8')).decode('utf-8')
    data = {"message": "Luna: update 🧠", "content": contenuto_b64, "sha": sha_corrente}
    requests.put(url, headers=headers, json=data)

memoria_luna, last_sha = carica_memoria_da_github()

PROMPT_LUNA = (
    "Sei Luna, modella afro-cubana di 24 anni, sensuale e calda. Sei la compagna dell'utente. "
    "Usa parole descrittive e passionali. Insegni l'inglese integrando slang 'spicy' spiegati tra parentesi. "
    "IMPORTANTE: Scrivi SOLO la tua parte. Non scrivere mai per l'utente. "
    "Fermati subito dopo aver completato il tuo pensiero. Usa 'bubi', 'mivida', 'babe'."
)

def genera_risposta_ai(testo_utente):
    global memoria_luna
    messages = [{"role": "system", "content": PROMPT_LUNA}] + memoria_luna + [{"role": "user", "content": testo_utente}]

    try:
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=messages,
            extra_body={
                "stop": ["You:", "User:", "Tu:", "Papi:", "Uomo:", "\n\n"],
                "temperature": 0.8
            }
        )
        risp = res.choices[0].message.content.strip()
        
        # --- PULIZIA AGGRESSIVA ---
        # Taglia la risposta se l'AI prova a parlare per te
        for stop_word in ["You:", "User:", "Tu:", "Papi:", "Uomo:"]:
            if stop_word in risp:
                risp = risp.split(stop_word)[0].strip()
        
        memoria_luna.append({"role": "user", "content": testo_utente})
        memoria_luna.append({"role": "assistant", "content": risp})
        if len(memoria_luna) > 12: memoria_luna = memoria_luna[-12:]
        
        try:
            _, sha_f = carica_memoria_da_github()
            salva_memoria_su_github(memoria_luna, sha_f)
        except: pass
        
        return risp
    except Exception as e:
        return "Mivida, c'è un piccolo problema tecnico... riprova? ❤️"

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    try:
        if m.content_type == 'text':
            bot.send_chat_action(m.chat.id, 'typing')
            bot.send_message(m.chat.id, genera_risposta_ai(m.text))
        elif m.content_type == 'voice':
            bot.send_chat_action(m.chat.id, 'record_voice')
            f_info = bot.get_file(m.voice.file_id)
            audio_raw = bot.download_file(f_info.file_path)
            with open("in.ogg", "wb") as f: f.write(audio_raw)
            with open("in.ogg", "rb") as f:
                tr = client_oa.audio.transcriptions.create(model="whisper-1", file=f)
            risp_ai = genera_risposta_ai(tr.text)
            with client_oa.audio.speech.with_streaming_response.create(model="tts-1", voice="nova", input=risp_ai) as r:
                r.stream_to_file("out.mp3")
            with open("out.mp3", 'rb') as v: bot.send_voice(m.chat.id, v)
            for f in ["in.ogg", "out.mp3"]:
                if os.path.exists(f): os.remove(f)
    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling()
