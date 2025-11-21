import os
from openai import OpenAI
from dotenv import load_dotenv
import sys
import json
import re

# 🔄 Carica le variabili dal file .env
load_dotenv()
API_KEY = os.environ.get("OPENAI_API_KEY")

if API_KEY is None:
    print("❌ ERRORE: Variabile OPENAI_API_KEY non trovata nel file .env!")
    sys.exit(1)


def read_file(path):
    """Legge un file e ritorna il contenuto"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ ERRORE: File non trovato -> {path}")
        sys.exit(1)


def extract_graph_params(lore_text):
    """
    Estrae branching_factor e depth dal testo del lore
    Cerca pattern come "5-7" e "3-5"
    """
    print("📊 Estrazione parametri dal lore...")

    # Cerca il branching factor
    branching_match = re.search(
        r'branching factor.*?(\d+)-(\d+)',
        lore_text,
        re.IGNORECASE
    )

    # Cerca la profondità (depth)
    depth_match = re.search(
        r'depth.*?constraints.*?(\d+)-(\d+)',
        lore_text,
        re.IGNORECASE
    )

    if not branching_match or not depth_match:
        print("⚠️  AVVISO: Branching o Depth non trovati nel lore!")
        print("   Utilizzo valori di default: branching_factor=3, depth=3")
        return {
            "branching_factor": 6,
            "depth": 4,
            "branching_range": (2, 4),
            "depth_range": (2, 4)
        }

    branching_min = int(branching_match.group(1))
    branching_max = int(branching_match.group(2))
    depth_min = int(depth_match.group(1))
    depth_max = int(depth_match.group(2))

    # Calcola i valori medi
    branching_factor = (branching_min + branching_max) // 2
    depth = (depth_min + depth_max) // 2

    params = {
        "branching_factor": branching_factor,
        "depth": depth,
        "branching_range": (branching_min, branching_max),
        "depth_range": (depth_min, depth_max)
    }

    print(f"✓ Branching Factor trovato: {branching_min}-{branching_max} → Media: {branching_factor}")
    print(f"✓ Depth trovato: {depth_min}-{depth_max} → Media: {depth}")

    return params


def build_prompt(domain, problem, sas_plan, lore, branching_factor=6, depth=4):
    """
    Costruisce un prompt migliorato che specifica esattamente la struttura desiderata
    """
    convergence_depth = max(2, depth // 2)

    return f"""
    Sei un sistema che genera grafi narrativi interattivi logici e strutturati basati su PDDL, SAS e Lore.

### OBIETTIVO
Genera un grafo narrativo completo in italiano, con:
- Branching Factor fisso = {branching_factor}
- Profondità totale = {depth}
- Stati persistenti
- Tutti i rami convergono al goal finale
- Formato rigidissimo (vedi sotto)

### STRUTTURA OBBLIGATORIA
La numerazione segue questo schema:
- Profondità 0: Nodo 0
- Profondità 1: Nodo 1.1 … 1.{branching_factor}
- Profondità 2: Nodo 1.X.Y
- ...
- Profondità {depth - 1}: Nodo X.Y.Z... = GOAL finale

Ogni nodo DEVE contenere ESATTAMENTE:
1. Titolo
2. 3-4 frasi narrative (conseguenze logiche del nodo precedente)
3. **Stato:** elenco cumulativo delle informazioni scoperte
4. **Scegli:** {branching_factor} scelte numerate

### NODI FINALI
L’ultimo livello (profondità {depth - 1}) deve essere:
“GOAL RAGGIUNTO – Caso Risolto”
e deve:
- identificare l’assassino
- mostrare le prove raccolte
- spiegare la convergenza delle scelte

### REGOLE CRITICHE
- Nessun nodo può mancare
- Ogni nodo deve avere esattamente {branching_factor} scelte
- Nessun ramo può terminare prima della profondità {depth - 1}
- Stato sempre aggiornato e coerente
- Nessuna scelta generica: ogni scelta modifica lo stato

### MATERIALI DI INPUT
DOMAIN PDDL:
{domain}

PROBLEM PDDL:
{problem}

SAS PLAN:
{sas_plan}

LORE:
{lore}

### PRODUCI ORA IL GRAFO
Inizia con:
## Nodo 0
e termina con:
## FINE DEL GRAFO NARRATIVO
    """


def generate_graph(prompt):
    """Invia il prompt a GPT-4 e ottiene il grafo narrativo"""
    client = OpenAI(api_key=API_KEY)

    print("🤖 Invio prompt a OpenAI (GPT-4)...")
    print("   (Questo potrebbe richiedere 30-60 secondi...)")

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4096
    )

    return response.choices[0].message.content


def save_params_to_json(params):
    """Salva i parametri estratti in un file JSON"""
    with open("graph_params.json", "w", encoding="utf-8") as f:
        json.dump({
            "branching_factor": params["branching_factor"],
            "depth": params["depth"],
            "branching_range": f"{params['branching_range'][0]}-{params['branching_range'][1]}",
            "depth_range": f"{params['depth_range'][0]}-{params['depth_range'][1]}"
        }, f, indent=2, ensure_ascii=False)
    print("💾 Parametri salvati su 'graph_params.json'")


def main():
    print("\n" + "=" * 80)
    print("🎮 QUESTMASTER - GENERATORE DI GRAFI NARRATIVI INTERATTIVI")
    print("=" * 80 + "\n")

    print("🔄 Caricamento file...")

    # Cambia questo percorso con il tuo
    BASE_PATH = r"C:\Users\ANGELICA\Desktop\ANGELICA\UNICAL\MAGISTRALE\I ANNO\SECONDO SEMESTRE\INTELLIGENZA ARTIFICIALE\PROGETTO\CODICE\QuestMaster"

    try:
        domain = read_file(os.path.join(BASE_PATH, "ChatBot/pddl_output/domain.pddl"))
        problem = read_file(os.path.join(BASE_PATH, "ChatBot/pddl_output/problem.pddl"))
        sas_plan = read_file(os.path.join(BASE_PATH, "ChatBot/pddl_output/sas_plan"))
        lore = read_file(os.path.join(BASE_PATH, "Lore/Generated_Lore/Lore.md"))
    except SystemExit:
        print("\n❌ Impossibile continuare senza i file di input.")
        return

    print("✓ Tutti i file caricati correttamente\n")

    # 📊 ESTRAI I PARAMETRI DAL LORE
    params = extract_graph_params(lore)

    branching_factor = params["branching_factor"]
    depth = params["depth"]

    print()

    # ✅ AGGIORNA IL PROMPT PER UTILIZZARE QUESTI VALORI
    print("🔧 Costruzione del prompt migliorato...")
    prompt = build_prompt(
        domain,
        problem,
        sas_plan,
        lore,
        branching_factor=branching_factor,
        depth=depth
    )

    print("✓ Prompt costruito correttamente\n")

    # 🤖 GENERA IL GRAFO
    output = generate_graph(prompt)

    print("\n" + "=" * 80)
    print("✅ GENERAZIONE COMPLETATA!")
    print("=" * 80 + "\n")

    print("📝 ANTEPRIMA DEL GRAFO (primi 1000 caratteri):\n")
    print(output[:1000])
    print("\n... [grafo completo salvato nei file] ...\n")

    # 💾 SALVATAGGIO SU FILE TESTUALE
    output_filename = "grafo_completo.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"✓ Grafo completo salvato su '{output_filename}'")

    # 💾 SALVATAGGIO PARAMETRI
    save_params_to_json(params)

    # 💾 SALVATAGGIO METADATI
    metadata = {
        "branching_factor": branching_factor,
        "depth": depth,
        "branching_range": f"{params['branching_range'][0]}-{params['branching_range'][1]}",
        "depth_range": f"{params['depth_range'][0]}-{params['depth_range'][1]}",
        "graph_filename": output_filename,
        "grafo_generato": True
    }

    with open("grafo_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print("✓ Metadati salvati su 'grafo_metadata.json'")

    # 🧪 VALIDAZIONE BASICA
    print("\n🧪 VALIDAZIONE DEL GRAFO:")
    print(f"   - Contiene 'Nodo 0': {'✓' if 'Nodo 0' in output else '✗'}")
    print(f"   - Contiene 'GOAL RAGGIUNTO': {'✓' if 'GOAL RAGGIUNTO' in output else '✗'}")
    print(f"   - Contiene 'Scegli': {'✓' if 'Scegli' in output else '✗'}")
    print(f"   - Contiene 'Stato:': {'✓' if 'Stato:' in output else '✗'}")

    num_nodes = output.count("Nodo ")
    print(f"   - Numero di nodi trovati: {num_nodes}")

    print("\n" + "=" * 80)
    print("🎉 COMPLETATO! Puoi ora usare il grafo nel tuo web game.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()