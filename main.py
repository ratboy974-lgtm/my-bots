def genera_immagine(prompt_foto):
    # Ora il prompt è dinamico: usa quello che scrivi tu come base principale
    # Aggiungiamo istruzioni per evitare il 'close-up' fisso e variare l'inquadratura
    descrizione_dinamica = (
        f"A hyper-realistic photo of a beautiful 24-year-old girl named Luna. "
        f"She is {prompt_foto}. Cinematic composition, varied camera angles, "
        f"natural textures, detailed environment, no repetitive close-ups."
    )
    
    res = client_oa.images.generate(
        model="dall-e-3",
        prompt=descrizione_dinamica,
        size="1024x1024", n=1
    )
    return res.data[0].url
