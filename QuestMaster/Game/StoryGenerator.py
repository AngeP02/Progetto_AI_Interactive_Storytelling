# File: QuestMaster/Game/StoryGenerator.py

from pathlib import Path
import requests
import json
import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StoryNode:
    """Un nodo della storia (una scena)"""
    id: str
    title: str
    narrative: str  # Testo lungo e coinvolgente
    choices: List[Dict] = field(default_factory=list)  # Lista di scelte con conseguenze
    is_ending: bool = False
    ending_type: str = ""  # "victory", "defeat", "neutral"
    pddl_state: str = ""  # Stato PDDL associato (per validazione)


class InteractiveStoryGenerator:
    """Genera una storia interattiva completa usando LLM + vincoli PDDL"""

    def __init__(self, lore_path: Path, pddl_constraints: Dict, config: Dict):
        self.lore = self._load_lore(lore_path)
        self.constraints = pddl_constraints
        self.config = config
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3"

        # Estrai info dal lore
        self.genre = self._extract_genre()
        self.tone = self._extract_tone()
        self.theme = config.get('theme', 'Una quest avventurosa')

        # Calcola profondità target dalla length
        self.target_depth = self._calculate_target_depth(config.get('length', 'Medium'))

    def generate_full_story(self) -> Dict[str, StoryNode]:
        """
        Genera la storia completa con tutti i branch

        Returns:
            Dict di nodi: {node_id: StoryNode}
        """
        logger.info("📖 Generazione storia interattiva completa...")

        # Step 1: Genera la struttura della storia (outline)
        story_outline = self._generate_story_outline()

        # Step 2: Genera ogni scena con narrativa dettagliata
        story_nodes = self._generate_detailed_scenes(story_outline)

        # Step 3: Valida rispetto ai vincoli PDDL
        validated_nodes = self._validate_against_pddl(story_nodes)

        logger.info(f"✓ Storia generata: {len(validated_nodes)} scene totali")

        return validated_nodes

    def _generate_story_outline(self) -> Dict:
        """Genera la struttura ad albero della storia INCREMENTALMENTE"""
        logger.info("📝 Generazione outline incrementale...")

        outline = {
            "title": self.theme,
            "starting_scene": None,
            "scenes": {},
            "endings": {}
        }

        # Step 1: Genera scena iniziale
        logger.info("  [1/4] Generazione scena iniziale...")
        starting_scene = self._generate_single_scene("scene_1", "scena iniziale", is_start=True)
        outline["starting_scene"] = starting_scene

        # Step 2: Genera scene di livello 2 (dalle scelte della scena iniziale)
        logger.info("  [2/4] Generazione scene livello 2...")
        level_2_scenes = {}
        for choice in starting_scene.get("choices", []):
            next_id = choice.get("leads_to", "")
            if next_id and not next_id.startswith("ending"):
                scene = self._generate_single_scene(next_id, f"seguito di '{choice['text']}'")
                level_2_scenes[next_id] = scene
        outline["scenes"].update(level_2_scenes)

        # Step 3: Genera scene di livello 3 (se target_depth > 4)
        if self.target_depth > 4:
            logger.info("  [3/4] Generazione scene livello 3...")
            for scene_id, scene in list(level_2_scenes.items()):
                for choice in scene.get("choices", []):
                    next_id = choice.get("leads_to", "")
                    if next_id and not next_id.startswith("ending") and next_id not in outline["scenes"]:
                        new_scene = self._generate_single_scene(next_id, f"seguito di '{choice['text']}'")
                        outline["scenes"][next_id] = new_scene

        # Step 4: Genera finali
        logger.info("  [4/4] Generazione finali...")
        endings = self._generate_endings()
        outline["endings"] = endings

        # Collega scene orfane ai finali
        self._link_orphans_to_endings(outline)

        logger.info(f"✓ Outline completato: {len(outline['scenes'])} scene, {len(outline['endings'])} finali")
        return outline

    def _generate_single_scene(self, scene_id: str, context: str, is_start: bool = False) -> Dict:
        """Genera UNA singola scena (veloce, JSON piccolo)"""

        system_prompt = f"""Sei un autore di {self.genre} con tono {self.tone}.
Genera UNA SOLA scena per una storia interattiva."""

        start_context = "Questa è la scena di apertura della storia. " if is_start else ""

        prompt = f"""{start_context}Genera una scena per: {context}

TEMA GENERALE: {self.theme}

Restituisci SOLO questo JSON (niente altro testo):
{{
  "id": "{scene_id}",
  "title": "Titolo scena (max 6 parole)",
  "summary": "Riassunto di 1 frase",
  "choices": [
    {{
      "text": "Prima scelta (1 frase)",
      "leads_to": "scene_{scene_id}_a",
      "consequence": "Cosa succede"
    }},
    {{
      "text": "Seconda scelta (1 frase)",
      "leads_to": "scene_{scene_id}_b",
      "consequence": "Cosa succede"
    }}
  ]
}}

Se questa scena dovrebbe portare a un finale, usa "leads_to": "ending_victory" o "ending_defeat".
Max 300 token. SOLO JSON.
"""

        response = self._call_ollama(prompt, system_prompt, num_predict=350)

        try:
            scene = self._extract_json(response)
            return scene
        except Exception as e:
            logger.warning(f"Errore parsing scena {scene_id}, uso fallback: {e}")
            # Fallback deterministico
            return {
                "id": scene_id,
                "title": f"Capitolo {scene_id}",
                "summary": context,
                "choices": [
                    {"text": "Procedi con cautela", "leads_to": "ending_victory", "consequence": "Avanzi"},
                    {"text": "Agisci rapidamente", "leads_to": "ending_defeat", "consequence": "Rischi"}
                ]
            }

    def _generate_endings(self) -> Dict:
        """Genera tutti i finali in un'unica chiamata (sono brevi)"""

        system_prompt = f"""Genera finali per una storia {self.genre}."""

        prompt = f"""Genera 3 finali per questa storia:
TEMA: {self.theme}

JSON richiesto:
{{
  "ending_victory": {{
    "id": "ending_victory",
    "title": "Titolo vittoria (max 4 parole)",
    "summary": "Cosa succede (1 frase)",
    "type": "victory"
  }},
  "ending_defeat": {{
    "id": "ending_defeat",
    "title": "Titolo sconfitta (max 4 parole)",
    "summary": "Cosa succede (1 frase)",
    "type": "defeat"
  }},
  "ending_neutral": {{
    "id": "ending_neutral",
    "title": "Titolo finale alternativo (max 4 parole)",
    "summary": "Cosa succede (1 frase)",
    "type": "neutral"
  }}
}}

SOLO JSON, max 250 token.
"""

        response = self._call_ollama(prompt, system_prompt, num_predict=300)

        try:
            endings = self._extract_json(response)
            return endings
        except:
            # Fallback
            return {
                "ending_victory": {
                    "id": "ending_victory",
                    "title": "Vittoria",
                    "summary": "Hai completato la missione con successo",
                    "type": "victory"
                },
                "ending_defeat": {
                    "id": "ending_defeat",
                    "title": "Sconfitta",
                    "summary": "La missione è fallita",
                    "type": "defeat"
                },
                "ending_neutral": {
                    "id": "ending_neutral",
                    "title": "Fine Ambigua",
                    "summary": "Le cose sono cambiate per sempre",
                    "type": "neutral"
                }
            }

    def _link_orphans_to_endings(self, outline: Dict):
        """Collega scene senza uscite ai finali"""
        all_referenced = set()

        # Trova tutti i nodi referenziati
        if outline["starting_scene"]:
            for choice in outline["starting_scene"].get("choices", []):
                all_referenced.add(choice.get("leads_to", ""))

        for scene in outline["scenes"].values():
            for choice in scene.get("choices", []):
                all_referenced.add(choice.get("leads_to", ""))

        # Scene che dovevano essere generate ma mancano
        existing_scenes = set(outline["scenes"].keys())
        existing_endings = set(outline["endings"].keys())

        orphans = all_referenced - existing_scenes - existing_endings - {""}

        if orphans:
            logger.info(f"  Collegamento {len(orphans)} scene orfane ai finali...")
            for orphan_id in orphans:
                # Sostituisci con un finale casuale
                ending_id = list(outline["endings"].keys())[0] if outline["endings"] else "ending_victory"

                # Trova e sostituisci il riferimento
                for scene in [outline["starting_scene"]] + list(outline["scenes"].values()):
                    if scene:
                        for choice in scene.get("choices", []):
                            if choice.get("leads_to") == orphan_id:
                                choice["leads_to"] = ending_id

    def _generate_detailed_scenes(self, outline: Dict) -> Dict[str, StoryNode]:
        """Genera la narrativa dettagliata per ogni scena"""
        story_nodes = {}

        # Scena iniziale
        starting_scene = outline.get('starting_scene', {})
        if starting_scene:
            try:
                node = self._generate_scene_narrative(starting_scene, is_start=True)
                story_nodes[node.id] = node
            except Exception as e:
                logger.error(f"Errore scena iniziale, uso fallback: {e}")
                # Fallback con narrativa base
                story_nodes['scene_1'] = StoryNode(
                    id='scene_1',
                    title=starting_scene.get('title', 'Inizio'),
                    narrative=f"{starting_scene.get('summary', 'La tua avventura inizia.')} Devi fare una scelta.",
                    choices=[
                        {'text': c.get('text', 'Continua'), 'next_node': c.get('leads_to', '')}
                        for c in starting_scene.get('choices', [])
                    ],
                    is_ending=False
                )

        # Scene intermedie
        scenes = outline.get('scenes', {})
        for scene_id, scene_data in scenes.items():
            try:
                node = self._generate_scene_narrative(scene_data)
                story_nodes[node.id] = node
            except Exception as e:
                logger.warning(f"Errore scena {scene_id}, uso fallback: {e}")
                # Fallback
                story_nodes[scene_id] = StoryNode(
                    id=scene_id,
                    title=scene_data.get('title', 'Capitolo'),
                    narrative=scene_data.get('summary', 'La storia continua...'),
                    choices=[
                        {'text': c.get('text', 'Continua'), 'next_node': c.get('leads_to', '')}
                        for c in scene_data.get('choices', [])
                    ],
                    is_ending=False
                )

        # Finali
        endings = outline.get('endings', {})
        for ending_id, ending_data in endings.items():
            try:
                node = self._generate_ending_narrative(ending_data)
                story_nodes[node.id] = node
            except Exception as e:
                logger.warning(f"Errore finale {ending_id}, uso fallback: {e}")
                # Fallback
                story_nodes[ending_id] = StoryNode(
                    id=ending_id,
                    title=ending_data.get('title', 'Fine'),
                    narrative=ending_data.get('summary', 'La storia è conclusa.'),
                    choices=[],
                    is_ending=True,
                    ending_type=ending_data.get('type', 'neutral')
                )

        return story_nodes

    def _generate_scene_narrative(self, scene_data: Dict, is_start: bool = False) -> StoryNode:
        """Genera la narrativa completa per una singola scena"""
        scene_id = scene_data.get('id', 'unknown')
        scene_title = scene_data.get('title', 'Capitolo Senza Titolo')
        scene_summary = scene_data.get('summary', '')
        choices_outline = scene_data.get('choices', [])

        logger.info(f"  Generando narrativa per: {scene_id}")

        system_prompt = f"""Sei un autore di narrativa {self.genre} con stile {self.tone}.
Scrivi in seconda persona (tu, ti, tuo) e presente. Sii CONCISO ma evocativo."""

        intro = "Questa è l'apertura della storia. " if is_start else ""

        # ⚡ RIDOTTO: Da 300-500 parole a 100-150 parole (2 paragrafi)
        prompt = f"""{intro}Espandi questa scena in 2 BREVI paragrafi (100-150 parole TOTALI):

TITOLO: {scene_title}
TRAMA: {scene_summary}

Requisiti:
- 2 paragrafi (non di più!)
- Seconda persona (tu/ti)
- Crea tensione
- Finisci con momento di scelta

SOLO la narrativa (niente scelte, quelle dopo).
Max 150 parole totali.
"""

        # ⚡ RIDOTTO: num_predict da 800 a 250
        narrative = self._call_ollama(prompt, system_prompt, num_predict=250)

        # Pulisci la narrativa
        narrative = self._clean_narrative(narrative)

        # Genera descrizioni per le scelte (BREVI)
        choices = []
        for choice_data in choices_outline:
            # ⚡ Non espandere le scelte, usa il testo base
            choice_text = choice_data.get('text', 'Continua')
            choices.append({
                'text': choice_text,
                'next_node': choice_data.get('leads_to', ''),
                'consequence': choice_data.get('consequence', '')
            })

        return StoryNode(
            id=scene_id,
            title=scene_title,
            narrative=narrative,
            choices=choices,
            is_ending=False
        )

    def _generate_ending_narrative(self, ending_data: Dict) -> StoryNode:
        """Genera la narrativa per un finale"""
        ending_id = ending_data.get('id', 'unknown_ending')
        ending_title = ending_data.get('title', 'Fine')
        ending_summary = ending_data.get('summary', '')
        ending_type = ending_data.get('type', 'neutral')

        logger.info(f"  Generando finale: {ending_id} ({ending_type})")

        system_prompt = f"""Sei un autore che scrive finali memorabili per storie {self.genre}.
Il finale deve essere emotivamente impattante e soddisfacente.
"""

        prompt = f"""Scrivi un finale {ending_type} per questa storia:

TITOLO: {ending_title}
TIPO: {ending_type}
CONTESTO: {ending_summary}

Il finale deve:
- Essere lungo 2-3 paragrafi
- Risolvere la tensione narrativa
- Essere emotivamente risonante
- {"Celebrare il trionfo del protagonista" if ending_type == "victory" else "Mostrare le conseguenze del fallimento" if ending_type == "defeat" else "Lasciare un messaggio significativo"}

Scrivi in seconda persona (tu/ti).
"""

        narrative = self._call_ollama(prompt, system_prompt)
        narrative = self._clean_narrative(narrative)

        return StoryNode(
            id=ending_id,
            title=ending_title,
            narrative=narrative,
            choices=[],  # Nessuna scelta nei finali
            is_ending=True,
            ending_type=ending_type
        )

    def _enhance_choice_text(self, basic_text: str, context: str) -> str:
        """Migliora il testo di una scelta rendendolo più descrittivo"""
        system_prompt = "Sei un esperto di game design per narrativa interattiva."

        prompt = f"""Trasforma questa scelta base in una descrizione coinvolgente (1-2 frasi):

SCELTA BASE: {basic_text}
CONTESTO: {context}

La scelta migliorata deve:
- Essere in seconda persona
- Suggerire conseguenze possibili
- Essere intrigante
- Massimo 2 frasi

Esempio:
Base: "Vai a sinistra"
Migliorato: "Ti avventuri nel corridoio di sinistra, dove senti echi di voci lontane. Potrebbe essere pericoloso, ma anche promettente."

Genera SOLO il testo della scelta migliorata, niente altro.
"""

        enhanced = self._call_ollama(prompt, system_prompt)
        return self._clean_narrative(enhanced)

    def _validate_against_pddl(self, nodes: Dict[str, StoryNode]) -> Dict[str, StoryNode]:
        """Valida che la storia rispetti i vincoli PDDL e sia COMPLETA"""
        logger.info("✓ Validazione vincoli PDDL e completezza grafo...")

        validated = nodes.copy()

        # 1. Trova nodi orfani (scelte che puntano a nodi inesistenti)
        orphan_references = set()
        for node in validated.values():
            for choice in node.choices:
                next_node_id = choice.get('next_node', '')
                if next_node_id and next_node_id not in validated:
                    orphan_references.add(next_node_id)
                    logger.warning(f"⚠️ Riferimento orfano trovato: {next_node_id}")

        # 2. Crea nodi di emergenza per riferimenti orfani
        for orphan_id in orphan_references:
            logger.info(f"  Creando nodo di emergenza per: {orphan_id}")
            validated[orphan_id] = StoryNode(
                id=orphan_id,
                title="Svolta Inaspettata",
                narrative="Qualcosa di imprevisto accade, cambiando il corso della tua avventura. Devi adattarti rapidamente alla nuova situazione.",
                choices=[
                    {
                        'text': 'Continua la tua missione con rinnovata determinazione',
                        'next_node': self._find_nearest_ending(validated)
                    }
                ],
                is_ending=False
            )

        # 3. Identifica nodi con scelte vuote (NON finali)
        empty_nodes = [
            node_id for node_id, node in validated.items()
            if not node.is_ending and len(node.choices) == 0
        ]

        if empty_nodes:
            logger.warning(f"⚠️ Trovati {len(empty_nodes)} nodi senza scelte (dead ends)")

            for node_id in empty_nodes:
                logger.info(f"  Correggendo dead end: {node_id}")

                # Trasforma in finale se è un vicolo cieco
                node = validated[node_id]

                # Se ha un titolo che suggerisce un finale, marcalo come tale
                if any(keyword in node.title.lower() for keyword in
                       ['fine', 'morte', 'vittoria', 'sconfitta', 'epilogo']):
                    node.is_ending = True
                    node.ending_type = self._guess_ending_type(node.title, node.narrative)
                    logger.info(f"    → Convertito in finale ({node.ending_type})")
                else:
                    # Altrimenti aggiungi una scelta di emergenza verso un finale
                    nearest_ending = self._find_nearest_ending(validated)
                    node.choices.append({
                        'text': 'Concludi la tua avventura',
                        'next_node': nearest_ending
                    })
                    logger.info(f"    → Aggiunta scelta verso {nearest_ending}")

        # 4. Verifica che ci sia almeno un finale vittorioso
        endings = [n for n in validated.values() if n.is_ending]
        victory_endings = [n for n in endings if n.ending_type == 'victory']

        if not victory_endings:
            logger.warning("⚠️ Nessun finale vittorioso trovato, ne creo uno")
            victory_node = StoryNode(
                id='ending_victory_emergency',
                title='Vittoria Conquistata',
                narrative='Dopo molte prove e tribulazioni, hai finalmente raggiunto il tuo obiettivo. La missione è compiuta, e puoi finalmente riposare sapendo di aver fatto la differenza. Il tuo nome sarà ricordato.',
                choices=[],
                is_ending=True,
                ending_type='victory'
            )
            validated[victory_node.id] = victory_node

            # Collega almeno un nodo al finale vittorioso
            non_ending_nodes = [n for n in validated.values() if not n.is_ending]
            if non_ending_nodes:
                random_node = non_ending_nodes[-1]  # Prendi l'ultimo
                random_node.choices.append({
                    'text': 'Compi l\'azione finale decisiva',
                    'next_node': victory_node.id
                })

        # 5. Verifica connettività (tutti i nodi devono essere raggiungibili)
        reachable = self._find_reachable_nodes(validated)
        unreachable = set(validated.keys()) - reachable

        if unreachable:
            logger.warning(f"⚠️ Trovati {len(unreachable)} nodi irraggiungibili")
            for node_id in unreachable:
                logger.info(f"  Nodo isolato rimosso: {node_id}")
                del validated[node_id]

        # 6. Statistiche finali
        final_endings = [n for n in validated.values() if n.is_ending]
        logger.info(f"✓ Validazione completata:")
        logger.info(f"  • Nodi totali: {len(validated)}")
        logger.info(f"  • Scene interattive: {len([n for n in validated.values() if not n.is_ending])}")
        logger.info(f"  • Finali: {len(final_endings)}")
        logger.info(f"    - Vittoria: {len([n for n in final_endings if n.ending_type == 'victory'])}")
        logger.info(f"    - Sconfitta: {len([n for n in final_endings if n.ending_type == 'defeat'])}")
        logger.info(
            f"    - Alternativi: {len([n for n in final_endings if n.ending_type not in ['victory', 'defeat']])}")

        return validated

    def _find_nearest_ending(self, nodes: Dict[str, StoryNode]) -> str:
        """Trova il finale più vicino (preferibilmente vittorioso)"""
        endings = [n for n in nodes.values() if n.is_ending]

        # Preferisci finali vittoriosi
        victory_endings = [n for n in endings if n.ending_type == 'victory']
        if victory_endings:
            return victory_endings[0].id

        # Altrimenti qualsiasi finale
        if endings:
            return endings[0].id

        # Se non ci sono finali, ritorna il primo nodo (fallback)
        return list(nodes.keys())[0] if nodes else 'scene_1'

    def _guess_ending_type(self, title: str, narrative: str) -> str:
        """Indovina il tipo di finale dal titolo/narrativa"""
        text = (title + ' ' + narrative).lower()

        if any(word in text for word in ['vittoria', 'trionfo', 'successo', 'completato', 'raggiunto', 'vinto']):
            return 'victory'
        elif any(word in text for word in ['sconfitta', 'morte', 'fallimento', 'perso', 'fine']):
            return 'defeat'
        else:
            return 'neutral'

    def _find_reachable_nodes(self, nodes: Dict[str, StoryNode]) -> set:
        """Trova tutti i nodi raggiungibili dal nodo iniziale (BFS)"""
        if not nodes:
            return set()

        # Assumi che il primo nodo sia l'iniziale
        start_node_id = list(nodes.keys())[0]

        visited = set()
        queue = [start_node_id]

        while queue:
            current_id = queue.pop(0)

            if current_id in visited or current_id not in nodes:
                continue

            visited.add(current_id)

            # Aggiungi tutti i nodi raggiungibili dalle scelte
            current_node = nodes[current_id]
            for choice in current_node.choices:
                next_id = choice.get('next_node', '')
                if next_id and next_id not in visited:
                    queue.append(next_id)

        return visited

    def _calculate_target_depth(self, length: str) -> int:
        """Calcola la profondità target dalla length"""
        if 'Short' in length or '2-5' in length:
            return 4
        elif 'Long' in length or '10+' in length:
            return 8
        else:  # Medium
            return 6

    def _generate_fallback_outline(self) -> Dict:
        """Genera un outline di fallback se l'LLM fallisce"""
        return {
            "title": self.theme,
            "starting_scene": {
                "id": "scene_1",
                "title": "L'Inizio",
                "summary": "Inizi la tua avventura",
                "choices": [
                    {"text": "Procedi con cautela", "leads_to": "scene_2", "consequence": "Avanzi"},
                    {"text": "Agisci audacemente", "leads_to": "scene_3", "consequence": "Prendi rischi"}
                ]
            },
            "scenes": {
                "scene_2": {
                    "id": "scene_2",
                    "title": "Approccio Cauto",
                    "summary": "Procedi con prudenza",
                    "choices": [
                        {"text": "Continua", "leads_to": "ending_victory", "consequence": "Successo"}
                    ]
                },
                "scene_3": {
                    "id": "scene_3",
                    "title": "Azione Audace",
                    "summary": "Agisci coraggiosamente",
                    "choices": [
                        {"text": "Persisti", "leads_to": "ending_victory", "consequence": "Vittoria"}
                    ]
                }
            },
            "endings": {
                "ending_victory": {
                    "id": "ending_victory",
                    "title": "Vittoria",
                    "summary": "Hai completato la missione",
                    "type": "victory"
                }
            }
        }

    def _clean_narrative(self, text: str) -> str:
        """Pulisce il testo narrativo da artefatti"""
        # Rimuovi markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)

        # Rimuovi linee vuote multiple
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return text.strip()

    def _call_ollama(self, prompt: str, system_prompt: str, num_predict: int = 250) -> str:
        """Chiama Ollama LLM con timeout e retry AGGRESSIVI"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.85,
                        "top_p": 0.9,
                        "num_predict": num_predict
                    }
                }

                # ⚡ Timeout RIDOTTO: 30s per chiamata (era 60s)
                timeout = 30

                response = requests.post(self.ollama_url, json=payload, timeout=timeout)
                response.raise_for_status()

                result = response.json()
                return result.get('response', '').strip()

            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Timeout tentativo {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    # ⚡ Riduci DRASTICAMENTE: -50% ogni volta
                    num_predict = max(100, int(num_predict * 0.5))
                    logger.info(f"  Ritento con num_predict={num_predict}")
                    continue
                else:
                    # ⚡ Dopo 3 tentativi, usa fallback invece di exception
                    logger.error("⏱️ Timeout finale, uso testo fallback")
                    return "La storia continua in modo inaspettato. Devi prendere una decisione importante."
            except Exception as e:
                logger.error(f"Errore chiamata Ollama: {e}")
                if attempt < max_retries - 1:
                    continue
                else:
                    # ⚡ Fallback invece di crash
                    return "Un evento importante si verifica. Come reagisci?"

    def _extract_json(self, text: str) -> Dict:
        """Estrae JSON dalla risposta LLM"""
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

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

    def export_story(self, nodes: Dict[str, StoryNode], output_path: Path):
        """Esporta la storia in JSON per debug"""
        story_data = {
            node_id: {
                'id': node.id,
                'title': node.title,
                'narrative': node.narrative[:100] + '...',
                'choices_count': len(node.choices),
                'is_ending': node.is_ending,
                'ending_type': node.ending_type
            }
            for node_id, node in nodes.items()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(story_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Storia esportata in: {output_path}")


if __name__ == '__main__':
    # Test
    logging.basicConfig(level=logging.INFO)

    SCRIPT_DIR = Path(__file__).resolve().parent
    lore_file = SCRIPT_DIR.parent / "Lore" / "Generated_Lore" / "Lore.md"

    test_config = {
        'theme': 'Un detective robotico indaga su un omicidio in una città cyberpunk',
        'genre': 'Cyberpunk Noir',
        'tone': 'Dark and Mysterious',
        'length': 'Medium (5-10 min)'
    }

    generator = InteractiveStoryGenerator(
        lore_path=lore_file,
        pddl_constraints={},
        config=test_config
    )

    story = generator.generate_full_story()

    # Esporta per debug
    generator.export_story(story, SCRIPT_DIR / "story_debug.json")

    print(f"\n✓ Storia generata: {len(story)} nodi")
    print(f"  - Scene iniziali: {sum(1 for n in story.values() if not n.is_ending)}")
    print(f"  - Finali: {sum(1 for n in story.values() if n.is_ending)}")