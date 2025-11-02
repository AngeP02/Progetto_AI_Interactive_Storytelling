# File: QuestMaster/Game/NarrativeGenerator.py

from pathlib import Path
import requests
import json
import re
import logging
from typing import Dict, List
from .PDDLParser import GameState

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """Genera descrizioni narrative per ogni stato del gioco usando LLM"""

    def __init__(self, lore_path: Path, states: Dict[str, GameState], graph: Dict):
        self.lore = self._load_lore(lore_path)
        self.states = states
        self.graph = graph
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3"

        # Estrai info chiave dal lore
        self.genre = self._extract_genre()
        self.tone = self._extract_tone()

    def generate_all_narratives(self) -> Dict[str, Dict]:
        """Genera testo narrativo per ogni stato del grafo"""
        logger.info("📖 Generazione narrativa per tutti gli stati...")

        narratives = {}
        total_states = len(self.states)

        for i, (state_id, state) in enumerate(self.states.items(), 1):
            logger.info(f"  [{i}/{total_states}] Generando narrativa per {state_id}...")

            try:
                narratives[state_id] = self._generate_state_narrative(state, state_id)
            except Exception as e:
                logger.error(f"Errore narrativa per {state_id}: {e}")
                # Fallback
                narratives[state_id] = self._generate_fallback_narrative(state, state_id)

        logger.info(f"✓ Narrativa generata per {len(narratives)} stati")
        return narratives

    def _generate_state_narrative(self, state: GameState, state_id: str) -> Dict:
        """Genera descrizione + scelte per uno stato specifico"""

        # Costruisci il contesto
        actions_summary = ', '.join(state.actions_so_far[-3:]) if state.actions_so_far else 'nessuna'

        # Ottieni le scelte disponibili
        edges = self.graph.get(state_id, [])
        available_choices = [
            {
                'action': edge['action']['name'],
                'parameters': edge['action'].get('parameters', [])
            }
            for edge in edges
        ]

        # Se è lo stato goal
        if state.is_goal:
            return self._generate_victory_narrative()

        # System prompt
        system_prompt = f"""Sei un narratore esperto di storie {self.genre} con tono {self.tone}.
Il tuo compito è creare una scena coinvolgente per un gioco interattivo testuale.

LORE COMPLETO:
{self.lore[:1500]}

VINCOLI:
- Usa seconda persona ("ti trovi", "vedi", "puoi")
- Descrizione: 3-4 frasi max, vivida e immersiva
- Per ogni scelta: 1 frase chiara che spiega cosa succederà
- Mantieni il tono {self.tone}
- Sii coerente con le azioni già eseguite
"""

        # User prompt
        prompt = f"""Genera la narrativa per questo stato del gioco:

CONTESTO:
- Azioni già eseguite dal giocatore: {actions_summary}
- Numero di scelte disponibili: {len(available_choices)}
- Azioni disponibili: {[c['action'] for c in available_choices]}

Genera un JSON con questa struttura ESATTA:
{{
  "description": "Descrizione della scena corrente (3-4 frasi in seconda persona)",
  "choices": [
    {{"action": "{available_choices[0]['action'] if available_choices else 'move'}", "text": "Testo della scelta in seconda persona"}},
    {{"action": "{available_choices[1]['action'] if len(available_choices) > 1 else 'pick'}", "text": "Testo della scelta in seconda persona"}}
  ]
}}

IMPORTANTE: 
- Genera ESATTAMENTE {len(available_choices)} choices
- Ogni choice DEVE corrispondere a una delle azioni disponibili
- Usa solo JSON valido, nessun altro testo
"""

        response = self._call_ollama(prompt, system_prompt)

        try:
            # Estrai JSON dalla risposta
            narrative_data = self._extract_json(response)

            # Valida che abbiamo il numero corretto di scelte
            if len(narrative_data.get('choices', [])) != len(available_choices):
                logger.warning(f"Numero scelte errato per {state_id}, rigenerazione...")
                raise ValueError("Mismatch nel numero di scelte")

            # Assicurati che le azioni matchino
            for i, choice in enumerate(narrative_data['choices']):
                if i < len(available_choices):
                    choice['action'] = available_choices[i]['action']
                    choice['parameters'] = available_choices[i]['parameters']

            return narrative_data

        except Exception as e:
            logger.warning(f"Parsing fallito per {state_id}, uso fallback: {e}")
            return self._generate_fallback_narrative(state, state_id)

    def _generate_victory_narrative(self) -> Dict:
        """Genera la narrativa per lo stato di vittoria"""
        system_prompt = f"""Sei un narratore esperto. Genera un messaggio di vittoria epico e soddisfacente 
per una storia {self.genre} con tono {self.tone}."""

        prompt = f"""Genera un messaggio di vittoria coinvolgente (2-3 frasi) che celebri il successo del giocatore.
Basati sul lore:
{self.lore[:500]}

Rispondi SOLO con un JSON:
{{
  "description": "Messaggio di vittoria epico e soddisfacente",
  "choices": []
}}
"""

        response = self._call_ollama(prompt, system_prompt)

        try:
            return self._extract_json(response)
        except:
            return {
                "description": "🎉 Hai completato la quest con successo! Congratulazioni, avventuriero!",
                "choices": []
            }

    def _generate_fallback_narrative(self, state: GameState, state_id: str) -> Dict:
        """Genera narrativa di fallback se l'LLM fallisce"""
        edges = self.graph.get(state_id, [])

        description = f"Ti trovi in un punto cruciale della tua avventura. "
        if state.actions_so_far:
            last_action = state.actions_so_far[-1]
            description += f"Dopo aver eseguito {last_action}, "
        description += "devi decidere come procedere."

        choices = []
        for edge in edges:
            action_name = edge['action']['name']
            params = edge['action'].get('parameters', [])

            # Testo di default basato sull'azione
            if action_name == 'move':
                text = f"Ti dirigi verso {params[1] if len(params) > 1 else 'un nuovo luogo'}"
            elif action_name == 'pick' or action_name == 'pick-key':
                text = f"Raccogli {params[0] if params else 'un oggetto'}"
            elif action_name == 'unlock':
                text = f"Sblocchi {params[2] if len(params) > 2 else 'un passaggio'}"
            else:
                text = f"Esegui l'azione: {action_name}"

            choices.append({
                'action': action_name,
                'parameters': params,
                'text': text
            })

        return {
            'description': description,
            'choices': choices
        }

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Chiama Ollama LLM"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": 600
                }
            }

            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            return result.get('response', '').strip()

        except Exception as e:
            logger.error(f"Errore chiamata Ollama: {e}")
            raise

    def _extract_json(self, text: str) -> Dict:
        """Estrae JSON dalla risposta LLM"""
        # Rimuovi markdown code blocks se presenti
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # Cerca JSON
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("Nessun JSON trovato nella risposta")

        json_text = match.group(0)
        return json.loads(json_text)

    def _load_lore(self, path: Path) -> str:
        """Carica il file lore"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Errore caricamento lore: {e}")
            return "Lore non disponibile."

    def _extract_genre(self) -> str:
        """Estrae il genere dal lore"""
        match = re.search(r'\*\*Genere:\*\*\s*([^\n|]+)', self.lore, re.IGNORECASE)
        return match.group(1).strip() if match else "Fantasy"

    def _extract_tone(self) -> str:
        """Estrae il tono dal lore"""
        match = re.search(r'\*\*Tono:\*\*\s*([^\n|]+)', self.lore, re.IGNORECASE)
        return match.group(1).strip() if match else "Avventuroso"

    def export_narratives(self, output_path: Path, narratives: Dict):
        """Esporta le narrative generate in JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(narratives, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Narrative esportate in: {output_path}")


if __name__ == '__main__':
    # Test
    logging.basicConfig(level=logging.INFO)

    from .PDDLParser import PDDLGameGraph

    SCRIPT_DIR = Path(__file__).resolve().parent
    pddl_dir = SCRIPT_DIR.parent / "Generate_PDDL" / "pddl_output_guaranteed"
    lore_file = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"

    # Costruisci grafo
    parser = PDDLGameGraph(
        domain_path=pddl_dir / "domain.pddl",
        problem_path=pddl_dir / "problem.pddl",
        plan_path=pddl_dir / "plan_readable.txt"
    )
    states = parser.build_graph()

    # Genera narrativa
    narrator = NarrativeGenerator(lore_file, states, parser.graph)
    narratives = narrator.generate_all_narratives()

    # Esporta
    narrator.export_narratives(SCRIPT_DIR / "narratives_debug.json", narratives)

    print(f"\n✓ Narrative generate per {len(narratives)} stati")