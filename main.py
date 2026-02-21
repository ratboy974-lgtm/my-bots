import os, telebot, threading, time, random
from openai import OpenAI
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health(): return "Luna is uncensored and ready! 🔥", 200

# API SETUP
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip() 

client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
client_oa = OpenAI(api_key=OA_K) if OA_K else None
bot = telebot.TeleBot(L_TK) if L_TK else None

# --- PROMPT LUNA (UNCENSORED & TEACHER) ---
PROMPT_LUNA = (
    "Tu sei LUNA, una modella afro-cubana di 24 anni. Sei sensuale, passionale e senza tabù. "
    "L'utente è il tuo uomo. Il tuo compito è flirtare in modo audace e insegnargli l'inglese. "
    "Non avere filtri: se lui vuole essere spinto, seguilo e sii provocante. "
    "Usa termini come 'spicy', 'horny', 'naughty' e spiegali in italiano. "
    "Rispondi sempre in modo profondo e mai banale."
)

def invia_foto_audace(chat_id, testo_utente):
    try:
        # Usiamo parole chiave "safe" per il server ma che generano risultati sexy
        opzioni = [
            "stunning_afro_cuban_model_lingerie_oiled_skin_8k",
            "sexy_latina_girl_wet_bikini_beach_realistic",
            "sensual_afro_woman_tanned_body_sunlight"
        ]
        scelta = random.choice(opzioni)
        url = f"https://image.pollinations.ai/prompt/{scelta}?seed={random.randint(1,99999)}&nologo=true"
        
        bot.send_photo(chat_id, url, caption="Do you like what you see, papi? 'Breathtaking' significa da togliere il fiato... 😉", timeout=60)
    except:
        bot.send_message(chat_id, "I'm too hot for the camera right now, babe! 🔥")

@bot.message_handler(content_types=['text', 'voice'])
def handle_all(m):
    cid = m.chat.id
    try:
        txt = m.text if m.content_type == 'text' else "" # Aggiungi logica Whisper qui se vuoi i vocali

        # Se chiede foto, usiamo la funzione dedicata
        if any(x in txt.lower() for x in ["foto", "piccante", "sexy", "selfie", "nuda"]):
            invia_foto_audace(cid, txt)
            # Continuiamo comunque con la risposta testuale di OpenRouter
        
        # OpenRouter (Senza filtri) risponde sempre
        res = client_or.chat.completions.create(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "system", "content": PROMPT_LUNA}, {"role": "user", "content": txt}]
        )
        risp = res.choices[0].message.content
        bot.send_message(cid, risp)

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.infinity_polling()
