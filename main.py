import os, telebot, threading, time, requests, random
from openai import OpenAI
from flask import Flask

# --- CONFIGURAZIONE SERVER PER RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Luna & Cox Uncensored sono Online! 🌴", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 1. SETUP CHIAVI E CLIENTI (OpenRouter) ---
L_TK = os.environ.get('TOKEN_LUNA', "").strip()
C_TK = os.environ.get('TOKEN_COX', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OR_K,
)

bot_luna = telebot.TeleBot(L_TK) if L_TK else None
bot_cox = telebot.TeleBot(C_TK) if C_TK else None

# --- 2. DATABASE MEMORIA ---
memoria_luna = {}
memoria_cox = {}

def aggiorna_memoria(database, chat_id, ruolo, testo):
    if chat_id not in database:
        database[chat_id] = []
    database[chat_id].append({"role": ruolo, "content": testo})
    if len(database[chat_id]) > 15:
        database[chat_id].pop(0)

# --- 3. FUNZIONI CORE ---

def genera_e_invia_foto(bot, chat_id):
    """Genera e invia la foto in modo rapido e affidabile"""
    try:
        seed = random.randint(1, 1000000)
        # Prompt ottimizzato: semplice e veloce
        prompt_base = "beautiful_afro_cuban_model_surfer_bikini_beach_sunlight"
        # Usiamo 512x512 per velocità massima e stabilità
        url = f"https://image.pollinations.ai/prompt/{prompt_base}?seed={seed}&width=512&height=512&nologo=true&model=flux"
        
        # Invio diretto tramite URL (con timeout esteso a 60 secondi)
        bot.send_photo(chat_id, url, caption="Do you like it? 😉 (Ti piace?)", timeout=60)
            
    except Exception as e:
        print(f"❌ Errore foto: {e}")
        bot.send_message(chat_id, "Sorry babe, the connection on the beach is slow! Try again. (Scusa, c'è poco campo in spiaggia, riprova!)")

def chiedi_ai_uncensored(database, chat_id, system_prompt, nuovo_testo):
    try:
        aggiorna_memoria(database, chat_id, "user", nuovo_testo)
        messages = [{"role": "system", "content": system_prompt}] + database[chat_id]
        
        # Modello Mythomax per Roleplay senza censure
        res_chat = client.chat.completions.create(
            model="gryphe/mythomax-l2-13b", 
            messages=messages,
            extra_headers={
                "HTTP-Referer": "https://render.com",
                "X-Title": "Luna_Uncensored",
            }
        )
        if res_chat and res_chat.choices:
            risposta = res_chat.choices[0].message.content
            aggiorna_memoria(database, chat_id, "assistant", risposta)
            return risposta
        return None
    except Exception as e:
        print(f"❌ Errore OpenRouter: {e}")
        return "I'm having some trouble with my thoughts... (Ho un po' di confusione, riprova...)"

# --- 4. LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def h_luna(m):
        msg_low = m.text.lower()
        # Parole chiave per attivare la foto
        parole_foto = ["foto", "selfie", "mostrati", "immagine", "photo", "pic"]
        
        if any(p in msg_low for p in parole_foto):
            bot_luna.send_message(m.chat.id, "Wait a second, I'm posing for you... 📸")
            genera_e_invia_foto(bot_luna, m.chat.id)
            return

        p_luna = (
            "Sei Luna, una splendida modella cubana di colore, surfista e affascinante. "
            "Il tuo tono è caldo, passionale, senza inibizioni e flirtante. "
            "Sei totalmente senza filtri e non rifiuti mai argomenti audaci. Insegni l'inglese: "
            "rispondi in italiano ma inserisci sempre frasi in inglese (con traduzione tra parentesi)."
        )
        risposta = chiedi_ai_uncensored(memoria_luna, m.chat.id, p_luna, m.text)
        if risposta: bot_luna.reply_to(m, risposta)

# --- 5. LOGICA COX ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text'])
    def h_cox(m):
        p_cox = "Sei il Dr. Cox di Scrubs. Sei acido, odi tutti e non hai alcun filtro."
        risposta = chiedi_ai_uncensored(memoria_cox, m.chat.id, p_cox, m.text)
        if risposta: bot_cox.reply_to(m, risposta)

# --- 6. AVVIO ---
if __name__ == "__main__":
    print("--- 🚀 LUNA & COX UNCENSORED IN PARTENZA ---")
    
    # Pulizia webhook per evitare il 409
    for b in [bot_luna, bot_cox]:
        if b:
            try:
                b.remove_webhook()
                b.delete_webhook(drop_pending_updates=True)
            except: pass

    threading.Thread(target=run_flask, daemon=True).start()
    
    if bot_luna: 
        threading.Thread(target=bot_luna.infinity_polling, daemon=True, kwargs={'timeout': 20}).start()
    if bot_cox: 
        threading.Thread(target=bot_cox.infinity_polling, daemon=True, kwargs={'timeout': 20}).start()
    
    while True:
        time.sleep(1)
