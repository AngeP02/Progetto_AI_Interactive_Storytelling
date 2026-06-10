```markdown
# SCENARIO GUIDA: La Rinascita del Drago Thalorax

## 1. CONTESTO NARRATIVO
Nel cuore del regno di Eldoria, un antico drago chiamato Thalorax il Conquistatore minaccia di risvegliarsi, portando distruzione. L'Eroe Prescelto, un giovane avventuriero con un'eredità magica, deve fermare il drago con l'aiuto di potenti alleati. La storia è un'epica avventura fantasy in cui il fato del regno è appeso a un filo.

## 2. STATO INIZIALE
- **Luogo di partenza:** Ingresso della Montagna delle Ombre
- **Inventario Iniziale:** Nessun oggetto iniziale
- **Elementi Chiave nella stanza:** Chiave di bronzo

## 3. REGOLE DEL MONDO (Logica Semplificata)
- Se l'Eroe Prescelto si trova in una stanza con una chiave, allora può raccogliere la chiave.
- Se l'Eroe Prescelto possiede la chiave corretta ed è davanti a una porta chiusa, allora può sbloccare la porta.
- Se una porta è sbloccata, allora l'Eroe Prescelto può attraversarla per muoversi in una nuova stanza.

## 4. OBIETTIVO FINALE (GOAL)
Raggiungere la stanza del tesoro di Thalorax.

## 5. SEQUENZA DI EVENTI (Suggerita)
- Passo 1: pick-key eroe_prescelto chiave_bronzo ingresso_montagna_ombre → L'Eroe Prescelto raccoglie la Chiave di Bronzo all'ingresso della Montagna delle Ombre.
- Passo 2: unlock eroe_prescelto chiave_bronzo porta_principale_eldoria ingresso_montagna_ombre → L'Eroe Prescelto usa la Chiave di Bronzo per sbloccare la Porta Principale di Eldoria.
- Passo 3: move eroe_prescelto ingresso_montagna_ombre sala_regia porta_principale_eldoria → L'Eroe Prescelto attraversa la Porta Principale e si sposta nella Sala Regia.
- Passo 4: pick-key eroe_prescelto chiave_oro sala_regia → L'Eroe Prescelto trova e raccoglie la Chiave d'Oro nella Sala Regia.
- Passo 5: unlock eroe_prescelto chiave_oro porta_tesoro sala_regia → L'Eroe Prescelto usa la Chiave d'Oro per sbloccare la Porta del Tesoro.
- Passo 6: move eroe_prescelto sala_regia stanza_tesoro_thalorax porta_tesoro → L'Eroe Prescelto attraversa la Porta del Tesoro e arriva nella Stanza del Tesoro di Thalorax.

## 6. VINCOLI DI GIOCO
- **MaxDepth:** 12
- **Branching:** 3
```