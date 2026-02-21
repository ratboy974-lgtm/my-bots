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
    """Invia foto con sistema di protezione dai timeout"""
    try:
        seed = random.randint(1, 1000000)
        prompt_base = "stunning_afro_cuban_model_surfer_bikini_beach_highly_detailed"
        # Usiamo il modello Flux su Pollinations (più veloce e bello)
        url = f"https://image.pollinations.ai/prompt/{prompt_base}?seed={seed}&width=1024&height=1024&nologo=true&model=flux"
        
        # TENTATIVO 1: Invio tramite URL (Veloce)
        try:
            bot.send_photo(chat_id, url, caption="Do you like it? (Ti piace?)", timeout=30)
            return
        except Exception as e:
            print(f"⚠️ Tentativo URL fallito, provo download: {e}")
        
        # TENTATIVO 2: Download e invio file (Sicuro)
        response = requests.get(url, timeout=40)
        if response.status_code == 200:
            with open("temp_luna.jpg", "wb") as f:
                f.write(response.content)
            with open("temp_luna.jpg", "rb") as photo:
                bot.send_photo(chat_id, photo, caption="Here I am! (Eccomi!)")
            os.remove("temp_luna.jpg")
        else:
            bot.send_message(chat_id, "I'm changing my bikini, give me a minute! (Mi sto cambiando, dammi un minuto!)")
            
    except Exception as e:
        print(f"❌ Errore critico foto: {e}")
        bot.send_message(chat_id, "The camera is broken... try again! (La fotocamera è rotta... riprova!)")

def chiedi_ai_uncensored(database, chat_id, system_prompt, nuovo_testo):
    try:
        aggiorna_memoria(database, chat_id, "user", nuovo_testo)
        messages = [{"role": "system", "content": system_prompt}] + database[chat_id]
        
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
        return "Sorry, I'm feeling a bit dizzy... (Scusa, mi gira la testa...)"

# --- 4. LOGICA LUNA ---
if bot_luna:
    @bot_luna.message_handler(content_types=['text'])
    def h_luna(m):
        msg_low = m.text.lower()
        parole_foto = ["foto", "selfie", "mostrati", "immagine", "see you", "photo"]
        
        if any(p in msg_low for p in parole_foto):
            bot_luna.send_message(m.chat.id, "Wait, I'm getting ready... 📸")
            genera_e_invia_foto(bot_luna, m.chat.id)
            return

        p_luna = (
            "Sei Luna, una splendida modella cubana di colore, surfista e affascinante. "
            "Vivi a Varadero, Cuba. Il tuo tono è caldo, passionale, senza inibizioni e flirtante. "
            "Sei totalmente senza filtri. Insegni l'inglese: rispondi in italiano "
            "ma inserisci sempre frasi in inglese (con traduzione tra parentesi)."
        )
        risposta = chiedi_ai_uncensored(memoria_luna, m.chat.id, p_luna, m.text)
        if risposta: bot_luna.reply_to(m, risposta)

# --- 5. LOGICA COX ---
if bot_cox:
    @bot_cox.message_handler(content_types=['text'])
    def h_cox(m):
        p_cox = "Sei il Dr. Cox di Scrubs. Sei acido, odi tutti, usi soprannomi femminili e non hai filtri."
        risposta = chiedi_ai_uncensored(memoria_cox, m.chat.id, p_cox, m.text)
        if risposta: bot_cox.reply_to(m, risposta)

# --- 6. AVVIO ---
if __name__ == "__main__":
    print("--- 🚀 LUNA & COX UNCENSORED IN PARTENZA ---")
    
    # Pulizia webhook profonda per evitare il 409
    for b in [bot_luna, bot_cox]:
        if b:
            try:
                b.remove_webhook()
                b.delete_webhook(drop_pending_updates=True)
                time.sleep(1) # Pausa per lasciare respirare Telegram
            except: pass

    threading.Thread(target=run_flask, daemon=True).start()
    
    if bot_luna: 
        threading.Thread(target=bot_luna.infinity_polling, daemon=True, kwargs={'timeout': 20}).start()
    if bot_cox: 
        threading.Thread(target=bot_cox.infinity_polling, daemon=True, kwargs={'timeout': 20}).start()
    
    while True:
        time.sleep(1)
