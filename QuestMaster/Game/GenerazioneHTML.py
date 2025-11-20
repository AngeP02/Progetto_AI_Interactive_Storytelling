#!/usr/bin/env python3
"""
Interactive Narrative Game Generator - Versione 2
Semplificata e robusta per evitare errori
"""

import json
from pathlib import Path


def load_story_json(filepath):
    """Carica il file JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File non trovato: {filepath}")
        print("   Posiziona il file JSON nella stessa cartella dello script")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Errore JSON: {e}")
        exit(1)


def build_html_game(story_data):
    """Genera l'HTML del gioco narrativo"""

    # Converti i dati in una stringa JSON sicura per JavaScript
    story_json = json.dumps(story_data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Eden Chronicles - Narrativa Interattiva</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0a0e27 0%, #16213e 100%);
            color: #00ff88;
            line-height: 1.6;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
        }}

        header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #00ff88;
            padding-bottom: 20px;
        }}

        h1 {{
            font-size: 2.5em;
            text-shadow: 0 0 10px #00ff88;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: #00ccff;
            font-style: italic;
        }}

        .scene-box {{
            background: rgba(22, 33, 62, 0.8);
            border: 1px solid #00ff88;
            border-radius: 5px;
            padding: 30px;
            margin: 20px 0;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.1);
        }}

        .scene-title {{
            color: #00ccff;
            font-size: 1.2em;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .scene-text {{
            font-size: 1.05em;
            line-height: 1.8;
            margin: 20px 0;
            color: #e0e0e0;
        }}

        .choices {{
            margin-top: 30px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .btn {{
            background: linear-gradient(90deg, rgba(0, 255, 136, 0.1), rgba(0, 204, 255, 0.1));
            border: 1px solid #00ff88;
            color: #00ff88;
            padding: 15px 20px;
            text-align: left;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
            border-radius: 3px;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .btn:hover {{
            background: linear-gradient(90deg, rgba(0, 255, 136, 0.3), rgba(0, 204, 255, 0.3));
            box-shadow: 0 0 15px rgba(0, 255, 136, 0.5);
            transform: translateX(5px);
        }}

        .btn:active {{
            opacity: 0.7;
        }}

        .progress {{
            width: 100%;
            height: 8px;
            background: rgba(0, 255, 136, 0.1);
            border-radius: 4px;
            margin: 15px 0;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #00ccff);
            transition: width 0.3s ease;
        }}

        .meta {{
            color: #666;
            font-size: 0.85em;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(0, 255, 136, 0.2);
        }}

        .ending {{
            background: linear-gradient(135deg, rgba(255, 102, 0, 0.1), rgba(0, 255, 136, 0.1));
            border: 2px solid #ff6600;
            border-radius: 5px;
            padding: 40px;
            text-align: center;
            margin-top: 40px;
        }}

        .ending h2 {{
            color: #ff6600;
            font-size: 2em;
            margin-bottom: 20px;
        }}

        .restart {{
            background: #ff6600;
            border: none;
            color: white;
            padding: 12px 30px;
            font-size: 1em;
            cursor: pointer;
            border-radius: 3px;
            margin-top: 20px;
            transition: all 0.3s ease;
        }}

        .restart:hover {{
            background: #ff8833;
            box-shadow: 0 0 15px rgba(255, 102, 0, 0.5);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ NEW EDEN CHRONICLES ⚡</h1>
            <p class="subtitle">Una storia interattiva di cyberpunk, tradimenti e scelte impossibili</p>
        </header>

        <div id="game"></div>
    </div>

    <script>
        const storyData = {story_json};

        class Game {{
            constructor() {{
                this.actionIdx = 0;
                this.nodePath = [];
                this.init();
            }}

            init() {{
                this.nodePath = [0]; // Indice del nodo radice
                this.render();
            }}

            getAction() {{
                return storyData.actions[this.actionIdx];
            }}

            getNode(idx) {{
                const action = this.getAction();
                if (!action || !action.nodes) return null;
                return action.nodes[idx];
            }}

            getCurrentNode() {{
                const nodeIdx = this.nodePath[this.nodePath.length - 1];
                return this.getNode(nodeIdx);
            }}

            // Trova i figli di un nodo basato sulla struttura
            getChildren() {{
                const action = this.getAction();
                const currentNode = this.getCurrentNode();
                if (!currentNode) return [];

                const currentDepth = currentNode.depth;
                const children = [];

                // Cerca i nodi con depth + 1
                for (let i = 0; i < action.nodes.length; i++) {{
                    const node = action.nodes[i];
                    if (node.depth === currentDepth + 1) {{
                        // Verifica che sia effettivamente un figlio (stesso prefisso ID)
                        const currPrefix = currentNode.id.split('.').slice(0, -1).join('.');
                        const nodePrefix = node.id.split('.').slice(0, -1).join('.');

                        if (currPrefix === nodePrefix || currentNode.id.endsWith('.' + node.id.split('.')[node.id.split('.').length - 2])) {{
                            children.push({{idx: i, node: node}});
                        }}
                    }}
                }}

                return children;
            }}

            selectChoice(idx) {{
                this.nodePath.push(idx);
                this.render();
                window.scrollTo(0, 0);
            }}

            nextAction() {{
                if (this.actionIdx < storyData.actions.length - 1) {{
                    this.actionIdx++;
                    this.nodePath = [0];
                    this.render();
                    window.scrollTo(0, 0);
                }}
            }}

            isEnded() {{
                const children = this.getChildren();
                return children.length === 0 && this.actionIdx >= storyData.actions.length - 1;
            }}

            canContinue() {{
                const children = this.getChildren();
                return children.length === 0 && this.actionIdx < storyData.actions.length - 1;
            }}

            render() {{
                const gameDiv = document.getElementById('game');
                gameDiv.innerHTML = '';

                const currentNode = this.getCurrentNode();
                if (!currentNode) {{
                    gameDiv.innerHTML = '<p style="color: red;">Errore: Nodo non trovato</p>';
                    return;
                }}

                const box = document.createElement('div');
                box.className = 'scene-box';

                // Titolo
                const title = document.createElement('div');
                title.className = 'scene-title';
                title.textContent = `[ACT ${{this.actionIdx + 1}}] ${{currentNode.type.toUpperCase()}}`;
                box.appendChild(title);

                // Progress
                const totalNodes = storyData.actions.reduce((sum, a) => sum + a.nodes.length, 0);
                const currentNodeGlobal = this.actionIdx * 13 + this.nodePath.length;
                const progress = Math.min((currentNodeGlobal / totalNodes) * 100, 100);

                const progressDiv = document.createElement('div');
                progressDiv.className = 'progress';
                const fill = document.createElement('div');
                fill.className = 'progress-fill';
                fill.style.width = progress + '%';
                progressDiv.appendChild(fill);
                box.appendChild(progressDiv);

                // Testo scena
                const text = document.createElement('div');
                text.className = 'scene-text';
                text.textContent = currentNode.text;
                box.appendChild(text);

                // Scelte o prosecuzione
                const children = this.getChildren();

                if (children.length > 0) {{
                    const choicesDiv = document.createElement('div');
                    choicesDiv.className = 'choices';

                    children.forEach(child => {{
                        const btn = document.createElement('button');
                        btn.className = 'btn';
                        btn.textContent = '▶ ' + child.node.text;
                        btn.onclick = () => this.selectChoice(child.idx);
                        choicesDiv.appendChild(btn);
                    }});

                    box.appendChild(choicesDiv);
                }} else if (this.canContinue()) {{
                    const choicesDiv = document.createElement('div');
                    choicesDiv.className = 'choices';
                    const btn = document.createElement('button');
                    btn.className = 'btn';
                    btn.textContent = '▶ PROSSIMA AZIONE';
                    btn.onclick = () => this.nextAction();
                    choicesDiv.appendChild(btn);
                    box.appendChild(choicesDiv);
                }} else if (this.isEnded()) {{
                    const ending = document.createElement('div');
                    ending.className = 'ending';
                    ending.innerHTML = `
                        <h2>⚡ MISSIONE COMPLETATA ⚡</h2>
                        <p>Hai concluso la tua storia a New Eden City.</p>
                        <button class="restart" onclick="location.reload()">RIAVVIA</button>
                    `;
                    box.appendChild(ending);
                }}

                // Metadata
                const meta = document.createElement('div');
                meta.className = 'meta';
                meta.textContent = `ID: ${{currentNode.id}} | Profondità: ${{currentNode.depth}} | Tipo: ${{currentNode.type}}`;
                box.appendChild(meta);

                gameDiv.appendChild(box);
            }}
        }}

        // Avvia il gioco
        const game = new Game();
    </script>
</body>
</html>
"""
    return html


def main():
    import sys

    # File di input/output
    json_file = sys.argv[1] if len(sys.argv) > 1 else "story_graph_interactive.json"
    html_file = sys.argv[2] if len(sys.argv) > 2 else "game.html"

    print("📖 Caricamento storia...")
    story = load_story_json(json_file)

    print("🎨 Generazione HTML...")
    html = build_html_game(story)

    print(f"💾 Salvataggio in {html_file}...")
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Fatto! Apri {html_file} nel browser")


if __name__ == "__main__":
    main()