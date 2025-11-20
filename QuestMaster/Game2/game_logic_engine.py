import os
from openai import OpenAI
from dotenv import load_dotenv
import sys
import json

# 🔄 Carica le variabili dal file .env
load_dotenv()
API_KEY = os.environ.get("OPENAI_API_KEY")

if API_KEY is None:
    print("❌ ERRORE: Variabile OPENAI_API_KEY non trovata nel file .env!")
    sys.exit(1)

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERRORE: File non trovato -> {path}")
        sys.exit(1)

def build_prompt(domain, problem, sas_plan, lore, branching_factor=6, depth=4):
    """
    Costruisce un prompt dettagliato che richiede:
    - tutti i rami espansi secondo branching_factor
    - profondità del grafo pari a depth
    - ogni scelta porta al goal
    - output sia testuale che in JSON
    """
    return f"""
Sei un sistema che trasforma un DOMAIN PDDL, un PROBLEM PDDL,
un piano SAS e un LORE narrativo in un GRAFO NARRATIVO COMPLETO in italiano.

REQUISITI:
- Tutti i rami devono essere espansi fino a profondità {depth}.
- Ogni nodo deve avere {branching_factor} scelte possibili.
- Tutte le scelte devono portare al raggiungimento del goal PDDL.
- Il grafo deve essere coerente con le azioni SAS e il lore.
- Restituisci l'output in forma testuale leggibile (come i nodi precedenti).

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

Genera ora il grafo completo, rispettando branching e profondità, con ogni scelta che porta al goal.
"""

def generate_graph(prompt):
    client = OpenAI(api_key=API_KEY)

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content

def main():
    print("🔄 Caricamento file...")

    print("🔄 Caricamento file...")
    BASE_PATH = r"C:\Users\ANGELICA\Desktop\ANGELICA\UNICAL\MAGISTRALE\I ANNO\SECONDO SEMESTRE\INTELLIGENZA ARTIFICIALE\PROGETTO\CODICE\QuestMaster"
    domain = read_file(os.path.join(BASE_PATH, "ChatBot/pddl_output/domain.pddl"))
    problem = read_file(os.path.join(BASE_PATH,"ChatBot/pddl_output/problem.pddl"))
    sas_plan = read_file(os.path.join(BASE_PATH,"ChatBot/pddl_output/sas_plan"))
    lore = read_file(os.path.join(BASE_PATH,"Lore/Generated_Lore/Lore.md"))


    # Puoi settare branching_factor e depth come da lore
    branching_factor = 6
    depth = 4

    print("🔧 Costruzione prompt...")
    prompt = build_prompt(domain, problem, sas_plan, lore, branching_factor, depth)

    print("🤖 Invio a modello OpenAI...")
    output = generate_graph(prompt)

    print("\n=========================== RISPOSTA GPT ===========================\n")
    print(output)
    print("\n====================================================================\n")

    # Salvataggio su file testuale
    with open("grafo_completo.txt", "w", encoding="utf-8") as f:
        f.write(output)
    print("💾 Grafo salvato su 'grafo_completo.txt'")

    # Proviamo a salvare anche JSON se il modello lo restituisce
    try:
        start_json = output.index("{")
        json_content = output[start_json:]
        parsed_json = json.loads(json_content)
        with open("grafo_completo.json", "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)
        print("💾 Grafo JSON salvato su 'grafo_completo.json'")
    except Exception:
        print("⚠️ JSON non trovato o malformato. Controlla l'output.")

if __name__ == "__main__":
    main()
