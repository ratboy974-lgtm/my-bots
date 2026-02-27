# --- MOTORE FOTO (DOWNLOAD CON SUPER-RETRY) ---
def genera_foto_luna(testo_utente):
    url = "https://fal.run/fal-ai/flux/dev"
    headers = {"Authorization": f"Key {FAL_K}", "Content-Type": "application/json"}
    prompt_puro = testo_utente.lower().replace("foto", "").replace("selfie", "").strip()
    full_prompt = f"Upper body shot of Luna, stunning 24yo italian girl, {prompt_puro}, detailed skin, realistic, 8k masterpiece"
    
    try:
        res = requests.post(url, headers=headers, json={"prompt": full_prompt, "seed": random.randint(1, 999999)}, timeout=60)
        if res.status_code == 200:
            img_url = res.json()['images'][0]['url']
            
            # Aumentiamo i tentativi e il tempo di attesa tra uno e l'altro
            for i in range(5):
                time.sleep(3 + i) # Aspetta 3s, poi 4s, poi 5s...
                try:
                    img_res = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                    if img_res.status_code == 200:
                        peso_file = len(img_res.content)
                        # Se il file è almeno 30KB, di solito è già visibile
                        if peso_file > 30000:
                            print(f"✅ Foto pronta! Peso: {peso_file} bytes al tentativo {i+1}")
                            return img_res.content
                except:
                    continue
                print(f"⚠️ Tentativo {i+1}: file ancora troppo leggero...")
    except Exception as e:
        print(f"❌ Errore critico: {e}")
    return None
