import os, telebot, threading, time, requests, json, re
from openai import OpenAI
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Luna V58: Debugging Flux Active 🔍", 200

# --- CONFIGURAZIONE ---
def clean_token(token_name):
    return os.environ.get(token_name, "").strip().replace("'", "").replace('"', "")

L_TK = clean_token('TOKEN_LUNA')
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
FAL_K = os.environ.get('FAL_KEY', "").strip()

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K)

bot_luna = telebot.TeleBot(L_TK, threaded=False) if ":" in L_TK else None

# --- FUNZIONE GENERAZIONE IMMAGINE (CON DEBUG) ---
def genera_immagine_fal(prompt_utente):
    if not FAL_K:
        return "ERRORE: Chiave FAL_KEY mancante nelle variabili Railway!"
    
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {
        "Authorization": f"Key {FAL_K}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": f"A hyper-realistic RAW photo of Luna, a beautiful 24-year-old Italian girl, natural skin, charismatic, {prompt_utente}",
        "image_size": "portrait_4_5",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "enable_safety_checker": False 
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return res.json()['images'][0]['url']
        else:
            return f"ERRORE API FAL: {res.status_code} - {res.text[:100]}"
    except Exception as e:
        return f"ERRORE CONNESSIONE: {str(e)}"

# --- LOGICA BOT ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text', 'voice', 'photo'])
    def handle_luna(m):
        cid = m.chat.id
        try:
            if m.content_type == 'text' and any(x in m.text.lower() for x in ["foto", "vederti", "pic", "photo"]):
                bot_luna.send_message(cid, "Mi preparo per te, papi... un attimo. 😉")
                bot_luna.send_chat_action(cid, 'upload_photo')
                
                risultato = genera_immagine_fal(m.text)
                
                if risultato.startswith("http"):
                    bot_luna.send_photo(cid, risultato)
                else:
                    # Se non è un link, è un messaggio di errore
                    bot_luna.send_message(cid, f"Papi, c'è un problema tecnico: {risultato}")
                return

            # Restante logica (Testo/Vocale)
            if m.content_type == 'voice':
                # (Codice trascrizione e risposta uguale a V57)
                bot_luna.send_message(cid, "Ti ho sentito mivida, ma ora testiamo le foto!")
            elif m.content_type == 'text':
                res = client_or.chat.completions.create(
                    model="google/gemini-2.0-flash-001", 
                    messages=[{"role": "system", "content": "Sei Luna, la donna di Papi. Sii audace."}, {"role": "user", "content": m.text}]
                )
                bot_luna.send_message(cid, res.choices[0].message.content)

        except Exception as e:
            print(f"Err V58: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    if bot_luna:
        time.sleep(20)
        bot_luna.delete_webhook(drop_pending_updates=True)
        print("🚀 Luna V58 Online. Pronto al Debug.")
        bot_luna.polling(none_stop=True)
