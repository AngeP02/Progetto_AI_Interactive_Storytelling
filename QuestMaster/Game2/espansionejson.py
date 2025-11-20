# ------------------------------------------------------------
# GENERATORE DI GRAFO NARRATIVO DA PDDL + SAS + LORE
# ------------------------------------------------------------
# Questo script:
# 1. Legge domain.pddl, problem.pddl, sas_plan, lore.md
# 2. Costruisce un prompt robusto
# 3. Chiama le API OpenAI tramite modello GPT-4.1 o GPT-5.1
# 4. Restituisce un grafo narrativo in italiano
#
# Usa:
#   python main.py
#
# ------------------------------------------------------------
import os

from openai import OpenAI
import sys
from dotenv import load_dotenv
load_dotenv()


# 🔑 INSERISCI QUI LA TUA API KEY
API_KEY = os.environ.get("OPENAI_API_KEY")


def read_file(path):
    """Legge un file di testo e ritorna il contenuto."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERRORE: File non trovato -> {path}")
        sys.exit(1)


def build_prompt(domain, problem, sas_plan, lore):
    """Costruisce il prompt inviato al modello."""
    return f"""
Sei un sistema che trasforma un DOMAIN PDDL, un PROBLEM PDDL,
un piano SAS e un LORE narrativo in un GRAFO NARRATIVO in italiano.

Il grafo finale deve:
- Essere narrativo ma derivato logicamente dal piano SAS
- Seguire il mondo descritto nel lore (Neo-Eden, detective, noir cyberpunk)
- Avere nodi narrativi chiari (N1, N2, N3…)
- Mostrare contesto → scelte → conseguenze
- Integrare le azioni del piano come eventi nella storia
- Finire con una conclusione coerente con gli obiettivi del problem PDDL


----------------------------------------
DOMAIN PDDL:
{domain}

----------------------------------------
PROBLEM PDDL:
{problem}

----------------------------------------
SAS PLAN:
{sas_plan}

----------------------------------------
LORE:
{lore}
----------------------------------------

FORMAT DEL RISULTATO DESIDERATO:
Un grafo narrativo come questo esempio:

NODO 1 – Contesto iniziale  
   - descrizione  
   - scelte possibili

NODO 2 – Avanzamento narrativo  
   - cosa succede  
   - scelte possibili  

NODO 3 – … ecc.

CONCLUSIONE – risultato derivato dal goal PDDL.

Ora genera il grafo narrativo completo.
"""


def generate_graph(prompt):
    client = OpenAI(api_key=API_KEY)

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    # Correzione: message è un oggetto, non un dict
    return response.choices[0].message.content



def main():
    print("🔄 Caricamento file...")
    BASE_PATH = r"C:\Users\ANGELICA\Desktop\ANGELICA\UNICAL\MAGISTRALE\I ANNO\SECONDO SEMESTRE\INTELLIGENZA ARTIFICIALE\PROGETTO\CODICE\QuestMaster"
    domain = read_file(os.path.join(BASE_PATH, "ChatBot/pddl_output/domain.pddl"))
    problem = read_file(os.path.join(BASE_PATH,"ChatBot/pddl_output/problem.pddl"))
    sas_plan = read_file(os.path.join(BASE_PATH,"ChatBot/pddl_output/sas_plan"))
    lore = read_file(os.path.join(BASE_PATH,"Lore/Generated_Lore/Lore.md"))

    print("🔧 Costruzione prompt...")
    prompt = build_prompt(domain, problem, sas_plan, lore)

    print("🤖 Invio a modello OpenAI...")
    output = generate_graph(prompt)

    print("\n=========================== RISPOSTA GPT ===========================\n")
    print(output)
    print("\n====================================================================\n")


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
