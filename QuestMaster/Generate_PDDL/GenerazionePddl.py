import os
import sys
import re
import subprocess
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.environ.get("OPENAI_API_KEY")

client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY)
else:
    logger.warning("OPENAI_API_KEY mancante nel file .env. Le funzioni LLM non funzioneranno.")
MODEL = "gpt-4o"


def check_openai_available() -> bool:
    return client is not None


def call_gpt(prompt, system_prompt=""):
    if not client:
        logger.error("Client OpenAI non inizializzato.")
        return ""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Errore chiamata OpenAI: {e}")
        return ""


class DifficultyLevel(Enum):
    EASY = "easy"  # 3-6 azioni
    MEDIUM = "medium"  # 7-12 azioni
    HARD = "hard"  # 13-25 azioni


@dataclass
class ValidatedPDDL:
    domain: str
    problem: str
    expected_plan_length: int
    description: str

#Pddl validi risolvibili
class PDDLLibrary:

    @staticmethod
    def get_keys_doors_easy() -> ValidatedPDDL:
        domain = """(define (domain keys-doors-simple)
                  (:requirements :strips :typing)
                  (:types location key door agent)
                  (:predicates
                    (at ?a - agent ?l - location)
                    (key-at ?k - key ?l - location)
                    (has-key ?a - agent ?k - key)
                    (door-between ?d - door ?l1 ?l2 - location)
                    (locked ?d - door)
                    (unlocks ?k - key ?d - door)
                  )
                
                  (:action move
                   :parameters (?a - agent ?from ?to - location ?d - door)
                   :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))
                   :effect (and (not (at ?a ?from)) (at ?a ?to))
                  )
                
                  (:action pick-key
                   :parameters (?a - agent ?k - key ?l - location)
                   :precondition (and (at ?a ?l) (key-at ?k ?l))
                   :effect (and (not (key-at ?k ?l)) (has-key ?a ?k))
                  )
                
                  (:action unlock
                   :parameters (?a - agent ?k - key ?d - door ?l - location)
                   :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d))
                   :effect (not (locked ?d))
                  )
                )"""

        problem = """(define (problem quest-easy)
                  (:domain keys-doors-simple)
                  (:objects
                    room1 room2 - location
                    hero - agent
                    silver_key - key
                    main_door - door
                  )
                  (:init
                    (at hero room1)
                    (key-at silver_key room1)
                    (door-between main_door room1 room2)
                    (locked main_door)
                    (unlocks silver_key main_door)
                  )
                  (:goal
                    (at hero room2)
                  )
                )"""
        return ValidatedPDDL(domain, problem, 3, "Easy: 2 rooms, 1 key")

    @staticmethod
    def get_keys_doors_medium() -> ValidatedPDDL:
        domain = """(define (domain keys-doors-simple)
                  (:requirements :strips :typing)
                  (:types location key door agent)
                  (:predicates
                    (at ?a - agent ?l - location)
                    (key-at ?k - key ?l - location)
                    (has-key ?a - agent ?k - key)
                    (door-between ?d - door ?l1 ?l2 - location)
                    (locked ?d - door)
                    (unlocks ?k - key ?d - door)
                  )
                
                  (:action move
                   :parameters (?a - agent ?from ?to - location ?d - door)
                   :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))
                   :effect (and (not (at ?a ?from)) (at ?a ?to))
                  )
                
                  (:action pick-key
                   :parameters (?a - agent ?k - key ?l - location)
                   :precondition (and (at ?a ?l) (key-at ?k ?l))
                   :effect (and (not (key-at ?k ?l)) (has-key ?a ?k))
                  )
                
                  (:action unlock
                   :parameters (?a - agent ?k - key ?d - door ?l - location)
                   :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d))
                   :effect (not (locked ?d))
                  )
                )"""

        problem = """(define (problem quest-medium)
                  (:domain keys-doors-simple)
                  (:objects
                    entrance hall treasure_room secret_chamber - location
                    hero - agent
                    bronze_key golden_key - key
                    main_door treasure_door - door
                  )
                  (:init
                    (at hero entrance)
                    (key-at bronze_key entrance)
                    (key-at golden_key hall)
                
                    (door-between main_door entrance hall)
                    (door-between treasure_door hall treasure_room)
                
                    (locked main_door)
                    (locked treasure_door)
                
                    (unlocks bronze_key main_door)
                    (unlocks golden_key treasure_door)
                  )
                  (:goal
                    (at hero treasure_room)
                  )
                )"""
        return ValidatedPDDL(domain, problem, 7, "Medium: 4 rooms, 2 keys")

    @staticmethod
    def get_keys_doors_hard() -> ValidatedPDDL:
        domain = """(define (domain keys-doors-simple)
              (:requirements :strips :typing)
              (:types location key door agent)
              (:predicates
                (at ?a - agent ?l - location)
                (key-at ?k - key ?l - location)
                (has-key ?a - agent ?k - key)
                (door-between ?d - door ?l1 ?l2 - location)
                (locked ?d - door)
                (unlocks ?k - key ?d - door)
              )
            
              (:action move
               :parameters (?a - agent ?from ?to - location ?d - door)
               :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d)))
               :effect (and (not (at ?a ?from)) (at ?a ?to))
              )
            
              (:action pick-key
               :parameters (?a - agent ?k - key ?l - location)
               :precondition (and (at ?a ?l) (key-at ?k ?l))
               :effect (and (not (key-at ?k ?l)) (has-key ?a ?k))
              )
            
              (:action unlock
               :parameters (?a - agent ?k - key ?d - door ?l - location)
               :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d))
               :effect (not (locked ?d))
              )
            )"""

        problem = """(define (problem quest-hard)
                  (:domain keys-doors-simple)
                  (:objects
                    entrance courtyard armory library vault throne_room - location
                    hero - agent
                    copper_key silver_key golden_key master_key - key
                    gate1 gate2 gate3 gate4 - door
                  )
                  (:init
                    (at hero entrance)
                
                    (key-at copper_key entrance)
                    (key-at silver_key courtyard)
                    (key-at golden_key armory)
                    (key-at master_key library)
                
                    (door-between gate1 entrance courtyard)
                    (door-between gate2 courtyard armory)
                    (door-between gate3 armory library)
                    (door-between gate4 library throne_room)
                
                    (locked gate1)
                    (locked gate2)
                    (locked gate3)
                    (locked gate4)
                
                    (unlocks copper_key gate1)
                    (unlocks silver_key gate2)
                    (unlocks golden_key gate3)
                    (unlocks master_key gate4)
                  )
                  (:goal
                    (at hero throne_room)
                  )
                )"""
        return ValidatedPDDL(domain, problem, 16, "Hard: 6 rooms, 4 keys")

    @staticmethod
    def get_logistics_easy() -> ValidatedPDDL:
        domain = """(define (domain logistics-simple)
                  (:requirements :strips :typing)
                  (:types location vehicle package)
                  (:predicates
                    (at-vehicle ?v - vehicle ?l - location)
                    (at-package ?p - package ?l - location)
                    (in-vehicle ?p - package ?v - vehicle)
                    (connected ?from ?to - location)
                  )
                
                  (:action move
                   :parameters (?v - vehicle ?from ?to - location)
                   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to))
                   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to))
                  )
                
                  (:action load
                   :parameters (?p - package ?v - vehicle ?l - location)
                   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l))
                   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v))
                  )
                
                  (:action unload
                   :parameters (?p - package ?v - vehicle ?l - location)
                   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l))
                   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l))
                  )
                )"""

        problem = """(define (problem delivery-easy)
                  (:domain logistics-simple)
                  (:objects
                    warehouse shop home - location
                    truck - vehicle
                    parcel - package
                  )
                  (:init
                    (at-vehicle truck warehouse)
                    (at-package parcel warehouse)
                
                    (connected warehouse shop)
                    (connected shop warehouse)
                    (connected shop home)
                    (connected home shop)
                  )
                  (:goal
                    (at-package parcel home)
                  )
                )"""
        return ValidatedPDDL(domain, problem, 5, "Easy logistics: deliver 1 package")

    @staticmethod
    def get_logistics_medium() -> ValidatedPDDL:
        domain = """(define (domain logistics-simple)
                  (:requirements :strips :typing)
                  (:types location vehicle package)
                  (:predicates
                    (at-vehicle ?v - vehicle ?l - location)
                    (at-package ?p - package ?l - location)
                    (in-vehicle ?p - package ?v - vehicle)
                    (connected ?from ?to - location)
                  )
                
                  (:action move
                   :parameters (?v - vehicle ?from ?to - location)
                   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to))
                   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to))
                  )
                
                  (:action load
                   :parameters (?p - package ?v - vehicle ?l - location)
                   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l))
                   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v))
                  )
                
                  (:action unload
                   :parameters (?p - package ?v - vehicle ?l - location)
                   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l))
                   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l))
                  )
                )"""

        problem = """(define (problem delivery-medium)
                  (:domain logistics-simple)
                  (:objects
                    warehouse depot shop home - location
                    truck - vehicle
                    package1 package2 - package
                  )
                  (:init
                    (at-vehicle truck warehouse)
                    (at-package package1 warehouse)
                    (at-package package2 depot)
                
                    (connected warehouse depot)
                    (connected depot warehouse)
                    (connected depot shop)
                    (connected shop depot)
                    (connected shop home)
                    (connected home shop)
                  )
                  (:goal
                    (and
                      (at-package package1 home)
                      (at-package package2 shop)
                    )
                  )
                )"""
        return ValidatedPDDL(domain, problem, 11, "Medium logistics: deliver 2 packages")


class SmartPDDLSelector:
    def __init__(self, lore_content: str):
        self.lore = lore_content
        self.library = PDDLLibrary()

    def select_best_pddl(self) -> ValidatedPDDL:
        analysis = self._analyze_lore()
        logger.info(f"Analisi Lore:")
        logger.info(f"   - Genere rilevato: {analysis['genre']}")
        logger.info(f"   - Depth target: {analysis['depth_min']}-{analysis['depth_max']}")
        logger.info(f"   - Difficoltà: {analysis['difficulty']}")

        if analysis['genre'] in ['fantasy', 'adventure', 'mystery']:
            template_type = 'keys_doors'
        else:
            template_type = 'logistics'

        if analysis['difficulty'] == DifficultyLevel.EASY:
            if template_type == 'keys_doors':
                pddl = self.library.get_keys_doors_easy()
            else:
                pddl = self.library.get_logistics_easy()
        elif analysis['difficulty'] == DifficultyLevel.MEDIUM:
            if template_type == 'keys_doors':
                pddl = self.library.get_keys_doors_medium()
            else:
                pddl = self.library.get_logistics_medium()
        else:  # HARD
            if template_type == 'keys_doors':
                pddl = self.library.get_keys_doors_hard()
            else:
                pddl = self.library.get_logistics_medium()  # Fallback

        logger.info(f"Selezionato: {pddl.description}")
        logger.info(f"Piano atteso: ~{pddl.expected_plan_length} azioni")

        return pddl

    def _analyze_lore(self) -> Dict:
        lore_lower = self.lore.lower()
        match = re.search(r'genere[:\s]*([^\n|]+)', self.lore, re.IGNORECASE)
        if match:
            genre = match.group(1).strip()
            logger.info(f"Genere rilevato dal testo: {genre}")
        else:
            prompt = f"""
            Leggi la seguente storia e identificane il genere.
            Scegline esattamente una da questa lista:
            ["Fantasy", "Romantico", "Drammatico", "Horror", "Commedia", "Fantascienza", "Mistero", "Storico", "Avventura"].
            Rispondi solo con la parola del genere.

            LORE:
            {self.lore}
            """
            system_prompt = "Sei un modello di classificazione del testo che identifica il genere letterario di una determinata storia."
            result = call_gpt(prompt, system_prompt)

            if result:
                genre = result.strip().lower()
                logger.info(f"Genere rilevato da LLM: {genre}")
            else:
                genre = "generic"
                logger.warning("Nessuna risposta valida da LLM, uso 'generic'.")

        depth_min, depth_max = 5, 10
        depth_patterns = [
            r'depth[:\s]+(\d+)\s*-\s*(\d+)',
            r'(\d+)\s*-\s*(\d+)\s+azioni',
            r'min[:\s]+(\d+).*max[:\s]+(\d+)',
        ]

        for pattern in depth_patterns:
            match = re.search(pattern, lore_lower)
            if match:
                depth_min = int(match.group(1))
                depth_max = int(match.group(2))
                break

        depth_section = re.search(r'depth constraints.*?(\d+)\s*-\s*(\d+)', lore_lower, re.DOTALL)
        if depth_section:
            depth_min = int(depth_section.group(1))
            depth_max = int(depth_section.group(2))
        if depth_max <= 3:
            difficulty = DifficultyLevel.EASY
        elif depth_max <= 5:
            difficulty = DifficultyLevel.MEDIUM
        else:
            difficulty = DifficultyLevel.HARD
        return {
            'genre': genre,
            'depth_min': depth_min,
            'depth_max': depth_max,
            'difficulty': difficulty
        }

class PDDLPersonalizer:
    def __init__(self, lore_content: str):
        self.lore = lore_content

    def personalize(self, pddl: ValidatedPDDL) -> ValidatedPDDL:
        names = self._extract_names()
        if not names['locations'] or not names['characters']:
            logger.info("Nomi insufficienti nel lore, uso template originale")
            return pddl

        logger.info(f"Personalizzo PDDL con nomi dal lore...")
        domain_personalized = pddl.domain
        problem_personalized = pddl.problem
        if 'keys-doors' in pddl.problem:
            location_mapping = self._create_location_mapping_keys_doors(names['locations'])
            for old, new in location_mapping.items():
                problem_personalized = problem_personalized.replace(old, new)
        if names['characters']:
            hero_name = self._sanitize_name(names['characters'][0])
            problem_personalized = problem_personalized.replace('hero', hero_name)
        logger.info(
            f"PDDL personalizzato con {len(names['locations'])} location e {len(names['characters'])} personaggi")
        return ValidatedPDDL(
            domain_personalized,
            problem_personalized,
            pddl.expected_plan_length,
            pddl.description + " (personalizzato)"
        )

    def _extract_names(self) -> Dict[str, List[str]]:
        all_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', self.lore)
        common_words = {'The', 'A', 'An', 'I', 'You', 'He', 'She', 'They', 'We'}
        all_names = [n for n in all_names if n not in common_words]
        locations = []
        characters = []
        for name in all_names[:10]:  # Max 10
            if any(kw in name.lower() for kw in ['room', 'hall', 'tower', 'cave', 'forest', 'lab', 'district']):
                locations.append(name)
            else:
                characters.append(name)
        return {
            'locations': locations[:6],  # Max 6 location
            'characters': characters[:3]  # Max 3 personaggi
        }

    def _create_location_mapping_keys_doors(self, lore_locations: List[str]) -> Dict[str, str]:
        generic = ['entrance', 'courtyard', 'armory', 'library', 'vault', 'throne_room',
                   'room1', 'room2', 'hall', 'treasure_room', 'secret_chamber']
        mapping = {}
        for i, gen in enumerate(generic):
            if i < len(lore_locations):
                new_name = self._sanitize_name(lore_locations[i])
                mapping[gen] = new_name
        return mapping

    def _sanitize_name(self, name: str) -> str:
        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name.strip('_')


class FastDownwardValidator:
    def __init__(self, fd_path: str):
        self.fd_path = Path(fd_path)
        if not self.fd_path.exists():
            raise FileNotFoundError(f"Fast Downward non trovato: {fd_path}")
    def validate(self, domain_path: Path, problem_path: Path, save_plan_to: Optional[Path] = None) -> Tuple[
        bool, str, str]:
        python_exe = sys.executable
        cmd = [
            python_exe,
            str(self.fd_path),
            str(domain_path.resolve()),
            str(problem_path.resolve()),
            "--search", "astar(lmcut())"
        ]
        env = os.environ.copy()
        keys_to_remove = [k for k in env.keys() if 'PYCHARM' in k.upper() or 'JETBRAINS' in k.upper()]
        for key in keys_to_remove:
            del env[key]
        if 'PYTHONSTARTUP' in env:
            del env['PYTHONSTARTUP']
        try:
            logger.info("Validazione Fast Downward...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.fd_path.parent,
                env=env
            )
            output = result.stdout + "\n" + result.stderr
            if "Solution found!" in output or "Plan found!" in output:
                possible_locations = [
                    self.fd_path.parent / "sas_plan",
                    Path.cwd() / "sas_plan",
                    domain_path.parent / "sas_plan"
                ]
                plan_content = None
                for plan_path in possible_locations:
                    if plan_path.exists():
                        with open(plan_path, 'r') as f:
                            plan_content = f.read()
                        break
                if plan_content:
                    if save_plan_to:
                        output_plan_path = save_plan_to / "sas_plan"
                        with open(output_plan_path, 'w') as f:
                            f.write(plan_content)
                        readable_plan_path = save_plan_to / "plan_readable.txt"
                        readable_plan = self._make_plan_readable(plan_content)
                        with open(readable_plan_path, 'w') as f:
                            f.write(readable_plan)
                        logger.info(f"✓ Piano salvato in: {readable_plan_path}")
                    return True, plan_content, output
                else:
                    return True, "Soluzione trovata", output
            logger.warning("Nessuna soluzione trovata — avvio Reflection Agent per rigenerare il piano...")

            try:
                reflection_result = self.run_reflection_agent(domain_path, problem_path)
                if reflection_result:
                    logger.info("Riprovo la validazione dopo Reflection Agent...")
                    return self.validate(domain_path, problem_path, save_plan_to)
                else:
                    logger.error("Reflection Agent non ha generato un nuovo piano valido.")
                    return False, "Reflection fallita: nessuna soluzione trovata", output
            except Exception as e:
                logger.exception("Errore durante il reflection agent")
                return False, f"Errore reflection: {e}", output
        except subprocess.TimeoutExpired:
            return False, "Timeout (60s)", ""
        except Exception as e:
            logger.exception("Errore validazione")
            return False, f"Errore: {e}", ""

    def run_reflection_agent(self, domain_path: Path, problem_path: Path) -> bool:
        try:
            logger.info("Avvio Reflection Agent per analizzare i file PDDL...")
            with open(domain_path, "r", encoding="utf-8") as f:
                domain_content = f.read()
            with open(problem_path, "r", encoding="utf-8") as f:
                problem_content = f.read()
            system_prompt = (
                "Sei un esperto di PDDL. Il tuo compito è analizzare un domain e una definizione di problem "
                "che non sono riusciti a produrre un piano valido in Fast Downward. Devi identificare problemi strutturali"
                "o logici (precondizioni mancanti, obiettivi incoerenti, azioni impossibili)"
                "e produrre una versione corretta che sia comunque fedele allo scenario originale."
            )

            user_prompt = f"""
            Il seguente domain PDDL e il problem non hanno prodotto alcun piano valido.
            Domain:
            {domain_content}
            Problem:
            {problem_content}
            1. Identifica il problema più probabile che impedisce la generazione del piano.
            2. Modifica il PDDL il meno possibile per risolvere il problema.
            3. Mantieni la sintassi rigorosamente valida e coerente con i requisiti di Fast Downward.
            4. Restituisci solo il domain e il problem corretti, formattati esattamente come:
            ---DOMAIN---
            <domain corretto>
            ---PROBLEM---
            <problem risolto>
            """

            response = call_gpt(user_prompt, system_prompt)
            domain_fixed, problem_fixed = None, None
            match_domain = re.search(r"---DOMAIN---(.*?)---PROBLEM---", response, re.DOTALL)
            match_problem = re.search(r"---PROBLEM---(.*)", response, re.DOTALL)
            if match_domain and match_problem:
                domain_fixed = match_domain.group(1).strip()
                problem_fixed = match_problem.group(1).strip()
            if not domain_fixed or not problem_fixed:
                logger.error("Il Reflection Agent non ha restituito un PDDL valido.")
                return False
            with open(domain_path, "w", encoding="utf-8") as f:
                f.write(domain_fixed)
            with open(problem_path, "w", encoding="utf-8") as f:
                f.write(problem_fixed)
            logger.info("Reflection Agent completato: file PDDL aggiornati.")
            return True
        except Exception as e:
            logger.exception("Errore nel Reflection Agent")
            return False

    def _make_plan_readable(self, plan_content: str) -> str:
        lines = plan_content.strip().split('\n')
        readable = ["=" * 60, "PIANO DI AZIONI", "=" * 60, ""]
        step = 1
        for line in lines:
            line = line.strip()
            if line and not line.startswith(';'):
                action = line.strip('()')
                readable.append(f"Step {step}: {action}")
                step += 1
        readable.append("")
        readable.append("=" * 60)
        readable.append(f"Piano completato in {step - 1} passi")
        readable.append("=" * 60)
        return '\n'.join(readable)

def generate_valid_pddl_guaranteed(lore_path: Path, output_dir: Path, fd_path: str, personalize: bool = True) -> Tuple[bool, str]:
    logger.info("=" * 70)
    logger.info("GENERAZIONE PDDL - STRATEGIA GARANTITA")
    logger.info("Usa template pre-validati + personalizzazione sicura (GPT-4o Enhanced)")
    logger.info("=" * 70)

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(lore_path, 'r', encoding='utf-8') as f:
        lore_content = f.read()

    logger.info("\nSTEP 1: Selezione template pre-validato...")
    selector = SmartPDDLSelector(lore_content)
    pddl = selector.select_best_pddl()
    if personalize:
        logger.info("\n STEP 2: Personalizzazione nomi...")
        personalizer = PDDLPersonalizer(lore_content)
        pddl = personalizer.personalize(pddl)
    else:
        logger.info("\nSTEP 2: Skip personalizzazione")
    logger.info("\nSTEP 3: Salvataggio file...")
    domain_path = output_dir / "domain.pddl"
    problem_path = output_dir / "problem.pddl"
    with open(domain_path, 'w') as f:
        f.write(pddl.domain)
    with open(problem_path, 'w') as f:
        f.write(pddl.problem)
    logger.info(f"✓ File salvati in: {output_dir}")
    logger.info("\nSTEP 4: Validazione finale...")
    validator = FastDownwardValidator(fd_path)
    success, message, output = validator.validate(domain_path, problem_path, save_plan_to=output_dir)
    if success:
        logger.info("\nSUCCESSO GARANTITO!")
        logger.info(f"File generati:")
        logger.info(f"   - Domain: {domain_path}")
        logger.info(f"   - Problem: {problem_path}")
        logger.info(f"   - Piano: {output_dir / 'plan_readable.txt'}")
        aggiunta_commenti_LLM(domain_path, problem_path)
        return True, "PDDL valido garantito"
    else:
        logger.error(f"\nValidazione fallita (imprevisto): {message}")
        return False, f"Errore validazione: {message}"


def aggiunta_commenti_LLM(domain_path: Path, problem_path: Path):
    domain_text = domain_path.read_text(encoding="utf-8")
    problem_text = problem_path.read_text(encoding="utf-8")

    system_prompt = """Sei un esperto in pianificazione dell'IA e PDDL (Planning Domain Definition Language).
    Il tuo compito è annotare i file PDDL con commenti in linea chiari e concisi.
    NON modificare o riordinare alcuna riga e non rimuovere le parentesi.
    Ogni commento deve essere sulla stessa riga, preceduto da un punto e virgola (;).
    Mantieni i commenti brevi, chiari e descrittivi in linguaggio naturale.
    """

    prompt_template = """Di seguito è riportato un file PDDL.
    Aggiungi un breve commento in linea a ogni riga, spiegando la funzione di quella riga in un linguaggio semplice.
    NON modificare la struttura, la spaziatura o la sintassi.
    Aggiungi commenti solo alla fine delle righe, utilizzando ';' come marcatore di commento.
    Restituisci SOLO il PDDL annotato, nient'altro.
    FILE PDDL:
    {content}
    """
    print("Aggiunta commenti al domain...")
    domain_commented = call_gpt(
        prompt_template.format(content=domain_text),
        system_prompt
    )

    print("Aggiunta commenti al problem...")
    problem_commented = call_gpt(
        prompt_template.format(content=problem_text),
        system_prompt
    )
    if not domain_commented or not problem_commented:
        print("Impossibile generare i file commentati. Controlla la connessione OpenAI.")
        return None

    domain_out = domain_path.parent / f"{domain_path.stem}_commented.pddl"
    problem_out = problem_path.parent / f"{problem_path.stem}_commented.pddl"
    domain_out.write_text(domain_commented, encoding="utf-8")
    problem_out.write_text(problem_commented, encoding="utf-8")

    print(f"File commentati salvati in:\n   - {domain_out}\n   - {problem_out}")
    return domain_out, problem_out


def check_ollama_available() -> bool:
    return check_openai_available()


if __name__ == '__main__':
    SCRIPT_DIR = Path(__file__).resolve().parent
    LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"
    OUTPUT_FOLDER = SCRIPT_DIR / "pddl_output_guaranteed"
    FAST_DOWNWARD = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"
    if not LORE_FILE.exists():
        print(f" Lore non trovato: {LORE_FILE}")
        exit(1)
    if not Path(FAST_DOWNWARD).exists():
        print(f" Fast Downward non trovato: {FAST_DOWNWARD}")
        exit(1)
    print("\n Generazione PDDL GARANTITA (GPT Edition)...\n")
    success, message = generate_valid_pddl_guaranteed(
        lore_path=LORE_FILE,
        output_dir=OUTPUT_FOLDER,
        fd_path=FAST_DOWNWARD,
        personalize=True
    )
    print(message)