# File: QuestMaster/Game/PDDLParser.py

from pathlib import Path
from typing import List, Dict, Optional
import re
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Rappresenta uno stato del gioco"""
    id: str
    actions_so_far: List[str] = field(default_factory=list)
    current_facts: List[str] = field(default_factory=list)
    available_actions: List[Dict] = field(default_factory=list)
    is_goal: bool = False

    def __hash__(self):
        return hash(self.id)


@dataclass
class GameAction:
    """Rappresenta un'azione PDDL"""
    name: str
    parameters: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    raw_text: str = ""


class PDDLGameGraph:
    """Costruisce il grafo degli stati dal piano PDDL"""

    def __init__(self, domain_path: Path, problem_path: Path, plan_path: Path):
        self.domain_path = domain_path
        self.problem_path = problem_path
        self.plan_path = plan_path

        self.domain_actions = {}
        self.init_facts = []
        self.goal_facts = []
        self.plan_actions = []

        self.states = {}
        self.graph = {}

        # Parse dei file
        self._parse_domain()
        self._parse_problem()
        self._parse_plan()

    def build_graph(self) -> Dict[str, GameState]:
        """Costruisce il grafo completo degli stati"""
        logger.info("🔨 Costruzione grafo degli stati...")

        # Stato iniziale
        initial_state = GameState(
            id='state_0',
            actions_so_far=[],
            current_facts=self.init_facts.copy(),
            is_goal=False
        )

        # Calcola azioni disponibili nello stato iniziale
        initial_state.available_actions = self._get_applicable_actions(initial_state.current_facts)
        self.states['state_0'] = initial_state
        self.graph['state_0'] = []

        # Segui il piano lineare principale
        current_state_id = 'state_0'

        for i, plan_action in enumerate(self.plan_actions):
            next_state_id = f'state_{i + 1}'

            # Applica l'azione
            next_state = self._apply_action(
                self.states[current_state_id],
                plan_action,
                next_state_id
            )

            self.states[next_state_id] = next_state

            # Crea arco nel grafo
            self.graph[current_state_id].append({
                'action': plan_action,
                'next_state': next_state_id,
                'is_main_path': True
            })

            # Inizializza grafo per il nuovo stato
            if next_state_id not in self.graph:
                self.graph[next_state_id] = []

            current_state_id = next_state_id

        # Marca l'ultimo stato come goal
        self.states[current_state_id].is_goal = True

        logger.info(f"✓ Grafo principale creato: {len(self.states)} stati")

        # Aggiungi branch alternativi (opzionale)
        self._add_alternative_branches()

        return self.states

    def _parse_domain(self):
        """Estrae azioni e predicati dal domain PDDL"""
        with open(self.domain_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Trova tutte le azioni
        action_pattern = r'\(:action\s+(\w+)\s+(.*?)\n\s*\)'
        actions = re.finditer(action_pattern, content, re.DOTALL)

        for match in actions:
            action_name = match.group(1)
            action_body = match.group(2)

            # Estrai parametri
            params_match = re.search(r':parameters\s*\((.*?)\)', action_body, re.DOTALL)
            parameters = []
            if params_match:
                param_text = params_match.group(1)
                # Estrai nomi variabili (formato: ?var - type)
                parameters = re.findall(r'\?(\w+)', param_text)

            # Estrai precondizioni
            precond_match = re.search(r':precondition\s*\(and\s*(.*?)\)', action_body, re.DOTALL)
            preconditions = []
            if precond_match:
                precond_text = precond_match.group(1)
                preconditions = re.findall(r'\([^)]+\)', precond_text)

            # Estrai effetti
            effect_match = re.search(r':effect\s*\(and\s*(.*?)\)', action_body, re.DOTALL)
            effects = []
            if effect_match:
                effect_text = effect_match.group(1)
                effects = re.findall(r'\((?:not\s+)?\([^)]+\)\)', effect_text)

            self.domain_actions[action_name] = GameAction(
                name=action_name,
                parameters=parameters,
                preconditions=preconditions,
                effects=effects,
                raw_text=action_body
            )

        logger.info(f"✓ Domain parsed: {len(self.domain_actions)} azioni trovate")

    def _parse_problem(self):
        """Estrae init e goal dal problem PDDL"""
        with open(self.problem_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Estrai init
        init_match = re.search(r'\(:init\s*(.*?)\s*\)\s*\(:goal', content, re.DOTALL)
        if init_match:
            init_text = init_match.group(1)
            self.init_facts = [f.strip() for f in re.findall(r'\([^)]+\)', init_text)]

        # Estrai goal
        goal_match = re.search(r'\(:goal\s*(.*?)\s*\)\s*\)', content, re.DOTALL)
        if goal_match:
            goal_text = goal_match.group(1)
            # Rimuovi 'and' se presente
            goal_text = re.sub(r'\(and\s*', '', goal_text)
            self.goal_facts = [f.strip() for f in re.findall(r'\([^)]+\)', goal_text)]

        logger.info(f"✓ Problem parsed: {len(self.init_facts)} fatti iniziali, {len(self.goal_facts)} goal")

    def _parse_plan(self):
        """Legge il piano e lo converte in lista di azioni"""
        with open(self.plan_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()

            # Salta commenti e linee vuote
            if not line or line.startswith(';') or line.startswith('=') or line.startswith('Step'):
                continue

            # Formato: (action_name param1 param2) oppure "Step X: (action ...)"
            # Rimuovi "Step X: " se presente
            line = re.sub(r'^Step\s+\d+:\s*', '', line)

            # Estrai azione
            match = re.match(r'\((\w+)\s*(.*?)\)', line)
            if match:
                action_name = match.group(1)
                params_text = match.group(2).strip()
                parameters = params_text.split() if params_text else []

                # Cerca l'azione nel domain
                domain_action = self.domain_actions.get(action_name)

                if domain_action:
                    # Crea istanza dell'azione con parametri concreti
                    action_instance = {
                        'name': action_name,
                        'parameters': parameters,
                        'preconditions': domain_action.preconditions,
                        'effects': self._instantiate_effects(domain_action, parameters)
                    }
                    self.plan_actions.append(action_instance)

        logger.info(f"✓ Piano parsed: {len(self.plan_actions)} azioni")

    def _instantiate_effects(self, domain_action: GameAction, concrete_params: List[str]) -> List[str]:
        """Sostituisce i parametri variabili con quelli concreti negli effetti"""
        if len(concrete_params) != len(domain_action.parameters):
            return domain_action.effects  # Fallback

        # Crea mapping ?var -> valore_concreto
        param_map = {f'?{var}': concrete_params[i]
                     for i, var in enumerate(domain_action.parameters)}

        instantiated = []
        for effect in domain_action.effects:
            instantiated_effect = effect
            for var, value in param_map.items():
                instantiated_effect = instantiated_effect.replace(var, value)
            instantiated.append(instantiated_effect)

        return instantiated

    def _apply_action(self, state: GameState, action: Dict, new_state_id: str) -> GameState:
        """Applica un'azione e calcola il nuovo stato"""
        new_facts = state.current_facts.copy()

        # Applica effetti
        for effect in action['effects']:
            effect_clean = effect.strip()

            # Effetto negativo: (not (predicato ...))
            if effect_clean.startswith('(not'):
                # Estrai il predicato da rimuovere
                fact_to_remove = re.search(r'\(not\s+(\([^)]+\))\)', effect_clean)
                if fact_to_remove:
                    fact = fact_to_remove.group(1)
                    if fact in new_facts:
                        new_facts.remove(fact)
            else:
                # Effetto positivo
                if effect_clean not in new_facts:
                    new_facts.append(effect_clean)

        # Crea nuovo stato
        new_state = GameState(
            id=new_state_id,
            actions_so_far=state.actions_so_far + [action['name']],
            current_facts=new_facts,
            is_goal=self._check_goal(new_facts)
        )

        # Calcola azioni disponibili
        new_state.available_actions = self._get_applicable_actions(new_facts)

        return new_state

    def _get_applicable_actions(self, current_facts: List[str]) -> List[Dict]:
        """Trova tutte le azioni applicabili nello stato corrente"""
        applicable = []

        # Per ora, ritorniamo tutte le azioni del domain
        # In una versione completa, dovresti controllare le precondizioni
        for action_name, domain_action in self.domain_actions.items():
            applicable.append({
                'name': action_name,
                'parameters': domain_action.parameters,
                'preconditions': domain_action.preconditions
            })

        return applicable

    def _check_goal(self, current_facts: List[str]) -> bool:
        """Controlla se i fatti correnti soddisfano il goal"""
        for goal in self.goal_facts:
            if goal not in current_facts:
                return False
        return True

    def _add_alternative_branches(self):
        """Aggiunge percorsi alternativi per aumentare la rigiocabilità"""
        logger.info("🌿 Aggiunta branch alternativi...")

        added_branches = 0

        # Per ogni stato non-goal nel percorso principale
        for state_id, state in list(self.states.items()):
            if state.is_goal:
                continue

            # Trova azioni disponibili ma non usate nel piano principale
            main_actions = [edge['action']['name'] for edge in self.graph[state_id]]

            for available_action in state.available_actions:
                if available_action['name'] not in main_actions:
                    # Crea un branch alternativo
                    alt_state_id = f"{state_id}_alt_{available_action['name']}"

                    # Evita loop infiniti
                    if alt_state_id in self.states:
                        continue

                    # Simula l'applicazione dell'azione (semplificato)
                    alt_state = GameState(
                        id=alt_state_id,
                        actions_so_far=state.actions_so_far + [available_action['name']],
                        current_facts=state.current_facts.copy(),  # Semplificato
                        available_actions=[],
                        is_goal=False
                    )

                    self.states[alt_state_id] = alt_state
                    self.graph[state_id].append({
                        'action': available_action,
                        'next_state': alt_state_id,
                        'is_main_path': False
                    })

                    added_branches += 1

                    # Limita il numero di branch per evitare esplosione combinatoria
                    if added_branches >= 10:
                        break

            if added_branches >= 10:
                break

        logger.info(f"✓ Aggiunti {added_branches} branch alternativi")

    def export_to_json(self, output_path: Path):
        """Esporta il grafo in formato JSON"""
        import json

        graph_data = {
            'states': {
                state_id: {
                    'id': state.id,
                    'actions_so_far': state.actions_so_far,
                    'is_goal': state.is_goal,
                    'fact_count': len(state.current_facts)
                }
                for state_id, state in self.states.items()
            },
            'edges': {
                state_id: [
                    {
                        'action': edge['action']['name'],
                        'next_state': edge['next_state'],
                        'is_main_path': edge.get('is_main_path', False)
                    }
                    for edge in edges
                ]
                for state_id, edges in self.graph.items()
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2)

        logger.info(f"✓ Grafo esportato in: {output_path}")


if __name__ == '__main__':
    # Test
    logging.basicConfig(level=logging.INFO)

    SCRIPT_DIR = Path(__file__).resolve().parent
    pddl_dir = SCRIPT_DIR.parent / "Generate_PDDL" / "pddl_output_guaranteed"

    parser = PDDLGameGraph(
        domain_path=pddl_dir / "domain.pddl",
        problem_path=pddl_dir / "problem.pddl",
        plan_path=pddl_dir / "plan_readable.txt"
    )

    states = parser.build_graph()
    print(f"\n📊 Grafo costruito: {len(states)} stati")

    # Esporta per debug
    parser.export_to_json(SCRIPT_DIR / "graph_debug.json")