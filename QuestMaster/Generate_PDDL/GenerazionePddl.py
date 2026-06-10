import os
import sys
import re
import subprocess
import logging
import json
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from openai import OpenAI
import re

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
        logger.info("STEP 1a: Tentativo generazione PDDL da Lore con LLM...")
        generated = self._generate_pddl_from_lore()
        if generated:
            logger.info("Generazione LLM riuscita.")
            return generated
        logger.warning("Generazione LLM fallita, fallback su template...")
        template_type, difficulty = self._analyze_lore_with_llm()
        logger.info(f"Fallback → tipo: {template_type}, difficoltà: {difficulty}")
        if template_type == 'keys_doors':
            if difficulty == DifficultyLevel.EASY:
                return self.library.get_keys_doors_easy()
            elif difficulty == DifficultyLevel.MEDIUM:
                return self.library.get_keys_doors_medium()
            else:
                return self.library.get_keys_doors_hard()
        else:
            if difficulty == DifficultyLevel.EASY:
                return self.library.get_logistics_easy()
            else:
                return self.library.get_logistics_medium()

    def _generate_pddl_from_lore(self) -> Optional[ValidatedPDDL]:
        depth_match = re.search(r"[Dd]epth.*?(\d+)\s*[-–]\s*(\d+)", self.lore)
        branch_match = re.search(r"[Bb]ranching.*?(\d+)\s*[-–]\s*(\d+)", self.lore)
        max_depth = int(depth_match.group(2)) if depth_match else 10
        max_branch = int(branch_match.group(2)) if branch_match else 3

        prompt = f"""
            Sei un esperto di PDDL (Planning Domain Definition Language) per videogiochi narrativi.
            Devi generare un dominio e un problema PDDL basandoti ESCLUSIVAMENTE sulla storia seguente.
            
            STORIA (LORE):
            {self.lore[:3000]}
            
            VINCOLI DI PIANIFICAZIONE:
            - Il piano soluzione deve avere tra 3 e {max_depth} azioni.
            - Ogni stato deve avere tra 2 e {max_branch} azioni applicabili (branching factor).
            
            ISTRUZIONI:
            1. Crea tipi, predicati e azioni coerenti con il mondo della storia (non usare nomi generici come "room1" o "hero").
            2. Il dominio deve avere almeno 3 azioni distinte.
            3. Il problema deve avere uno stato iniziale e un goal chiaramente raggiungibili.
            4. Il PDDL deve essere sintatticamente corretto e risolvibile.
            5. Usa solo :requirements :strips :typing.
            
            Restituisci SOLO nel formato seguente, senza altro testo:
            ---DOMAIN---
            (define (domain ...)
              ...
            )
            ---PROBLEM---
            (define (problem ...)
              ...
            )
        """
        system_prompt = "Sei un esperto PDDL. Rispondi SOLO con il codice PDDL richiesto, nel formato esatto."
        response = call_gpt(prompt, system_prompt)

        if not response:
            return None
        try:
            match_domain = re.search(r"---DOMAIN---(.*?)---PROBLEM---", response, re.DOTALL)
            match_problem = re.search(r"---PROBLEM---(.*)", response, re.DOTALL)
            if not match_domain or not match_problem:
                logger.warning("LLM non ha rispettato il formato richiesto.")
                return None
            domain = match_domain.group(1).strip()
            problem = match_problem.group(1).strip()
            if "(define" not in domain or "(define" not in problem:
                logger.warning("PDDL generato malformato.")
                return None
            return ValidatedPDDL(domain, problem, max_depth, "Generato da Lore (LLM)")
        except Exception as e:
            logger.error(f"Errore parsing PDDL generato da LLM: {e}")
            return None

    def _analyze_lore_with_llm(self) -> Tuple[str, DifficultyLevel]:
        prompt = f"""
            Analizza la seguente storia (LORE) e determina come configurare un problema di pianificazione PDDL.
            LORE: "{self.lore[:2500]}"
            Rispondi ESATTAMENTE con un JSON valido:
            {{"type": "keys_doors", "difficulty": "medium"}}
            Non aggiungere altro testo.
        """
        system_prompt = "Sei un assistente AI che classifica storie per la generazione procedurale di livelli."
        response = call_gpt(prompt, system_prompt)
        detected_type = 'keys_doors'
        detected_diff = DifficultyLevel.EASY
        if response:
            try:
                clean_json = response.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                detected_type = data.get('type', 'keys_doors')
                diff_str = data.get('difficulty', 'easy')
                detected_diff = (DifficultyLevel.HARD if diff_str == 'hard'
                                 else DifficultyLevel.MEDIUM if diff_str == 'medium'
                                 else DifficultyLevel.EASY)
            except Exception as e:
                logger.error(f"Errore analisi LLM fallback: {e}")
        return detected_type, detected_diff

class PDDLPersonalizer:
    def __init__(self, lore_content: str):
        self.lore = lore_content

    def personalize(self, pddl: ValidatedPDDL) -> ValidatedPDDL:
        logger.info("Avvio personalizzazione semantica con LLM...")
        placeholders = self._extract_placeholders(pddl.problem)
        if not placeholders:
            logger.info("Nessun placeholder trovato, salto personalizzazione.")
            return pddl
        mapping = self._get_mapping_from_llm(placeholders)
        if not mapping:
            logger.warning("Mapping fallito o vuoto, uso template originale.")
            return pddl
        problem_personalized = pddl.problem
        count = 0
        for generic, specific in mapping.items():
            if generic in problem_personalized:
                safe_name = self._sanitize_name(specific)
                if safe_name:
                    problem_personalized = problem_personalized.replace(generic, safe_name)
                    count += 1
        logger.info(f"Applicate {count} sostituzioni semantiche.")
        return ValidatedPDDL(
            pddl.domain,
            problem_personalized,
            pddl.expected_plan_length,
            pddl.description + " (Personalizzato AI)"
        )

    def _extract_placeholders(self, pddl_text: str) -> List[str]:

        known_tokens = [
            "room1", "room2", "entrance", "hall", "treasure_room", "secret_chamber",
            "courtyard", "armory", "library", "vault", "throne_room",
            "hero",
            "silver_key", "bronze_key", "golden_key", "copper_key", "master_key",
            "main_door", "treasure_door", "gate1", "gate2", "gate3", "gate4",
            "warehouse", "shop", "home", "depot",
            "truck",
            "parcel", "package", "package1", "package2"
        ]

        found = []
        for token in known_tokens:
            if token in pddl_text:
                found.append(token)
        return found

    def _get_mapping_from_llm(self, placeholders: List[str]) -> Dict[str, str]:
        placeholders_str = ", ".join(placeholders)
        prompt = f"""
            Hai una storia e un set di oggetti generici di un template PDDL.
            Il tuo compito è rinominare gli oggetti generici usando nomi estratti dalla storia, mantenendo coerenza semantica.
            STORIA:
            "{self.lore[:2000]}"
            OGGETTI GENERICI DA RIMPIAZZARE:
            [{placeholders_str}]
            ISTRUZIONI:
            1. Per ogni oggetto generico, trova un nome corrispondente nella storia.
            2. Esempio: se 'hero' è Mario nella storia, mappa "hero": "mario".
            3. Esempio: se 'room1' è una Cripta, mappa "room1": "cripta_oscura".
            4. I nomi devono essere in formato PDDL valido: solo lettere minuscole, numeri e underscore (_). NIENTE SPAZI.
            5. Se non trovi un nome esatto, inventane uno coerente con il tema della storia.
            Restituisci ESATTAMENTE un JSON key-value:
            {{
                "hero": "nome_nella_storia",
                "room1": "nome_luogo_1",
                ...
            }}
        """
        system_prompt = "Sei un esperto di mapping semantico per videogiochi."
        response = call_gpt(prompt, system_prompt)
        try:
            clean_json = response.replace("```json", "").replace("```", "").strip()
            mapping = json.loads(clean_json)
            return mapping
        except Exception as e:
            logger.error(f"Errore parsing JSON mapping: {e}")
            return {}

    def _sanitize_name(self, name: str) -> str:
        name = name.lower().strip()
        name = re.sub(r'\s+', '_', name)
        name = re.sub(r'[^a-z0-9_]', '', name)
        return name

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
                    return True, "Soluzione trovata (file piano non recuperato)", output
            logger.warning("Nessuna soluzione trovata — avvio analisi Reflection Agent")
            try:
                suggestion = self.get_reflection_suggestion(domain_path, problem_path)
                return False, f"REFLECTION_PENDING::{suggestion}", output
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
            logger.info("Analisi errori PDDL con Reflection Agent...")
            with open(domain_path, "r", encoding="utf-8") as f:
                domain_content = f.read()
            with open(problem_path, "r", encoding="utf-8") as f:
                problem_content = f.read()
            system_prompt = "Sei un esperto di PDDL. Correggi errori logici in domini e problemi."
            user_prompt = f"""
            Il seguente domain PDDL e il problem non hanno prodotto alcun piano valido.
            Domain:
            {domain_content}
            Problem:
            {problem_content}
            Identifica l'errore (es. locked door senza chiave, grafo non connesso).
            Restituisci SOLO il domain e il problem corretti, formattati esattamente come:
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
                logger.error("Il Reflection Agent non ha restituito un formato valido.")
                return False

            with open(domain_path, "w", encoding="utf-8") as f:
                f.write(domain_fixed)
            with open(problem_path, "w", encoding="utf-8") as f:
                f.write(problem_fixed)

            logger.info("Reflection Agent: file PDDL aggiornati e salvati.")
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

    def get_reflection_suggestion(self, domain_path: Path, problem_path: Path) -> str:
        try:
            with open(domain_path, "r", encoding="utf-8") as f:
                domain_content = f.read()
            with open(problem_path, "r", encoding="utf-8") as f:
                problem_content = f.read()

            system_prompt = "Sei un esperto di PDDL. Analizza errori logici e proponi correzioni."
            user_prompt = f"""
                Il seguente domain PDDL e problem non producono un piano valido.
                Domain:
                {domain_content}
                Problem:
                {problem_content}
    
                Identifica il problema (es. porta bloccata senza chiave, grafo non connesso).
                Spiega in italiano (2-3 frasi) qual è l'errore e come correggerlo.
                Poi restituisci i file corretti nel formato ESATTO:
                ---SPIEGAZIONE---
                <spiegazione breve dell'errore>
                ---DOMAIN---
                <domain corretto>
                ---PROBLEM---
                <problem corretto>
            """
            return call_gpt(user_prompt, system_prompt)
        except Exception as e:
            logger.exception("Errore get_reflection_suggestion")
            return f"Impossibile analizzare il PDDL: {e}"


def generate_valid_pddl_guaranteed(lore_path: Path, output_dir: Path, fd_path: str, personalize: bool = True) -> Tuple[
    bool, str]:
    logger.info("=" * 70)
    logger.info("GENERAZIONE PDDL - STRATEGIA IBRIDA (Template + LLM Reasoning)")
    logger.info("=" * 70)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(lore_path, 'r', encoding='utf-8') as f:
        lore_content = f.read()

    logger.info("\nSTEP 1: Analisi Lore e Selezione Template...")

    depth_match = re.search(r"[Dd]epth.*?(\d+)\s*[-–]\s*(\d+)", lore_content)
    max_depth = int(depth_match.group(2)) if depth_match else 10
    logger.info(f"Vincolo MaxDepth rilevato dalla Lore: {max_depth}")

    selector = SmartPDDLSelector(lore_content)
    pddl = selector.select_best_pddl()

    if pddl.expected_plan_length > max_depth:
        logger.warning(
            f"Il template selezionato ha piano atteso di {pddl.expected_plan_length} passi, "
            f"superiore al MaxDepth della Lore ({max_depth})."
        )

    if personalize:
        logger.info("\nSTEP 2: Personalizzazione Semantica...")
        personalizer = PDDLPersonalizer(lore_content)
        pddl = personalizer.personalize(pddl)
    else:
        logger.info("\nSTEP 2: Skip personalizzazione")

    logger.info("\nSTEP 3: Salvataggio file...")
    domain_path = output_dir / "domain.pddl"
    problem_path = output_dir / "problem.pddl"

    with open(domain_path, 'w', encoding='utf-8') as f:
        f.write(pddl.domain)
    with open(problem_path, 'w', encoding='utf-8') as f:
        f.write(pddl.problem)
    logger.info(f"✓ File salvati in: {output_dir}")

    logger.info("\nSTEP 4: Validazione finale con Fast Downward ed eventuale Reflection...")
    validator = FastDownwardValidator(fd_path)

    MAX_ATTEMPTS = 3  # Numero massimo di tentativi di auto-correzione

    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info(f"--- Tentativo di validazione {attempt}/{MAX_ATTEMPTS} ---")
        success, message, output = validator.validate(domain_path, problem_path, save_plan_to=output_dir)

        if success:
            logger.info("\nSUCCESSO GARANTITO!")
            logger.info(f"File generati e validati con successo al tentativo {attempt}.")
            aggiunta_commenti_LLM(domain_path, problem_path)
            return True, "PDDL valido generato e personalizzato con successo."

        if "REFLECTION_PENDING::" in message:
            if attempt < MAX_ATTEMPTS:
                logger.warning(f"Validazione fallita. L'Agente di Reflection tenta l'auto-correzione automatica...")
                raw_suggestion = message.split("REFLECTION_PENDING::", 1)[1]
                match_domain = re.search(r"---DOMAIN---(.*?)---PROBLEM---", raw_suggestion, re.DOTALL)
                match_problem = re.search(r"---PROBLEM---(.*)", raw_suggestion, re.DOTALL)

                if match_domain and match_problem:
                    domain_fixed = re.sub(r"```[a-zA-Z]*", "", match_domain.group(1)).replace("```", "").strip()
                    problem_fixed = re.sub(r"```[a-zA-Z]*", "", match_problem.group(1)).replace("```", "").strip()
                    domain_path.write_text(domain_fixed, encoding="utf-8")
                    problem_path.write_text(problem_fixed, encoding="utf-8")
                    logger.info(
                        f"✓ File PDDL aggiornati automaticamente dall'Agente (Pronto per il tentativo {attempt + 1}).")
                    continue
                else:
                    logger.error("Impossibile fare parsing dei blocchi corretti dal Reflection Agent.")

            else:
                logger.error("L'AI ha fallito l'auto-correzione per 3 volte. ATTIVAZIONE FALLBACK DI EMERGENZA.")
                template_type, difficulty = selector._analyze_lore_with_llm()
                logger.info(f"Fallback → Selezione automatica template tipo: {template_type}, difficoltà: {difficulty.value}")
                if template_type == 'keys_doors':
                    if difficulty == DifficultyLevel.EASY:
                        safe_pddl = selector.library.get_keys_doors_easy()
                    elif difficulty == DifficultyLevel.MEDIUM:
                        safe_pddl = selector.library.get_keys_doors_medium()
                    else:
                        safe_pddl = selector.library.get_keys_doors_hard()
                else:
                    if difficulty == DifficultyLevel.EASY:
                        safe_pddl = selector.library.get_logistics_easy()
                    else:
                        safe_pddl = selector.library.get_logistics_medium()
                if personalize:
                    logger.info("Avvio personalizzazione semantica del template di emergenza...")
                    personalizer = PDDLPersonalizer(lore_content)
                    safe_pddl = personalizer.personalize(safe_pddl)
                domain_path.write_text(safe_pddl.domain, encoding="utf-8")
                problem_path.write_text(safe_pddl.problem, encoding="utf-8")

                success_fb, msg_fb, _ = validator.validate(domain_path, problem_path, save_plan_to=output_dir)

                if success_fb:
                    aggiunta_commenti_LLM(domain_path, problem_path)
                    return True, "Generazione completata con successo tramite Template di Fallback strutturato."
                else:
                    return False, f"Errore critico. Anche il template di fallback ha fallito la validazione: {msg_fb}"
        else:
            return False, message

    return False, "Impossibile generare un PDDL valido."
def aggiunta_commenti_LLM(domain_path: Path, problem_path: Path):
    try:
        domain_text = domain_path.read_text(encoding="utf-8")
        problem_text = problem_path.read_text(encoding="utf-8")
        system_prompt = "Sei un esperto PDDL. Aggiungi commenti brevi dopo ';' per spiegare le righe."
        prompt_template = """Annota il seguente codice PDDL con commenti. Non modificare la logica.
        CODICE:
        {content}
        """
        logger.info("Aggiunta commenti al domain...")
        domain_commented = call_gpt(prompt_template.format(content=domain_text), system_prompt)
        logger.info("Aggiunta commenti al problem...")
        problem_commented = call_gpt(prompt_template.format(content=problem_text), system_prompt)
        if domain_commented and problem_commented:
            domain_out = domain_path.parent / f"{domain_path.stem}_commented.pddl"
            problem_out = problem_path.parent / f"{problem_path.stem}_commented.pddl"
            domain_out.write_text(domain_commented, encoding="utf-8")
            problem_out.write_text(problem_commented, encoding="utf-8")
            logger.info(f"File commentati salvati.")
            return domain_out, problem_out
    except Exception as e:
        logger.warning(f"Salto aggiunta commenti per errore: {e}")
    return None


if __name__ == '__main__':
    SCRIPT_DIR = Path(__file__).resolve().parent
    LORE_FILE = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"
    OUTPUT_FOLDER = SCRIPT_DIR / "pddl_output_guaranteed"

    FAST_DOWNWARD = r"C:\Users\ANGELICA\Desktop\SOFTWARE\FASTDOWNWARD\fast-downward-24.06.1\fast-downward.py"

    if not LORE_FILE.exists():
        logger.error(f"File Lore non trovato: {LORE_FILE}")
        LORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LORE_FILE, "w") as f:
            f.write(
                "Genere: Fantasy. Un cavaliere di nome Artu deve trovare la chiave sacra nella foresta proibita per aprire il portale.")
        logger.info("Creato file Lore di test.")

    if not Path(FAST_DOWNWARD).exists():
        logger.error(f"Fast Downward non trovato a: {FAST_DOWNWARD}")
        logger.warning("Lo script proseguirà ma la validazione fallirà.")

    print("\n--- Generazione PDDL AI IBRIDA ---\n")
    success, msg = generate_valid_pddl_guaranteed(
        lore_path=LORE_FILE,
        output_dir=OUTPUT_FOLDER,
        fd_path=FAST_DOWNWARD,
        personalize=True
    )
    print("\nESITO:", msg)