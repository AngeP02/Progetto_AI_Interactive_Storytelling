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

def build_prompt(domain, problem, sas_plan, lore):
    return f"""
Genera un GRAFO NARRATIVO COERENTE CON PDDL dove:

1. STATO NARRATIVO PERSISTENTE
   - Ogni nodo specifica quale "stato del caso" sei
   - Es: "Stato: Hai identificato Specter come sospetto"
   - Le scelte future rispecchiano questo stato

2. CONSEGUENZE LOGICHE
   - Scelta 1 (Visita Elara) → Scopri X
   - Scelta 2 (Scena crimine) → Scopri Y
   - Nel prossimo nodo, puoi usare X o Y per azioni diverse

3. CONVERGENZA OBBLIGATORIA
   - Dopo profondità 2, i percorsi devono convergere
   - Tutti gli elementi raccolti si incontrano in nodi comuni
   - Es: "Riunione finale dove accusi il colpevole"

4. GOAL ESPLICITO
   - L'ultimo nodo deve essere "GOAL RAGGIUNTO: Caso Risolto"
   - Deve mostrare quale informazione ha risolto tutto
   - Es: "Hai provato che Victor pagò Specter per uccidere Aurora"

5. PROFONDITÀ E BRANCHING
   - depth={lore.depth}, branching_factor={lore.branching_factor}
   - TUTTI i percorsi raggiungono il goal (non tutti gli endpoint sono uguali)

ESEMPIO DI STRUTTURA CORRETTA:

## Nodo 0: Inizio
Sei nella tua città, indaghi sulla morte di Aurora.
Stato: Nessuna pista ancora

**Scegli:**
1. Visita Dr. Elara Vex
2. Vai alla scena del crimine
...

---

### Nodo 1.1: Da Elara
[Conseguenze: Elara rivela che Specter è il sabotatore]
Stato: Specter identificato come sospetto principale

**Scegli:**
1. Traccia le comunicazioni di Specter
2. Infiltrati nell'AI Underground
...

---

### Nodo 1.2: Scena del Crimine
[Conseguenze: Scopri Black Rain, impronta digitale di un guanto cibernetico]
Stato: Hai due tracce: Black Rain e guanto cibernetico

**Scegli:**
1. Analizza il guanto cibernetico
2. Ricerca Black Rain nei database
...

---

### Nodo 2.1: Convergenza (da 1.1 + altre scelte)
[Combina tutte le prove raccolte]
Stato: Specter collegato a Victor LaGraine tramite pagamenti criptati

**Scegli:**
1. Arresta Victor LaGraine
2. Piedi in una trappola a Specter
...

---

## GOAL RAGGIUNTO: Caso Risolto
Victor LaGraine è l'assassino. Specter era il suo esecutore.
Prova definitiva: [combinazione di tutte le scoperte]"""

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


    print("🔧 Costruzione prompt...")
    prompt = build_prompt(domain, problem, sas_plan, lore)

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
