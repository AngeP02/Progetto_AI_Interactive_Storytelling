import re
import json
from pathlib import Path
from dataclasses import dataclass, field


# ============================================================
#        PARSING LORE / PDDL / SAS
# ============================================================

@dataclass
class LoreData:
    title: str
    branching: int
    depth: int
    intro: str


def parse_lore(text: str) -> LoreData:
    title = "Untitled Story"
    branching = 3
    depth = 4
    intro = ""

    # titolo = prima riga con testo
    title_match = re.search(r"#\s*(.*)", text)
    if title_match:
        title = title_match.group(1).strip()

    # branching
    b_match = re.search(r"[Bb]ranch(?:ing)?\s*[:=]\s*(\d+)", text)
    if b_match:
        branching = int(b_match.group(1))

    # profondità
    d_match = re.search(r"[Dd]epth\s*[:=]\s*(\d+)", text)
    if d_match:
        depth = int(d_match.group(1))

    # intro = primo blocco dopo ---
    intro_match = re.split(r"---", text)
    if len(intro_match) > 1:
        intro = intro_match[1].strip()

    return LoreData(title=title, branching=branching, depth=depth, intro=intro)


@dataclass
class PDDLAction:
    name: str
    params: list
    preconditions: list
    effects: list


def parse_pddl_actions(domain_text: str) -> dict:
    actions = {}

    blocks = re.findall(r"\(:action(.*?)\)\s*\)", domain_text, flags=re.DOTALL)
    for block in blocks:
        name_match = re.search(r":action\s+(\S+)", block)
        if not name_match:
            continue
        name = name_match.group(1)

        params = re.findall(r"\?(\w+)", block)
        preconds = re.findall(r"\(.*?\)", re.search(r":precondition(.*?):effect", block, flags=re.DOTALL).group(1))
        effects = re.findall(r"\(.*?\)", re.search(r":effect(.*)", block, flags=re.DOTALL).group(1))

        actions[name] = PDDLAction(name, params, preconds, effects)

    return actions


def parse_sas_plan(sas_text: str) -> list:
    lines = sas_text.splitlines()
    plan = []
    for line in lines:
        if line.startswith("(") and line.endswith(")"):
            act = line[1:-1]
            plan.append(act)
    return plan


# ============================================================
#                 GRAFO LOGICO DETERMINISTICO
# ============================================================

@dataclass
class StoryNode:
    id: str
    text: str
    children: list = field(default_factory=list)


class LogicalStoryGraph:
    def __init__(self, branching: int, depth: int, lore: LoreData, plan: list):
        self.branching = branching
        self.depth = depth
        self.lore = lore
        self.plan = plan
        self.root = StoryNode("1", lore.intro)

    def generate(self):
        self._expand_node(self.root, level=1)
        return self.root

    def _expand_node(self, node: StoryNode, level: int):
        if level > self.depth:
            return

        # deterministico: ogni livello segue una parte del piano (se esiste)
        action_text = ""
        if level - 1 < len(self.plan):
            action_text = f"Azione pianificata: {self.plan[level-1]}"
        else:
            action_text = "Azione di riempimento: nessuna nel piano."

        for i in range(1, self.branching + 1):
            child_id = f"{node.id}.{i}"
            text = f"{action_text} → Scelta {i} al livello {level}"
            child = StoryNode(child_id, text)
            node.children.append(child)
            self._expand_node(child, level + 1)


# ============================================================
#                        HTML EXPORT
# ============================================================

def node_to_html(node: StoryNode) -> str:
    html = f"<li><b>{node.id}</b> – {node.text}"
    if node.children:
        html += "<ul>"
        for c in node.children:
            html += node_to_html(c)
        html += "</ul>"
    html += "</li>"
    return html


def export_html(root: StoryNode, title: str) -> str:
    return f"""
<html>
<head>
<meta charset="UTF-8"/>
<title>{title}</title>
<style>
body {{ font-family: Arial; padding: 20px; }}
ul {{ list-style-type: none; }}
b {{ color: #c00; }}
</style>
</head>
<body>
<h1>{title}</h1>
<ul>
{node_to_html(root)}
</ul>
</body>
</html>
"""


# ============================================================
#                    USO FINALE DEL SISTEMA
# ============================================================

def generate_story_graph(lore_text, domain_text, problem_text, sas_text):
    lore = parse_lore(lore_text)
    actions = parse_pddl_actions(domain_text)
    plan = parse_sas_plan(sas_text)

    graph = LogicalStoryGraph(lore.branching, lore.depth, lore, plan)
    root = graph.generate()
    html = export_html(root, lore.title)

    return root, html


# ============================================================
#                      ESEMPIO D’USO
# ============================================================

if __name__ == "__main__":
    lore = Path("lore.md").read_text(encoding="utf-8")
    domain = Path("domain.pddl").read_text(encoding="utf-8")
    problem = Path("problem.pddl").read_text(encoding="utf-8")
    sas = Path("sas_plan").read_text(encoding="utf-8")

    root, html = generate_story_graph(lore, domain, problem, sas)
    Path("story_graph.html").write_text(html, encoding="utf-8")
    print("HTML generato: story_graph.html")
