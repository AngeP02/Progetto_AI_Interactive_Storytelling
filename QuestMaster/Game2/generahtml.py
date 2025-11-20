"""
PDDL Story Graph Generator v2 - FIXED
Genera un grafo strutturato CORRETTO che rispecchia il SAS plan.

CORREZIONI:
- ✅ Stato PDDL reale accumulato in ogni nodo
- ✅ Applica effetti SAS effettivi
- ✅ Ogni path: inizio → azione SAS → branching narrativo → azione SAS → ...
- ✅ Niente "chose_option", solo fatti PDDL veri
"""

from dotenv import load_dotenv
from openai import OpenAI
import logging
import os
import json
import re
from typing import List, Set, Tuple, Dict, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


# ============================================================================
# PARSING PDDL/SAS - CORRETTO
# ============================================================================

def parse_sas_plan(plan_content: str) -> List[Tuple]:
    """Estrae azioni dal piano SAS in ordine."""
    actions = []
    for line in plan_content.strip().split('\n'):
        line = line.strip()
        if line.startswith('(') and not line.startswith(';'):
            parts = line[1:-1].strip().split()
            if parts:
                actions.append(tuple(parts))
    logger.info(f"✓ Parsed {len(actions)} SAS actions")
    return actions


def parse_pddl_problem(problem_content: str) -> Dict:
    """Estrae stato iniziale e goal."""
    init_match = re.search(r':init\s+\((.*?)\s*\)', problem_content, re.DOTALL)
    goal_match = re.search(r':goal\s+\((.*?)\s*\)', problem_content, re.DOTALL)

    init_facts = set()
    if init_match:
        for match in re.findall(r'\(([^()]+)\)', init_match.group(1)):
            parts = tuple(match.strip().split())
            if parts and parts[0] not in ('and', 'or'):
                init_facts.add(parts)

    goal_facts = set()
    if goal_match:
        for match in re.findall(r'\(([^()]+)\)', goal_match.group(1)):
            parts = tuple(match.strip().split())
            if parts and parts[0] not in ('and', 'or'):
                goal_facts.add(parts)

    logger.info(f"✓ Initial state: {len(init_facts)} facts")
    logger.info(f"✓ Goal state: {len(goal_facts)} facts")

    return {
        "initial_state": init_facts,
        "goal_state": goal_facts
    }


def parse_pddl_domain(domain_content: str) -> Dict[str, Dict]:
    """Estrae azioni dal domain.pddl."""
    actions = {}

    # Pattern per estrarre azioni PDDL
    action_pattern = r':action\s+(\w+)\s*:parameters\s*\((.*?)\)\s*:precondition\s*\((.*?)\)\s*:effect\s*\((.*?)\)(?=\s*(?::action|$))'

    for match in re.finditer(action_pattern, domain_content, re.DOTALL):
        action_name = match.group(1)
        params_str = match.group(2)
        precond_str = match.group(3)
        effect_str = match.group(4)

        # Parse parametri: ?x - type
        params = []
        for p in params_str.split('-'):
            p = p.strip()
            if p.startswith('?'):
                params.append(p)

        # Parse precondizioni ed effetti
        preconditions = []
        for lit_match in re.findall(r'\(([^()]+)\)', precond_str):
            parts = tuple(lit_match.strip().split())
            if parts and parts[0] not in ('and', 'or', 'not'):
                preconditions.append(parts)

        effects = []
        for lit_match in re.findall(r'\(([^()]+)\)', effect_str):
            parts = tuple(lit_match.strip().split())
            if parts and parts[0] not in ('and', 'or'):
                effects.append(parts)

        actions[action_name] = {
            "params": params,
            "preconditions": preconditions,
            "effects": effects
        }

    logger.info(f"✓ Parsed {len(actions)} PDDL actions")
    return actions


# ============================================================================
# MODELLI DI DATI
# ============================================================================

@dataclass
class GraphNode:
    """Nodo del grafo."""
    node_id: str
    depth: int
    node_type: str  # "scene", "choice", "consequence"
    action_name: Optional[str] = None
    state: Optional[List[str]] = None  # Stato PDDL attuale (stringificato)
    state_added: Optional[List[str]] = None  # Fatti aggiunti
    state_removed: Optional[List[str]] = None  # Fatti rimossi
    choice_index: Optional[int] = None
    parent_id: Optional[str] = None

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "depth": self.depth,
            "node_type": self.node_type,
            "action_name": self.action_name,
            "state": self.state or [],
            "state_added": self.state_added or [],
            "state_removed": self.state_removed or [],
            "choice_index": self.choice_index,
            "parent_id": self.parent_id
        }


# ============================================================================
# GENERATORE GRAFO - FIXED
# ============================================================================

class PDDLGraphGenerator:
    """Genera grafo scaffolding CORRETTO."""

    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.lore = ""

    def _load_files(self, lore_path: str, plan_path: str, domain_path: str, problem_path: str):
        """Carica file."""
        logger.info("\n📂 Caricamento file...")

        with open(lore_path, 'r', encoding='utf-8') as f:
            self.lore = f.read()

        with open(plan_path, 'r', encoding='utf-8') as f:
            self.plan_actions = parse_sas_plan(f.read())

        with open(domain_path, 'r', encoding='utf-8') as f:
            self.pddl_domain = parse_pddl_domain(f.read())

        with open(problem_path, 'r', encoding='utf-8') as f:
            problem_data = parse_pddl_problem(f.read())
            self.initial_state = problem_data["initial_state"]
            self.goal_state = problem_data["goal_state"]

    def _apply_pddl_action(self, current_state: Set[Tuple], action_tuple: Tuple) -> Tuple[Set[Tuple], Set[Tuple], Set[Tuple]]:
        """
        Applica un'azione PDDL e ritorna (nuovo_stato, aggiunti, rimossi).
        """
        action_name = action_tuple[0]

        if action_name not in self.pddl_domain:
            logger.warning(f"⚠️ Azione {action_name} non trovata nel dominio")
            return current_state, set(), set()

        action_def = self.pddl_domain[action_name]
        params = action_def["params"]
        args = action_tuple[1:]

        # Crea binding: ?param -> arg
        binding = dict(zip(params, args))

        # Applica effetti
        new_state = set(current_state)

        for effect in action_def["effects"]:
            # Applica binding
            bound_effect = tuple(binding.get(arg, arg) for arg in effect)

            if bound_effect[0] == 'not' and len(bound_effect) > 1:
                # Rimozione: (not (fatto arg1 arg2))
                fact_to_remove = bound_effect[1:]
                new_state.discard(fact_to_remove)
            else:
                # Aggiunta
                new_state.add(bound_effect)

        # Calcola diff
        added = new_state - current_state
        removed = current_state - new_state

        return new_state, added, removed

    def _generate_choice_descriptions(self, current_state: Set[Tuple], action: Tuple,
                                      num_choices: int) -> List[str]:
        """Genera descrizioni brevi per le scelte."""

        state_str = '\n'.join([f"  • {' '.join(f)}" for f in sorted(list(current_state))[:5]])

        system_prompt = """Sei un game designer. Generi ALTERNATIVE per una scelta narrativa.

OUTPUT SOLO: {"choices": ["desc1", "desc2"]}

REGOLE:
1. Ogni choice: 5-10 parole, una frase
2. ALTERNATIVE DIVERSE (non ripetitive)
3. Fattibili con lo stato PDDL corrente"""

        user_prompt = f"""AZIONE: {' '.join(action)}

STATO:
{state_str}

Generi {num_choices} alternative diverse (JSON)."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            text = response.choices[0].message.content.strip()
            data = json.loads(text)
            return data.get("choices", [f"Opzione {i+1}" for i in range(num_choices)])
        except Exception as e:
            logger.warning(f"⚠️ LLM fallback: {e}")
            return [f"Opzione {i+1}" for i in range(num_choices)]

    def generate(self, lore_path: str, plan_path: str, domain_path: str,
                 problem_path: str, output_json: str,
                 branching: int = 2, max_depth: int = 3) -> Dict:
        """Genera grafo scaffolding CORRETTO."""

        self._load_files(lore_path, plan_path, domain_path, problem_path)

        all_nodes: List[GraphNode] = []
        edges: Dict[str, List[str]] = {}

        current_state = self.initial_state

        logger.info(f"\n🎮 Generazione grafo scaffolding (branching={branching}, depth={max_depth})...\n")

        # PRINCIPALE: Per ogni azione nel piano SAS
        for action_idx, action_tuple in enumerate(self.plan_actions):
            logger.info(f"\n[{action_idx+1}/{len(self.plan_actions)}] SAS: {' '.join(action_tuple)}")

            old_state = current_state.copy()

            # Applica azione PDDL
            current_state, added, removed = self._apply_pddl_action(current_state, action_tuple)

            # 1. CREA NODO SCENA (rappresenta l'azione SAS eseguita)
            scene_id = str(action_idx)
            scene_node = GraphNode(
                node_id=scene_id,
                depth=0,
                node_type="scene",
                action_name=' '.join(action_tuple),
                state=[' '.join(f) for f in sorted(list(current_state))],
                state_added=[' '.join(f) for f in sorted(list(added))],
                state_removed=[' '.join(f) for f in sorted(list(removed))]
            )
            all_nodes.append(scene_node)
            edges[scene_id] = []

            logger.info(f"   Scene {scene_id}: +{len(added)} facts, -{len(removed)} facts")

            # 2. GENERA BRANCHING (scelte narrative)
            choice_descriptions = self._generate_choice_descriptions(
                current_state, action_tuple, branching
            )

            # Funzione ricorsiva per build del branching tree
            def build_branching(parent_id: str, current_depth: int, state: Set[Tuple]):
                """Costruisce l'albero di scelte narrative."""

                if current_depth >= max_depth:
                    return

                is_choice_level = (current_depth % 2 == 1)

                if is_choice_level:
                    # Crea nodi CHOICE
                    for choice_idx in range(1, branching + 1):
                        choice_id = f"{parent_id}.{choice_idx}"

                        choice_node = GraphNode(
                            node_id=choice_id,
                            depth=current_depth,
                            node_type="choice",
                            state=[' '.join(f) for f in sorted(list(state))],
                            choice_index=choice_idx,
                            parent_id=parent_id
                        )
                        all_nodes.append(choice_node)

                        if parent_id not in edges:
                            edges[parent_id] = []
                        edges[parent_id].append(choice_id)

                        # Ricorsione: prossimo livello (consequence)
                        if current_depth + 1 < max_depth:
                            consequence_id = f"{choice_id}.0"

                            # Simula cambio stato dalla scelta (marker)
                            new_state = state.copy()

                            consequence_node = GraphNode(
                                node_id=consequence_id,
                                depth=current_depth + 1,
                                node_type="consequence",
                                state=[' '.join(f) for f in sorted(list(new_state))],
                                parent_id=choice_id
                            )
                            all_nodes.append(consequence_node)

                            if choice_id not in edges:
                                edges[choice_id] = []
                            edges[choice_id].append(consequence_id)

                            # Continua ricorsione
                            build_branching(consequence_id, current_depth + 2, new_state)

            # Avvia branching da questa scena
            build_branching(scene_id, 1, current_state)

        # Costruisci output
        output = {
            "metadata": {
                "total_actions": len(self.plan_actions),
                "max_depth": max_depth,
                "branching": branching,
                "total_nodes": len(all_nodes),
                "model": self.model
            },
            "nodes": [n.to_dict() for n in all_nodes],
            "edges": edges
        }

        # Salva
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"\n✅ Grafo generato!")
        logger.info(f"   Nodi totali: {len(all_nodes)}")
        logger.info(f"   Salvato: {output_json}\n")

        return output


# ============================================================================
# ESECUZIONE
# ============================================================================

if __name__ == "__main__":
    BASE_PATH = r"C:\Users\ANGELICA\Desktop\ANGELICA\UNICAL\MAGISTRALE\I ANNO\SECONDO SEMESTRE\INTELLIGENZA ARTIFICIALE\PROGETTO\CODICE\QuestMaster"

    generator = PDDLGraphGenerator()

    output = generator.generate(
        lore_path=os.path.join(BASE_PATH, "Lore", "Generated_Lore", "Lore.md"),
        plan_path=os.path.join(BASE_PATH, "ChatBot", "pddl_output", "sas_plan"),
        domain_path=os.path.join(BASE_PATH, "ChatBot", "pddl_output", "domain.pddl"),
        problem_path=os.path.join(BASE_PATH, "ChatBot", "pddl_output", "problem.pddl"),
        output_json=os.path.join(BASE_PATH, "Game", "story_graph_scaffolding.json"),
        branching=2,
        max_depth=3
    )