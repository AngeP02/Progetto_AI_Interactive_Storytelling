# File: QuestMaster/Game/HTMLGenerator.py

from pathlib import Path
import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class InteractiveGameGenerator:
    """Genera l'HTML del gioco interattivo"""

    def __init__(self, states: Dict, graph: Dict, narratives: Dict, config: Dict):
        self.states = states
        self.graph = graph
        self.narratives = narratives
        self.config = config

    def generate_game_html(self, output_path: Path):
        """Genera il file HTML completo del gioco"""
        logger.info("🌐 Generazione HTML del gioco...")

        # Prepara i dati per JavaScript
        game_data = self._prepare_game_data()

        # Genera HTML
        html_content = self._get_html_template()

        # Inietta i dati del gioco
        html_content = html_content.replace(
            '/* GAME_DATA_PLACEHOLDER */',
            f'const GAME_DATA = {json.dumps(game_data, indent=2, ensure_ascii=False)};'
        )

        # Salva file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ HTML generato: {output_path}")

    def _prepare_game_data(self) -> Dict:
        """Prepara la struttura dati per il gioco JavaScript"""
        game_data = {
            'config': {
                'title': self.config.get('theme', 'QuestMaster Adventure'),
                'genre': self.config.get('genre', 'Fantasy'),
                'tone': self.config.get('tone', 'Adventurous'),
                'graphics': self.config.get('graphics', 'Text Only')
            },
            'initial_state': 'state_0',
            'states': {}
        }

        # Per ogni stato, aggiungi la narrativa e le scelte
        for state_id, state in self.states.items():
            narrative = self.narratives.get(state_id, {})
            edges = self.graph.get(state_id, [])

            game_data['states'][state_id] = {
                'id': state_id,
                'is_goal': state.is_goal,
                'description': narrative.get('description', 'Descrizione non disponibile.'),
                'choices': []
            }

            # Aggiungi le scelte con i loro stati di destinazione
            narrative_choices = narrative.get('choices', [])

            for i, edge in enumerate(edges):
                choice_data = {
                    'action': edge['action']['name'],
                    'next_state': edge['next_state'],
                    'is_main_path': edge.get('is_main_path', False)
                }

                # Associa il testo narrativo se disponibile
                if i < len(narrative_choices):
                    choice_data['text'] = narrative_choices[i].get('text', f"Esegui {edge['action']['name']}")
                else:
                    choice_data['text'] = f"Esegui {edge['action']['name']}"

                game_data['states'][state_id]['choices'].append(choice_data)

        return game_data

    def _get_html_template(self) -> str:
        """Ritorna il template HTML del gioco"""
        return '''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuestMaster - Interactive Adventure</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: url("/static/img/SfondoChatbot.png");
            background-size: cover;
            background-attachment: fixed;
            min-height: 100vh;
            padding: 20px;
        }

        .game-container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            min-height: 600px;
        }

        .game-header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #5eb7ca;
        }

        .game-header h1 {
            color: #5eb7ca;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        }

        .game-header .genre-tag {
            display: inline-block;
            background: linear-gradient(135deg, #7eddb2 0%, #5eb7ca 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }

        .narrative-section {
            background: rgba(247, 250, 252, 0.8);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .narrative-text {
            font-size: 1.2em;
            line-height: 1.8;
            color: #333;
            margin-bottom: 20px;
            text-align: justify;
        }

        .choices-section {
            margin-top: 20px;
        }

        .choices-title {
            font-size: 1.1em;
            font-weight: bold;
            color: #5eb7ca;
            margin-bottom: 15px;
            text-align: center;
        }

        .choices-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .choice-button {
            padding: 18px 25px;
            background: linear-gradient(135deg, #e4b281 0%, #dc8a3f 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(220, 138, 63, 0.3);
            text-align: left;
            position: relative;
            overflow: hidden;
        }

        .choice-button::before {
            content: '→';
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.5em;
            opacity: 0.7;
            transition: transform 0.3s;
        }

        .choice-button:hover:not(:disabled) {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(220, 138, 63, 0.4);
        }

        .choice-button:hover::before {
            transform: translateY(-50%) translateX(5px);
        }

        .choice-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .choice-button.main-path {
            background: linear-gradient(135deg, #7eddb2 0%, #5eb7ca 100%);
            box-shadow: 0 4px 15px rgba(94, 183, 202, 0.3);
        }

        .choice-button.main-path::after {
            content: '⭐';
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.2em;
        }

        .victory-screen {
            text-align: center;
            padding: 40px;
        }

        .victory-screen h2 {
            font-size: 3em;
            color: #5eb7ca;
            margin-bottom: 20px;
            animation: victoryPulse 2s infinite;
        }

        @keyframes victoryPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .victory-screen .victory-message {
            font-size: 1.3em;
            line-height: 1.8;
            color: #333;
            margin-bottom: 30px;
        }

        .victory-screen .stats {
            background: rgba(126, 221, 178, 0.2);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
        }

        .victory-screen .stats p {
            font-size: 1.1em;
            margin: 10px 0;
            color: #666;
        }

        .restart-button {
            padding: 18px 40px;
            background: linear-gradient(135deg, #7eddb2 0%, #5eb7ca 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 18px;
            font-weight: bold;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(94, 183, 202, 0.3);
        }

        .restart-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(94, 183, 202, 0.4);
        }

        .game-progress {
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(126, 221, 178, 0.1);
            border-radius: 10px;
        }

        .game-progress .steps {
            font-size: 0.9em;
            color: #666;
        }

        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: #5eb7ca;
        }

        .loading::after {
            content: '...';
            animation: dots 1.5s infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        @media (max-width: 768px) {
            .game-container {
                padding: 20px;
            }

            .game-header h1 {
                font-size: 2em;
            }

            .narrative-text {
                font-size: 1.1em;
            }

            .choice-button {
                font-size: 14px;
                padding: 15px 20px;
            }
        }
    </style>
</head>
<body>
    <div class="game-container">
        <div class="game-header">
            <h1 id="gameTitle">QuestMaster</h1>
            <div class="genre-tag" id="genreTag">Fantasy</div>
        </div>

        <div class="game-progress" id="gameProgress" style="display: none;">
            <div class="steps">Passo <span id="currentStep">1</span></div>
        </div>

        <div id="gameContent">
            <div class="loading">Caricamento avventura</div>
        </div>
    </div>

    <script>
        /* GAME_DATA_PLACEHOLDER */

        class AdventureGame {
            constructor(gameData) {
                this.data = gameData;
                this.currentState = gameData.initial_state;
                this.history = [];
                this.stepCount = 0;
            }

            start() {
                // Imposta titolo e genere
                document.getElementById('gameTitle').textContent = this.data.config.title;
                document.getElementById('genreTag').textContent = this.data.config.genre;

                // Mostra lo stato iniziale
                this.renderState(this.currentState);
            }

            renderState(stateId) {
                const state = this.data.states[stateId];
                const container = document.getElementById('gameContent');

                if (!state) {
                    container.innerHTML = `
                        <div class="narrative-section">
                            <p style="color: red;">Errore: Stato non trovato (${stateId})</p>
                            <button class="restart-button" onclick="location.reload()">
                                Riavvia Gioco
                            </button>
                        </div>
                    `;
                    return;
                }

                // Aggiorna progresso
                this.stepCount++;
                document.getElementById('gameProgress').style.display = 'block';
                document.getElementById('currentStep').textContent = this.stepCount;

                // Stato goal (vittoria)
                if (state.is_goal) {
                    this.renderVictory(state);
                    return;
                }

                // Stato normale
                let html = `
                    <div class="narrative-section">
                        <div class="narrative-text">${state.description}</div>
                `;

                if (state.choices && state.choices.length > 0) {
                    html += `
                        <div class="choices-section">
                            <div class="choices-title">Cosa fai?</div>
                            <div class="choices-container">
                    `;

                    state.choices.forEach((choice, index) => {
                        const mainPathClass = choice.is_main_path ? 'main-path' : '';
                        html += `
                            <button class="choice-button ${mainPathClass}" 
                                    onclick="game.makeChoice('${choice.next_state}')">
                                ${choice.text}
                            </button>
                        `;
                    });

                    html += `
                            </div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="choices-section">
                            <p style="text-align: center; color: #999;">
                                Nessuna azione disponibile
                            </p>
                            <button class="restart-button" onclick="location.reload()">
                                Riavvia Gioco
                            </button>
                        </div>
                    `;
                }

                html += '</div>';
                container.innerHTML = html;

                // Scroll smooth verso l'alto
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            renderVictory(state) {
                const container = document.getElementById('gameContent');

                container.innerHTML = `
                    <div class="victory-screen">
                        <h2>🎉 Vittoria! 🎉</h2>
                        <div class="victory-message">
                            ${state.description}
                        </div>
                        <div class="stats">
                            <p><strong>Passi completati:</strong> ${this.stepCount}</p>
                            <p><strong>Genere:</strong> ${this.data.config.genre}</p>
                            <p><strong>Difficoltà:</strong> ${this.data.config.tone}</p>
                        </div>
                        <button class="restart-button" onclick="location.reload()">
                            🔄 Gioca Ancora
                        </button>
                    </div>
                `;

                // Confetti effect (opzionale)
                this.celebrateVictory();
            }

            makeChoice(nextStateId) {
                // Salva nella storia
                this.history.push(this.currentState);

                // Vai al prossimo stato
                this.currentState = nextStateId;
                this.renderState(nextStateId);
            }

            celebrateVictory() {
                // Effetto confetti semplice con emoji
                const confettiCount = 30;
                for (let i = 0; i < confettiCount; i++) {
                    this.createConfetti();
                }
            }

            createConfetti() {
                const confetti = document.createElement('div');
                confetti.textContent = ['🎉', '⭐', '🎊', '✨'][Math.floor(Math.random() * 4)];
                confetti.style.position = 'fixed';
                confetti.style.left = Math.random() * 100 + 'vw';
                confetti.style.top = '-50px';
                confetti.style.fontSize = '2em';
                confetti.style.zIndex = '9999';
                confetti.style.pointerEvents = 'none';
                confetti.style.animation = `fall ${2 + Math.random() * 3}s linear`;

                document.body.appendChild(confetti);

                setTimeout(() => confetti.remove(), 5000);
            }
        }

        // Aggiungi animazione CSS per confetti
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fall {
                to {
                    transform: translateY(100vh) rotate(360deg);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);

        // Avvia il gioco quando la pagina è caricata
        let game;
        window.addEventListener('DOMContentLoaded', () => {
            if (typeof GAME_DATA === 'undefined') {
                document.getElementById('gameContent').innerHTML = `
                    <div class="narrative-section">
                        <p style="color: red; text-align: center;">
                            Errore: Dati del gioco non caricati correttamente.
                        </p>
                    </div>
                `;
                return;
            }

            game = new AdventureGame(GAME_DATA);
            game.start();
        });

        // Gestione errori globali
        window.addEventListener('error', (event) => {
            console.error('Errore nel gioco:', event.error);
        });
    </script>
</body>
</html>
'''


if __name__ == '__main__':
    # Test
    logging.basicConfig(level=logging.INFO)

    # Dati mock per test
    mock_states = {
        'state_0': type('obj', (object,), {'id': 'state_0', 'is_goal': False})(),
        'state_1': type('obj', (object,), {'id': 'state_1', 'is_goal': True})()
    }

    mock_graph = {
        'state_0': [
            {'action': {'name': 'move'}, 'next_state': 'state_1', 'is_main_path': True}
        ]
    }

    mock_narratives = {
        'state_0': {
            'description': 'Ti trovi all\'ingresso di una grotta misteriosa.',
            'choices': [{'text': 'Entri nella grotta', 'action': 'move'}]
        },
        'state_1': {
            'description': 'Hai scoperto il tesoro nascosto! Vittoria!',
            'choices': []
        }
    }

    mock_config = {
        'theme': 'Test Adventure',
        'genre': 'Fantasy',
        'tone': 'Mysterious',
        'graphics': 'Text Only'
    }

    generator = InteractiveGameGenerator(mock_states, mock_graph, mock_narratives, mock_config)

    output_path = Path(__file__).parent / "test_game.html"
    generator.generate_game_html(output_path)

    print(f"✓ HTML di test generato: {output_path}")