import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LoreGeneratorLLM:
    """Helper per le chiamate Ollama, specifico per la generazione della Lore."""

    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3"

    def call_ollama(self, prompt, system_prompt):
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,  # Aumento la temperatura per più creatività
                    "top_p": 0.9,
                    "num_predict": 1000  # Aumento la predizione per una risposta più lunga
                }
            }

            response = requests.post(self.ollama_url, json=payload, timeout=300)
            response.raise_for_status()

            result = response.json()
            return result.get('response', '').strip()

        except requests.exceptions.RequestException as e:
            logger.error(f"Errore chiamata Ollama per Lore: {e}")
            return "Errore: Impossibile generare la lore. Controlla Ollama."
        except Exception as e:
            logger.error(f"Errore generico in LoreGeneratorLLM: {e}")
            return "Errore imprevisto durante la generazione della lore."

def get_pddl_constraints(length: str) -> dict:
    """Restituisce i vincoli logici (Branching e Depth) in base alla lunghezza della storia."""
    length_map = {
        "Short": {
            "branching": "2-3",  # Meno scelte per stato
            "depth": "3-6"      # Percorso breve
        },
        "Medium": {
            "branching": "3-4",
            "depth": "7-12"
        },
        "Long": {
            "branching": "4-5",  # Più scelte e complessità per stato
            "depth": "13-25"     # Percorso lungo e profondo
        }
        # Aggiungi altri livelli se la tua variabile length lo prevede
    }
    # Usa 'Medium' come fallback se 'length' non è nel dizionario
    return length_map.get(length, length_map["Medium"])

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
    graphics = config.get('graphics', 'Illustrated')
    theme = config.get('theme', 'A simple quest.')

    # 1. Preparazione del Prompt
    system_prompt = f"""Sei un autore di storie classiche e non e un Game Master esperto. Il tuo compito è creare un'ambientazione (lore) ricca, coerente e affascinante per una storia interattiva, che sarà poi utilizzata da un sistema di pianificazione logica (PDDL) e da un LLM narrativo.

Le specifiche della storia sono:
- **Genere:** {genre}
- **Lunghezza/Complessità:** {length}
- **Tono Narrativo:** {tone}
- **Tema/Trama Principale:** {theme}
I vincoli di pianificazione logica che definiscono la complessità del PDDL devono essere **integrati nel tuo testo narrativo e nel riepilogo finale** in modo che siano coerenti con la storia che stai creando:
- **Fattore di Ramificazione (Branching Factor):** Deve rispettare la length della storia.
- **Vincoli di Profondità (Depth Constraints):**  Deve rispettare la length della storia.

Struttura la tua risposta in sezioni chiare con i seguenti titoli Markdown:
## Contesto Iniziale
## Personaggi Principali (Giocatore e PNG chiave)
## Fazioni/Gruppi di Interesse
## Luoghi Chiave
## Obiettivi Iniziali
## Branching Factor (minimo e massimo)
## Depth Constraints (minimo e massimo)
Assicurati che il tono sia {tone} e che la descrizione sia appropriata per un gioco {genre}. Fornisci dettagli sufficienti per creare un mondo coinvolgente.
"""

    # Il prompt effettivo può essere semplice dato che il system_prompt è molto dettagliato
    prompt = f"Genera la lore completa per una quest con il tema: '{theme}'."

    # 2. Chiamata all'LLM
    lore_content = llm.call_ollama(prompt, system_prompt)

    if "Errore:" in lore_content:
        # Se la chiamata LLM fallisce, genera una lore di fallback
        logger.error("Fallita la generazione LLM della Lore, uso il contenuto di fallback.")
        lore_content = f"""# ⚠️ Lore di Fallback
**Genere:** {genre}
**Lunghezza:** {length}
**Tono:** {tone}
**Tema:** {theme}

Impossibile connettersi a Ollama. Questa è una lore di fallback.
**Contesto Iniziale:** Il mondo di Eldoria sta affrontando una minaccia misteriosa.
**Obiettivi Iniziali:** Scoprire la fonte della minaccia.
"""

    # 3. Salvataggio del Documento

    # Creazione della cartella di destinazione (all'interno di QuestMaster)
    # Calcolo del percorso: BASE_DIR era QuestMaster, quindi 'Lore' è la destinazione.
    # In base al tuo codice Flask, BASE_DIR è QuestMaster.
    # Quindi, la lore verrà salvata in QuestMaster/Lore/Generated_Lore/

    # Trova la directory del modulo corrente (QuestMaster/Lore/)
    current_dir = Path(__file__).resolve().parent
    output_dir = current_dir / "Generated_Lore"
    output_dir.mkdir(parents=True, exist_ok=True)  # Crea la cartella se non esiste

    # Nome del file basato sul tema per renderlo unico
    safe_theme = "".join(c for c in theme if c.isalnum() or c.isspace()).rstrip()
    if len(safe_theme) > 30:
        safe_theme = safe_theme[:30]

    # Aggiungo un identificatore per evitare sovrascritture in caso di temi simili
    import time
    timestamp = int(time.time())
    file_name = f"Lore.md"
    file_path = output_dir / file_name

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            # Aggiungo l'intestazione con i parametri per chiarezza
            f.write(f"# Documento di Lore: {theme}\n\n")
            f.write(f"**Genere:** {genre} | **Tono:** {tone} | **Lunghezza:** {length}\n\n")
            f.write("---\n\n")
            f.write(lore_content)
        logger.info(f"Lore document saved successfully: {file_path}")
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
        "theme": "Un detective robotico deve risolvere un omicidio in una metropoli corrotta dominata dalle corporazioni."
    }
    print("Avvio la generazione della Lore di test...")
    path = generate_lore_document(test_config)
    print(f"\nLore generata e salvata in: {path}")