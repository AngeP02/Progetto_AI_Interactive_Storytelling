import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
API_KEY = os.environ.get("OPENAI_API_KEY")

if API_KEY is None:
    print("ERRORE: Variabile OPENAI_API_KEY non trovata nel file .env!")
    sys.exit(1)


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ ERRORE: File non trovato -> {path}")
        sys.exit(1)


def save_to_file(content, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successo! Il file '{filename}' è stato creato.")
    except IOError as e:
        print(f"Errore nel salvataggio del file: {e}")


def generate_quest_plan(pddl_content, lore_content):
    prompt = f"""
    Sei un esperto Game Designer e Scrittore Tecnico. 
    Il tuo compito è creare un "File Scenario Guida" (Quest Plan) che servirà come cervello per un gioco testuale interattivo. 
    Devi unire le regole logiche (PDDL) con l'atmosfera narrativa (Lore) in un unico documento strutturato.

    --- INIZIO DATI PDDL (LOGICA) ---
    {pddl_content}
    --- FINE DATI PDDL ---

    --- INIZIO DATI LORE (TRAMA E VINCOLI) ---
    {lore_content}
    --- FINE DATI LORE ---

    ISTRUZIONI SPECIALI PER I VINCOLI:
    Analizza attentamente il testo della LORE sopra. Cerca le sezioni o frasi che specificano:
    1. "Branching Factor" (Ramificazione delle scelte).
    2. "Depth Constraints" (Lunghezza/Profondità della storia).
    Estrai i valori numerici (se è un range come "7-12", usa il valore massimo, es. 12).

    Genera un output formattato in MARKDOWN, seguendo ESATTAMENTE questa struttura:

    # SCENARIO GUIDA: [Titolo dell'Avventura]

    ## 1. CONTESTO NARRATIVO
    [Descrizione breve dell'ambientazione, del protagonista e del tono della storia basato sul Lore]

    ## 2. STATO INIZIALE
    - **Luogo di partenza:** [Dove si trova il giocatore]
    - **Inventario Iniziale:** [Cosa possiede]
    - **Elementi Chiave nella stanza:** [Oggetti o entità visibili inizialmente]

    ## 3. REGOLE DEL MONDO (Logica Semplificata)
    [Traduci le azioni PDDL in regole "Se... Allora..." leggibili. Esempio: "Per aprire X serve Y"]

    ## 4. OBIETTIVO FINALE (GOAL)
    [Qual è la condizione di vittoria]

    ## 5. SEQUENZA DI EVENTI (Suggerita)
    [Una breve scaletta dei passaggi logici per vincere, derivata dal piano PDDL]

    ## 6. VINCOLI DI GIOCO
    - **MaxDepth:** [Inserisci SOLO il numero intero estratto dalla Lore, es. 12]
    - **Branching:** [Inserisci SOLO il numero intero estratto dalla Lore, es. 3]
    """

    print("...Invio richiesta all'IA per generare il Quest Plan...")

    client = OpenAI(api_key=API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content


def run_quest_plan_generation():
    BASE_PATH = r"C:\Users\ANGELICA\Desktop\ANGELICA\UNICAL\MAGISTRALE\I ANNO\SECONDO SEMESTRE\INTELLIGENZA ARTIFICIALE\PROGETTO\CODICE\QuestMaster"
    path_domain = os.path.join(BASE_PATH, "ChatBot/pddl_output/domain.pddl")
    path_problem = os.path.join(BASE_PATH, "ChatBot/pddl_output/problem.pddl")
    path_lore = os.path.join(BASE_PATH, "Lore/Generated_Lore/Lore.md")
    domain_content = read_file(path_domain)
    problem_content = read_file(path_problem)
    lore_content = read_file(path_lore)
    full_pddl_content = f"*** DOMAIN PDDL ***\n{domain_content}\n\n*** PROBLEM PDDL ***\n{problem_content}"
    plan_content = generate_quest_plan(full_pddl_content, lore_content)
    output_filename = "quest_plan.md"
    save_to_file(plan_content, output_filename)
    return plan_content

if __name__ == "__main__":
   run_quest_plan_generation()