import os
import re
import ollama
import subprocess
from pathlib import Path

# ========== CONFIGURAZIONE ==========
MODEL_NAME = "llama3:latest"
OUTPUT_DIR = Path("Generated_PDDL")
OUTPUT_DIR.mkdir(exist_ok=True)


# ========== 1️⃣ PARSING DEL LORE DOCUMENT ==========
def parse_lore_document(lore_text):
    """
    Estrae parametri logici e indizi di entità dal Lore Document.
    """
    branching = re.findall(r"Branching Factor.*?(\d+).*?(\d+)", lore_text, re.S)
    branching_min, branching_max = map(int, branching[0]) if branching else (2, 4)

    depth = re.findall(r"Depth Constraints.*?(\d+).*?(\d+)", lore_text, re.S)
    depth_min, depth_max = map(int, depth[0]) if depth else (5, 10)

    entities = {}
    entities["characters"] = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", lore_text)
    entities["locations"] = re.findall(r"(?:in|at|on|within)\s+([A-Z][a-zA-Z\s]+)", lore_text)
    entities["objects"] = re.findall(r"\b(?:code|device|artifact|weapon|system|file|key)\b", lore_text, re.I)
    entities["goals"] = re.findall(r"Goal:?\s*(.+)", lore_text)

    for k in entities:
        entities[k] = list(set(entities[k]))

    return {
        "branching_min": branching_min,
        "branching_max": branching_max,
        "depth_min": depth_min,
        "depth_max": depth_max,
        "entities": entities
    }


# ========== 2️⃣ GENERAZIONE CON TEMPLATE ==========
def generate_pddl_from_lore(lore_text, theme="Cyberpunk Noir"):
    """
    Genera file PDDL basandosi su template predefiniti e riempie solo le entità e goal dal Lore.
    Struttura fissa come domain/problem forniti.
    """
    parsed = parse_lore_document(lore_text)

    # ==== TEMPLATE FISSI ====
    domain_template = """
(define (domain lost-code)
  (:requirements :strips :typing)

  (:types location ai agent code obstacle)

  (:predicates
    (at ?a - ai ?l - location)
    (has-code ?a - ai)
    (code-found ?c - code)
    (obstacle-present ?o - obstacle ?l - location)
    (rival-ai-present ?r - ai ?l - location)
    (corporate-agent-present ?ag - agent ?l - location)
    (safe ?l - location)
  )

  ;; Azioni
  (:action move
    :parameters (?a - ai ?from - location ?to - location)
    :precondition (and (at ?a ?from) (safe ?to))
    :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action hack
    :parameters (?a - ai ?o - obstacle ?l - location)
    :precondition (and (at ?a ?l) (obstacle-present ?o ?l))
    :effect (not (obstacle-present ?o ?l))
  )

  (:action confront-rival
    :parameters (?a - ai ?r - ai ?l - location)
    :precondition (and (at ?a ?l) (rival-ai-present ?r ?l))
    :effect (not (rival-ai-present ?r ?l))
  )

  (:action evade-corporate
    :parameters (?a - ai ?ag - agent ?l - location)
    :precondition (and (at ?a ?l) (corporate-agent-present ?ag ?l))
    :effect (not (corporate-agent-present ?ag ?l))
  )

  (:action recover-code
    :parameters (?a - ai ?c - code ?l - location)
    :precondition (and (at ?a ?l) (safe ?l))
    :effect (and (has-code ?a) (code-found ?c))
  )
)
"""

    problem_template = """
(define (problem lost-code-problem)
  (:domain lost-code)

  (:objects
    {characters}
    {locations}
    {ai}
    {agents}
    {obstacles}
    {codes}
  )

  (:init
    {init_statements}
  )

  (:goal
    {goal_statement}
  )
)
"""

    # ==== ESTRAZIONE ENTITÀ DAL LORE ====
    characters = ' '.join([c.lower() for c in parsed['entities']['characters']])
    locations = ' '.join([l.lower() for l in parsed['entities']['locations']])
    ai_entities = 'ai1 ai2'  # puoi aggiungere dinamicamente se vuoi
    agents = 'agent1 agent2'
    obstacles = 'firewall security-system ice-wall'
    codes = 'lost-code'

    # ==== INIZIALIZZAZIONE BASE ====
    init_statements = "\n    ".join([
        "(at ai1 alleyway)",
        "(rival-ai-present rival1 street)",
        "(rival-ai-present rival2 rooftop)",
        "(corporate-agent-present agent1 street)",
        "(corporate-agent-present agent2 lab)",
        "(obstacle-present firewall street)",
        "(obstacle-present security-system lab)",
        "(obstacle-present ice-wall underground)",
        "(safe alleyway)",
        "(safe street)",
        "(safe rooftop)",
        "(safe lab)",
        "(safe underground)"
    ])

    goal_statement = "(and (has-code ai1) (code-found lost-code))"

    # ==== REMPLAZZO TEMPLATE ====
    problem_text = problem_template.format(
        characters=characters,
        locations=locations,
        ai=ai_entities,
        agents=agents,
        obstacles=obstacles,
        codes=codes,
        init_statements=init_statements,
        goal_statement=goal_statement
    )

    # ==== SALVATAGGIO FILE ====
    domain_path = OUTPUT_DIR / "domain.pddl"
    problem_path = OUTPUT_DIR / "problem.pddl"

    domain_path.write_text(domain_template)
    problem_path.write_text(problem_text)

    print(f"✅ File salvati in: {OUTPUT_DIR.resolve()}")
    print(f" - domain.pddl ({len(domain_template)} chars)")
    print(f" - problem.pddl ({len(problem_text)} chars)")

    return domain_path, problem_path


# ========== 3️⃣ VALIDAZIONE CON FAST DOWNWARD ==========
def validate_with_fastdownward(domain_path, problem_path):
    fast_downward_path = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"

    if not os.path.exists(fast_downward_path):
        print("❌ Fast Downward non trovato al percorso specificato.")
        return

    cmd = [
        "python",
        fast_downward_path,
        str(domain_path),
        str(problem_path),
        "--search",
        "astar(lmcut())"
    ]

    try:
        print("▶️ Esecuzione Fast Downward...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Validazione completata.")
        print("Output planner:\n", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore durante l’esecuzione di Fast Downward:\n{e.stdout}\n{e.stderr}")


# ========== MAIN ==========
if __name__ == "__main__":
    with open(
            "/QuestMaster/Lore/Generated_Lore/Lore_In_a_gritty_hightech_city_youre_a_rogue_.txt",
            "r", encoding="utf-8") as f:
        lore_text = f.read()

    domain_path, problem_path = generate_pddl_from_lore(lore_text, theme="Cyberpunk Noir")

    if domain_path and problem_path:
        validate_with_fastdownward(domain_path, problem_path)
