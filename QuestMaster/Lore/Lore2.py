import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Carica le variabili d'ambiente (API Key)
load_dotenv()
API_KEY = os.environ.get("OPENAI_API_KEY")


# --- LLM Helper per GPT ---

class LoreGeneratorLLM:
    """Helper per le chiamate OpenAI (GPT), specifico per la generazione della Lore."""

    def __init__(self):
        if not API_KEY:
            logger.error("❌ OPENAI_API_KEY mancante nel file .env!")
            self.client = None
        else:
            self.client = OpenAI(api_key=API_KEY)

        self.model = "gpt-4o"  # Usa gpt-4o per la massima qualità creativa

    def call_gpt(self, prompt, system_prompt):
        """Esegue una chiamata chat completion a GPT."""
        if not self.client:
            return "Errore: API Key non configurata."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,  # Alta creatività per la lore
                max_tokens=1500  # Abbastanza spazio per una lore dettagliata
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Errore chiamata OpenAI per Lore: {e}")
            return f"Errore: Impossibile generare la lore. Dettagli: {str(e)}"


def get_pddl_constraints(length: str) -> dict:
    """Restituisce i vincoli logici (Branching e Depth) in base alla lunghezza della storia."""
    length_map = {
        "Short": {
            "branching": "2-3",  # Meno scelte per stato
            "depth": "3-6"  # Percorso breve
        },
        "Medium": {
            "branching": "3-4",
            "depth": "7-12"
        },
        "Long": {
            "branching": "4-5",  # Più scelte e complessità per stato
            "depth": "13-25"  # Percorso lungo e profondo
        }
    }
    # Usa 'Medium' come fallback se 'length' non è nel dizionario (gestisce stringhe parziali)
    for key in length_map:
        if key in length:
            return length_map[key]
    return length_map["Medium"]


# --- Funzione Principale di Generazione Lore ---

def generate_lore_document(config: dict) -> str:
    """
    Genera un documento di lore (ambientazione e contesto) basato sulla configurazione della quest
    e lo salva come file Markdown.

    Args:
        config (dict): Dizionario di configurazione della quest (genere, tema, tono, ecc.).

    Returns:
        str: Il percorso completo del file di lore generato.
    """
    llm = LoreGeneratorLLM()

    # Estrazione dei parametri
    genre = config.get('genre', 'Fantasy')
    length = config.get('length', 'Medium')
    tone = config.get('tone', 'Adventurous')
    theme = config.get('theme', 'A simple quest.')

    # Recupera i vincoli numerici per inserirli nel prompt
    constraints = get_pddl_constraints(length)
    branching_txt = constraints["branching"]
    depth_txt = constraints["depth"]

    # 1. Preparazione del Prompt
    system_prompt = f"""Sei un autore di storie classiche e un Game Master esperto. Il tuo compito è creare un'ambientazione (lore) ricca, coerente e affascinante per una storia interattiva, che sarà poi utilizzata da un sistema di pianificazione logica (PDDL) e da un LLM narrativo.

Le specifiche della storia sono:
- **Genere:** {genre}
- **Lunghezza/Complessità:** {length}
- **Tono Narrativo:** {tone}
- **Tema/Trama Principale:** {theme}

IMPORTANTE: I vincoli di pianificazione logica devono essere **integrati nel tuo testo narrativo e nel riepilogo finale** in modo esplicito:
- **Fattore di Ramificazione (Branching Factor):** {branching_txt} scelte per nodo.
- **Vincoli di Profondità (Depth Constraints):** Tra {depth_txt} passi per completare la storia.

Struttura la tua risposta in sezioni chiare con i seguenti titoli Markdown ESATTI:
## Contesto Iniziale
## Personaggi Principali (Giocatore e PNG chiave)
## Fazioni/Gruppi di Interesse
## Luoghi Chiave
## Obiettivi Iniziali
## Branching Factor (minimo e massimo)
## Depth Constraints (minimo e massimo)

Assicurati che il tono sia {tone} e che la descrizione sia appropriata per un gioco {genre}. Fornisci dettagli sufficienti per creare un mondo coinvolgente.
"""

    prompt = f"Genera la lore completa per una quest con il tema: '{theme}'. Usa la struttura richiesta."

    # 2. Chiamata all'LLM (GPT)
    logger.info("✍️  Generazione Lore con GPT-4o in corso...")
    lore_content = llm.call_gpt(prompt, system_prompt)

    if "Errore:" in lore_content:
        logger.error("Fallita la generazione LLM della Lore, uso il contenuto di fallback.")
        lore_content = f"""# ⚠️ Lore di Fallback
**Genere:** {genre}
**Lunghezza:** {length}
**Tono:** {tone}
**Tema:** {theme}

Impossibile connettersi a OpenAI.
**Contesto Iniziale:** Il mondo è avvolto nel mistero a causa di un errore di connessione.
**Obiettivi Iniziali:** Ripristinare la chiave API.
**Branching Factor:** {branching_txt}
**Depth Constraints:** {depth_txt}
"""

    # 3. Salvataggio del Documento

    # Determina la cartella di output
    current_dir = Path(__file__).resolve().parent
    output_dir = current_dir / "Generated_Lore"
    output_dir.mkdir(parents=True, exist_ok=True)

    file_name = "Lore.md"
    file_path = output_dir / file_name

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            # Intestazione con metadati
            f.write(f"# Documento di Lore: {theme}\n\n")
            f.write(f"**Genere:** {genre} | **Tono:** {tone} | **Lunghezza:** {length}\n")
            f.write(f"**Generato da:** GPT-4o\n\n")
            f.write("---\n\n")
            f.write(lore_content)

        logger.info(f"✅ Lore salvata con successo: {file_path}")
        return str(file_path)

    except Exception as e:
        logger.error(f"Errore nel salvataggio del file di lore: {e}")
        return f"Errore: Impossibile salvare il file di lore. Dettagli: {e}"


# Esempio di utilizzo per il debug (opzionale)
if __name__ == '__main__':
    # Esempio di configurazione
    test_config = {
        "genre": "Cyberpunk",
        "length": "Long (10+ min)",
        "tone": "Dark and Mysterious",
        "graphics": "Illustrated",
        "theme": "Un detective robotico deve risolvere un omicidio in una metropoli corrotta."
    }
    print("🚀 Avvio test generazione Lore (GPT)...")
    path = generate_lore_document(test_config)
    print(f"\n📂 Lore generata e salvata in: {path}")