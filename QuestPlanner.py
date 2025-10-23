import requests
import json
import logging
import subprocess
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class PDDLGenerator:
    def __init__(self, ollama_url="http://localhost:11434/api/generate", model="llama3"):
        self.ollama_url = ollama_url
        self.model = model
        self.pddl_dir = Path("pddl_files")
        self.pddl_dir.mkdir(exist_ok=True)

    def call_ollama(self, prompt, system_prompt=""):
        """Chiama Ollama per generare contenuto"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 2000
                }
            }

            response = requests.post(self.ollama_url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get('response', '').strip()
        except Exception as e:
            logger.error(f"Errore chiamata Ollama: {e}")
            raise

    def generate_domain(self, config):
        """Genera il file PDDL Domain basato sulla configurazione"""
        system_prompt = """You are an expert in PDDL (Planning Domain Definition Language) and interactive storytelling.
        You create coherent and playable domain definitions for text adventures."""

        prompt = f"""Generate a complete PDDL domain file for an interactive story with these characteristics:
        - Genre: {config['genre']}
        - Theme: {config['theme']}
        - Tone: {config['tone']}
        - Length: {config['length']}

        The domain must include:
        1. Types: location, item, character, puzzle, clue
        2. Predicates for: player position, item possession, door states, puzzle solving
        3. Actions: move between locations, pick up items, use items, solve puzzles, interact with characters
        4. Each action must have clear preconditions and effects

        Create 3-5 puzzles that fit the theme. Each puzzle should require specific items or clues to solve.

        Return ONLY valid PDDL syntax, starting with (define (domain quest-domain) and ending with the closing parenthesis.
        Make it narrative-rich but logically sound."""

        domain_text = self.call_ollama(prompt, system_prompt)

        # Estrai solo il codice PDDL valido
        start_idx = domain_text.find('(define (domain')
        if start_idx != -1:
            domain_text = domain_text[start_idx:]
            # Trova l'ultima parentesi chiusa
            paren_count = 0
            for i, char in enumerate(domain_text):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        domain_text = domain_text[:i + 1]
                        break

        # Salva il dominio
        domain_path = self.pddl_dir / "domain.pddl"
        with open(domain_path, 'w', encoding='utf-8') as f:
            f.write(domain_text)

        logger.info(f"Domain PDDL generato: {domain_path}")
        return domain_text, str(domain_path)

    def generate_problem(self, config, domain_text):
        """Genera il file PDDL Problem basato sulla configurazione e sul dominio"""
        system_prompt = """You are an expert in PDDL problem definitions. 
        You create initial states and goals that are challenging but solvable."""

        # Calcola la complessità in base alla lunghezza
        complexity_map = {
            "Short (2-5 min)": "3-5 locations, 2-3 items, 1-2 puzzles",
            "Medium (5-10 min)": "5-8 locations, 4-6 items, 2-3 puzzles",
            "Long (10+ min)": "8-12 locations, 6-10 items, 3-5 puzzles"
        }
        complexity = complexity_map.get(config['length'], "5-8 locations, 4-6 items, 2-3 puzzles")

        prompt = f"""Based on this PDDL domain:
        {domain_text[:1500]}...

        Generate a complete PDDL problem file for:
        - Genre: {config['genre']}
        - Theme: {config['theme']}
        - Complexity: {complexity}

        The problem must include:
        1. Objects: Define all locations, items, characters, puzzles, and clues needed
        2. Init state: Player starts at a specific location, items are distributed logically, doors may be locked, puzzles are unsolved
        3. Goal state: Player must reach a final location AND have solved key puzzles (related to "{config['theme']}")

        Make the initial state challenging but ensure the goal is achievable through logical progression.

        Return ONLY valid PDDL syntax, starting with (define (problem quest-problem) and ending with the closing parenthesis.
        Use object names that fit the narrative theme."""

        problem_text = self.call_ollama(prompt, system_prompt)

        # Estrai solo il codice PDDL valido
        start_idx = problem_text.find('(define (problem')
        if start_idx != -1:
            problem_text = problem_text[start_idx:]
            paren_count = 0
            for i, char in enumerate(problem_text):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        problem_text = problem_text[:i + 1]
                        break

        # Salva il problema
        problem_path = self.pddl_dir / "problem.pddl"
        with open(problem_path, 'w', encoding='utf-8') as f:
            f.write(problem_text)

        logger.info(f"Problem PDDL generato: {problem_path}")
        return problem_text, str(problem_path)

    def validate_plan(self, domain_path, problem_path):
        """Valida il piano usando Fast Downward o un planner PDDL"""
        logger.info("Validazione del piano PDDL...")

        try:
            # Prova a usare Fast Downward se disponibile
            # Nota: Fast Downward deve essere installato e nel PATH
            result = subprocess.run(
                ['fast-downward', '--search', 'astar(lmcut())',
                 domain_path, problem_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 or "Solution found" in result.stdout:
                logger.info("✓ Piano validato: soluzione trovata!")
                return True, "Piano risolvibile - soluzione esistente"
            else:
                logger.warning("✗ Piano non risolvibile")
                return False, "Piano non risolvibile - nessuna soluzione trovata"

        except FileNotFoundError:
            logger.warning("Fast Downward non trovato. Validazione simulata.")
            # Fallback: validazione sintattica di base
            return self._basic_validation(domain_path, problem_path)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout validazione planner")
            return False, "Timeout durante la validazione"
        except Exception as e:
            logger.error(f"Errore validazione: {e}")
            return False, f"Errore: {str(e)}"

    def _basic_validation(self, domain_path, problem_path):
        """Validazione sintattica di base se Fast Downward non è disponibile"""
        try:
            with open(domain_path, 'r') as f:
                domain = f.read()
            with open(problem_path, 'r') as f:
                problem = f.read()

            # Controlla sintassi di base
            checks = [
                ('(define (domain' in domain, "Domain definition mancante"),
                ('(:requirements' in domain, "Requirements mancanti"),
                ('(:types' in domain, "Types mancanti"),
                ('(:predicates' in domain, "Predicates mancanti"),
                ('(:action' in domain, "Azioni mancanti"),
                ('(define (problem' in problem, "Problem definition mancante"),
                ('(:domain' in problem, "Riferimento al domain mancante"),
                ('(:objects' in problem, "Objects mancanti"),
                ('(:init' in problem, "Init state mancante"),
                ('(:goal' in problem, "Goal mancante")
            ]

            for check, error_msg in checks:
                if not check:
                    return False, f"Validazione fallita: {error_msg}"

            logger.info("✓ Validazione sintattica completata")
            return True, "Validazione sintattica superata (planner non disponibile)"

        except Exception as e:
            return False, f"Errore validazione: {str(e)}"

    def extract_narrative_elements(self, domain_text, problem_text):
        """Estrae elementi narrativi dai file PDDL per la generazione della storia"""
        system_prompt = """You are a narrative analyzer. Extract key story elements from PDDL definitions."""

        prompt = f"""Analyze these PDDL files and extract narrative elements:

DOMAIN (excerpt):
{domain_text[:1000]}

PROBLEM (excerpt):
{problem_text[:1000]}

Extract and return a JSON with:
{{
    "locations": ["list of location names"],
    "characters": ["list of character names"],
    "items": ["list of item names"],
    "puzzles": ["list of puzzle descriptions"],
    "initial_situation": "brief description of starting state",
    "final_goal": "description of what the player must achieve"
}}

Return ONLY the JSON, no other text."""

        response = self.call_ollama(prompt, system_prompt)

        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                elements = json.loads(json_str)
                return elements
        except Exception as e:
            logger.error(f"Errore estrazione elementi narrativi: {e}")
            return {
                "locations": ["unknown"],
                "characters": ["unknown"],
                "items": ["unknown"],
                "puzzles": ["unknown"],
                "initial_situation": "Unknown",
                "final_goal": "Unknown"
            }


class QuestPlanner:
    """Orchestratore principale della fase di pianificazione"""

    def __init__(self):
        self.pddl_generator = PDDLGenerator()

    def plan_quest(self, config):
        """
        Fase di pianificazione completa
        Input: config dict con genre, length, tone, graphics, theme
        Output: dict con PDDL files, validation status, e narrative elements
        """
        logger.info("=== INIZIO FASE DI PIANIFICAZIONE LOGICA ===")
        logger.info(f"Configurazione: {config}")

        try:
            # 1. Genera il Domain PDDL
            logger.info("Step 1: Generazione Domain PDDL...")
            domain_text, domain_path = self.pddl_generator.generate_domain(config)

            # 2. Genera il Problem PDDL
            logger.info("Step 2: Generazione Problem PDDL...")
            problem_text, problem_path = self.pddl_generator.generate_problem(config, domain_text)

            # 3. Valida la risolvibilità
            logger.info("Step 3: Validazione e verifica risolvibilità...")
            is_valid, validation_message = self.pddl_generator.validate_plan(domain_path, problem_path)

            # 4. Estrai elementi narrativi
            logger.info("Step 4: Estrazione elementi narrativi...")
            narrative_elements = self.pddl_generator.extract_narrative_elements(domain_text, problem_text)

            # 5. Compila il risultato
            result = {
                "success": True,
                "planning_complete": True,
                "validation": {
                    "is_valid": is_valid,
                    "message": validation_message
                },
                "pddl_files": {
                    "domain_path": domain_path,
                    "problem_path": problem_path,
                    "domain_text": domain_text,
                    "problem_text": problem_text
                },
                "narrative_elements": narrative_elements,
                "config": config
            }

            logger.info("=== PIANIFICAZIONE COMPLETATA CON SUCCESSO ===")
            return result

        except Exception as e:
            logger.error(f"Errore durante la pianificazione: {e}")
            return {
                "success": False,
                "error": str(e),
                "config": config
            }


# Esempio di utilizzo
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Simula il config ottenuto dal frontend
    test_config = {
        "genre": "Fantasy",
        "length": "Medium (5-10 min)",
        "tone": "Epic and Solemn",
        "graphics": "Illustrated",
        "theme": "Una missione per salvare il regno"
    }

    planner = QuestPlanner()
    result = planner.plan_quest(test_config)

    print("\n" + "=" * 60)
    print("RISULTATO PIANIFICAZIONE:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result['success']:
        print("\n✓ Domain e Problem PDDL generati con successo!")
        print(f"✓ Validazione: {result['validation']['message']}")
        print(f"✓ Elementi narrativi estratti: {len(result['narrative_elements'])} categorie")
    else:
        print(f"\n✗ Errore: {result['error']}")