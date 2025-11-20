#!/usr/bin/env python3
# story_graph_generator.py
"""
Generatore semplice e corretto di grafo narrativo che:
- interpreta domain.pddl (azioni: params, precond, effect)
- interpreta problem.pddl (oggetti, init)
- interpreta sas_plan (azioni ground)
- simula stati applicando il piano e rileva azioni applicabili ad ogni stato
- esporta story_graph.json + story_game.html (interfaccia minima)

Limitazioni: parser minimale, pensato per PDDL nello stile mostrato dall'utente.
"""

import re
import json
import os
from copy import deepcopy
from typing import List, Dict, Tuple, Set

# -------------------------
# Parser PDDL minimale
# -------------------------
def extract_section(pattern: str, text: str, flags=0) -> List[str]:
    return re.findall(pattern, text, flags | re.S)

def parse_domain(domain_text: str) -> Dict:
    """
    Estrae azioni con parametri, precondizioni ed effetti.
    Ritorna dict: { action_name: { 'params': [...], 'pre': [...], 'eff': [...] } }
    """
    actions = {}
    # regex per catturare blocchi :action ... :parameters (...) :precondition (...) :effect (...)
    action_blocks = re.findall(r'\(:action\s+([^\s]+)(.*?)\)\s*\)', domain_text, re.S)
    if not action_blocks:
        # fallback: cerca singoli blocchi più semplici
        action_blocks = re.findall(r'\(:action\s+([^\s]+)(.*?)\)', domain_text, re.S)

    for name, body in action_blocks:
        # params
        params_m = re.search(r':parameters\s*\((.*?)\)', body, re.S)
        params = []
        if params_m:
            # splits like "?v - vehicle ?from - location"
            raw = params_m.group(1).strip()
            toks = raw.split()
            # create ordered parameter list like ['?v','?from','?to']
            params = [t for t in toks if t.startswith('?')]

        # precondition
        pre_m = re.search(r':precondition\s*\((.*?)\)\s*(?::|$)', body, re.S)
        preconds = []
        if pre_m:
            p = pre_m.group(1).strip()
            # rimuove leading "and"
            p = re.sub(r'^\s*and\s*', '', p, flags=re.I).strip()
            preconds = split_predicate_list(p)

        # effect
        eff_m = re.search(r':effect\s*\((.*?)\)\s*(?::|$)', body, re.S)
        effects = []
        if eff_m:
            e = eff_m.group(1).strip()
            e = re.sub(r'^\s*and\s*', '', e, flags=re.I).strip()
            effects = split_predicate_list(e)

        actions[name.lower()] = {
            'name': name.lower(),
            'params': params,
            'pre': preconds,
            'eff': effects
        }

    return {
        'actions': actions
    }

def split_predicate_list(block: str) -> List[str]:
    """
    Divide un blocco di precondition/effect in singole predicate strings.
    Semplice: cerca porzioni tra parentesi ( ), o tokens negati (not (...))
    """
    preds = []
    # cerca (not (...)) oppure (...) top-level
    # rimuovi eventuali and annidati
    block = block.strip()
    # find all occurrences of (not (pred ...)) or (pred ...)
    for m in re.finditer(r'\(not\s*\(([^()]+)\)\)|\(([^\(\)]+)\)', block):
        if m.group(1):
            preds.append('(not (' + m.group(1).strip() + '))')
        elif m.group(2):
            preds.append('(' + m.group(2).strip() + ')')
    # fallback: se nulla trovato, tenta split per newline
    if not preds:
        lines = [l.strip() for l in re.split(r'[\n;]+', block) if l.strip()]
        preds = lines
    return [p.strip() for p in preds]

def parse_problem(problem_text: str) -> Dict:
    """
    Estrae objects, init predicates, goal (opzionale).
    Oggetti: ritorna dict name->type (se available)
    init: lista di predicate strings come '(at-vehicle truck warehouse)'
    """
    objects = {}
    objs_m = re.search(r'\(:objects(.*?)\)', problem_text, re.S)
    if objs_m:
        raw = objs_m.group(1).strip()
        # simple parse: groups separated by '-' indicate types
        # example: "warehouse depot shop home - location\n truck - vehicle\n package1 package2 - package"
        for line in re.split(r'\n', raw):
            line = line.strip()
            if not line: 
                continue
            if '-' in line:
                left, typ = line.rsplit('-', 1)
                typ = typ.strip()
                for name in left.strip().split():
                    objects[name.strip()] = typ
            else:
                for name in line.split():
                    objects[name.strip()] = None

    # init
    init_m = re.search(r'\(:init(.*?)\)', problem_text, re.S)
    init_preds = []
    if init_m:
        block = init_m.group(1)
        init_preds = [p.strip() for p in re.findall(r'\([^\)]+\)', block)]

    # goal (not strictly needed for generator but parse it)
    goal = None
    goal_m = re.search(r'\(:goal\s*\((.*?)\)\s*\)', problem_text, re.S)
    if goal_m:
        goal_block = goal_m.group(1)
        goal = [p.strip() for p in re.findall(r'\([^\)]+\)', goal_block)]

    return {
        'objects': objects,
        'init': init_preds,
        'goal': goal
    }

# -------------------------
# Utils: predicate parsing and grounding
# -------------------------
def parse_predicate(pred_str: str) -> Tuple[str, Tuple[str, ...], bool]:
    """
    Input e.g. "(at-vehicle truck warehouse)" or "(not (in-vehicle p v))"
    Returns: (name, args_tuple, is_negative)
    """
    s = pred_str.strip()
    if s.startswith('(not'):
        inner = re.search(r'\(not\s*\((.*)\)\)', s, re.S).group(1).strip()
        parts = inner.split()
        return parts[0], tuple(parts[1:]), True
    else:
        inner = re.sub(r'^\(|\)$', '', s).strip()
        parts = inner.split()
        return parts[0], tuple(parts[1:]), False

def pred_to_key(name: str, args: Tuple[str, ...]) -> str:
    return f"{name} " + " ".join(args)

def state_from_init(init_preds: List[str]) -> Set[str]:
    """
    Ritorna set di predicate keys (solo positive).
    """
    s = set()
    for p in init_preds:
        name, args, neg = parse_predicate(p)
        if not neg:
            s.add(pred_to_key(name, args))
    return s

# -------------------------
# Applicabilità e applicazione azione ground
# -------------------------
def ground_action_schema(schema: Dict, args: List[str]) -> Dict:
    """
    Dato schema con params e pre/effects, e lista di actual args (names),
    crea versione groundata con pre/effects sostituite.
    schema['params'] è come ['?p','?v','?l']
    args corrisponde in ordine.
    Ritorna dict con 'pre' and 'eff' as lists of predicate keys and flags for negatives.
    """
    mapping = {}
    for p, a in zip(schema['params'], args):
        mapping[p] = a

    def substitute(pred_str):
        # prendiamo qualcosa come "(at-package ?p ?l)" o "(not (in-vehicle ?p ?v))"
        if pred_str.startswith('(not'):
            inner = re.search(r'\(not\s*\((.*)\)\)', pred_str, re.S).group(1).strip()
            parts = inner.split()
            name = parts[0]
            args_ = tuple(mapping.get(tok, tok) for tok in parts[1:])
            return ('not', pred_to_key(name, args_))
        else:
            inner = re.sub(r'^\(|\)$', '', pred_str).strip()
            parts = inner.split()
            name = parts[0]
            args_ = tuple(mapping.get(tok, tok) for tok in parts[1:])
            return ('pos', pred_to_key(name, args_))

    pre = [substitute(p) for p in schema['pre']]
    eff = [substitute(e) for e in schema['eff']]
    return {'pre': pre, 'eff': eff, 'name': schema['name'], 'args': args}

def is_applicable(grounded_action: Dict, state: Set[str]) -> bool:
    for kind, pk in grounded_action['pre']:
        if kind == 'pos':
            if pk not in state:
                return False
        elif kind == 'not':
            # precondition (not ...) means the atom must NOT be in state
            if pk in state:
                return False
    return True

def apply_action(grounded_action: Dict, state: Set[str]) -> Set[str]:
    new_state = set(state)
    for kind, pk in grounded_action['eff']:
        if kind == 'pos':
            new_state.add(pk)
        elif kind == 'not':
            if pk in new_state:
                new_state.remove(pk)
    return new_state

# -------------------------
# SAS plan parsing (reuse user's style)
# -------------------------
def parse_sas_plan(plan_text: str) -> List[Tuple[str, List[str]]]:
    actions = []
    for line in plan_text.splitlines():
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        if line.startswith('(') and line.endswith(')'):
            inner = line[1:-1].strip()
            parts = inner.split()
            name = parts[0].lower()
            args = parts[1:]
            actions.append((name, args))
    return actions

# -------------------------
# Scene text generation (semplice, usa lore snippet)
# -------------------------
def generate_scene_text(lore: str, state: Set[str], node_id: str) -> str:
    # usiamo il primo paragrafo del lore come contesto
    first_para = lore.strip().split('\n\n')[0].replace('\n', ' ').strip()
    # sintetizza lo stato in poche parole (max 6 fatti)
    facts = list(state)[:6]
    facts_str = "; ".join(facts) if facts else "nessun fatto rilevante"
    text = f"{first_para} [Stato {node_id}: {facts_str}]"
    return text

# -------------------------
# Costruzione grafo basato su piano + azioni applicabili
# -------------------------
def build_story_graph(domain: Dict, problem: Dict, plan: List[Tuple[str, List[str]]],
                      lore: str, depth_limit=5, branching_limit=4) -> Dict:
    actions_schema = domain['actions']
    initial_state = state_from_init(problem['init'])
    nodes = []
    edges = []

    # Node 0: stato iniziale
    state = initial_state
    node_map = {}  # state_key -> node_id for reuse if repeated states happen
    def state_key(s: Set[str]) -> str:
        return "|".join(sorted(s))

    node_counter = 0
    def add_node(s: Set[str], note=""):
        nonlocal node_counter
        key = state_key(s)
        if key in node_map:
            return node_map[key]
        node_id = f"N{node_counter}"
        node_counter += 1
        node_map[key] = node_id
        nodes.append({
            'id': node_id,
            'state': sorted(list(s)),
            'text': generate_scene_text(lore, s, node_id),
            'note': note,
            'choices': []  # to be filled
        })
        return node_id

    # create nodes sequentially following the plan, but also record applicable actions at each state
    seq_nodes = []
    current_state = deepcopy(state)
    start_node = add_node(current_state, note="start")
    seq_nodes.append(start_node)

    # before applying each plan action, compute applicable grounded actions (all possible groundings from objects)
    all_objects = list(problem['objects'].keys())
    object_types = problem['objects']  # not used for typing in minimal version

    # helper to generate all groundings for an action schema
    def ground_all_for_schema(schema):
        # produce combinations of objects of the same arity blindly (cartesian product)
        # For simplicity we allow any object for any param (type-check omitted)
        from itertools import product
        slots = len(schema['params'])
        if slots == 0:
            return [[]]
        combos = list(product(all_objects, repeat=slots))
        return [list(c) for c in combos]

    # For each state before executing plan action:
    pre_states = [deepcopy(current_state)]
    for step_idx, (act_name, act_args) in enumerate(plan):
        # compute applicable actions in current_state
        applicable = []
        for schema_name, schema in actions_schema.items():
            # ground all combos but limit to keep branching small
            for grounding in ground_all_for_schema(schema)[:200]:
                grounded = ground_action_schema(schema, grounding)
                if is_applicable(grounded, current_state):
                    applicable.append({
                        'action': schema_name,
                        'args': grounding,
                        'grounded': grounded
                    })
        # keep unique by action+args
        unique = {}
        for a in applicable:
            key = a['action'] + " " + " ".join(a['args'])
            unique[key] = a
        applicable = list(unique.values())

        # limit branching
        applicable = sorted(applicable, key=lambda x: x['action'])[:branching_limit]

        # add choices to current node
        cur_node_id = add_node(current_state, note=f"before_plan_step_{step_idx+1}")
        # mark plan's action among choices (if present)
        plan_key = act_name + " " + " ".join(act_args)
        choice_list = []
        for a in applicable:
            is_plan = (a['action'] == act_name and a['args'] == act_args)
            # simulate resulting state when applying this choice
            next_state = apply_action(a['grounded'], current_state) if is_applicable(a['grounded'], current_state) else None
            next_node_id = add_node(next_state, note=f"result_of_{a['action']}" ) if next_state is not None else None

            choice_item = {
                'label': f"{a['action']} {' '.join(a['args'])}",
                'action': a['action'],
                'args': a['args'],
                'is_plan_action': is_plan,
                'next_node': next_node_id
            }
            choice_list.append(choice_item)

        # also ensure the exact plan action appears (if not in applicable due to our grounding limits)
        if not any(c['is_plan_action'] for c in choice_list):
            # try to find a grounding exactly equal to plan action
            if act_name in actions_schema:
                schema = actions_schema[act_name]
                grounded_plan = ground_action_schema(schema, act_args)
                if is_applicable(grounded_plan, current_state):
                    next_state = apply_action(grounded_plan, current_state)
                    next_node_id = add_node(next_state, note=f"plan_result_step_{step_idx+1}")
                    choice_list.insert(0, {
                        'label': f"{act_name} {' '.join(act_args)}",
                        'action': act_name,
                        'args': act_args,
                        'is_plan_action': True,
                        'next_node': next_node_id
                    })

        # attach choice_list to node entry
        # find node in nodes list and update choices
        for n in nodes:
            if n['id'] == cur_node_id:
                n['choices'] = choice_list
                break

        # apply the actual plan action to advance the sequential simulation if it's applicable
        if act_name in actions_schema:
            schema = actions_schema[act_name]
            grounded_plan = ground_action_schema(schema, act_args)
            if is_applicable(grounded_plan, current_state):
                current_state = apply_action(grounded_plan, current_state)
                next_node = add_node(current_state, note=f"after_plan_step_{step_idx+1}")
                seq_nodes.append(next_node)
            else:
                # plan action not applicable (shouldn't happen if sas_plan valid) -> keep state unchanged and note error
                next_node = add_node(current_state, note=f"plan_failed_step_{step_idx+1}")
                seq_nodes.append(next_node)
        else:
            next_node = add_node(current_state, note=f"plan_unknown_action_{step_idx+1}")
            seq_nodes.append(next_node)

        pre_states.append(deepcopy(current_state))

    # finalize: build graph dict
    graph = {
        'metadata': {
            'num_nodes': len(nodes),
            'plan_length': len(plan),
            'depth_limit': depth_limit,
            'branching_limit': branching_limit
        },
        'nodes': nodes,
        'start_node': start_node,
        'plan_sequence_nodes': seq_nodes
    }
    return graph

# -------------------------
# HTML generator (molto semplice)
# -------------------------
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Story Game - Interactive Viewer</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; margin: 24px; background:#111; color:#eee; }
    .card { background:#1b1b1b; padding:20px; border-radius:8px; box-shadow:0 4px 14px rgba(0,0,0,.6); max-width:900px; margin-bottom:16px }
    .choices { margin-top:12px; }
    button.choice { display:block; margin:6px 0; padding:10px; border-radius:6px; border:1px solid #333; background:#222; color:#fff; cursor:pointer; text-align:left; }
    button.choice:hover { background:#2b2b2b; }
    .meta { color:#9aa; font-size:0.9em }
  </style>
</head>
<body>
  <div id="app">
    <h1>Story Game - Interactive Viewer</h1>
    <div id="node" class="card"></div>
    <div id="breadcrumbs" class="meta"></div>
  </div>

<script>
let graph = null;
let nodeIndex = {};
let breadcrumbs = [];

function loadGraph(g) {
  graph = g;
  nodeIndex = {};
  for (const n of g.nodes) nodeIndex[n.id] = n;
  showNode(g.start_node);
}

function showNode(nodeId) {
  const node = nodeIndex[nodeId];
  if (!node) {
    document.getElementById('node').innerHTML = '<b>Node not found</b>';
    return;
  }
  // update breadcrumbs
  breadcrumbs.push(nodeId);
  if (breadcrumbs.length>10) breadcrumbs.shift();
  document.getElementById('breadcrumbs').innerText = 'Path: ' + breadcrumbs.join(' → ');

  let html = '<h2>' + node.id + '</h2>';
  html += '<div class="meta">Note: ' + (node.note || '') + '</div>';
  html += '<p>' + escapeHtml(node.text) + '</p>';
  html += '<div class="meta">Stato attuale: <ul>';
  for (const f of node.state) html += '<li>' + escapeHtml(f) + '</li>';
  html += '</ul></div>';

  if (node.choices && node.choices.length>0) {
    html += '<div class="choices"><h3>Scelte:</h3>';
    for (const c of node.choices) {
      const label = c.label + (c.is_plan_action ? ' (Azione del piano)' : '');
      const nid = c.next_node;
      html += '<button class="choice" onclick="handleChoice(\'' + (nid || '') + '\')">' + escapeHtml(label) + '</button>';
    }
    html += '</div>';
  } else {
    html += '<div class="meta">Nessuna scelta disponibile.</div>';
  }
  document.getElementById('node').innerHTML = html;
}

function handleChoice(nextNodeId) {
  if (!nextNodeId) {
    alert('Questa scelta non porta a uno stato simulato.');
    return;
  }
  showNode(nextNodeId);
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// loader: carica story_graph.json nello stesso folder
fetch('story_graph.json')
  .then(r => r.json())
  .then(g => loadGraph(g))
  .catch(err => {
    document.getElementById('node').innerHTML = '<b>Errore caricamento story_graph.json</b><pre>' + err + '</pre>';
  });

</script>
</body>
</html>
"""

# -------------------------
# Main
# -------------------------
def main(domain_file, problem_file, plan_file, lore_file, output_dir):
    with open(domain_file, 'r', encoding='utf-8') as f:
        domain_text = f.read()
    with open(problem_file, 'r', encoding='utf-8') as f:
        problem_text = f.read()
    with open(plan_file, 'r', encoding='utf-8') as f:
        plan_text = f.read()
    with open(lore_file, 'r', encoding='utf-8') as f:
        lore_text = f.read()

    domain = parse_domain(domain_text)
    problem = parse_problem(problem_text)
    plan = parse_sas_plan(plan_text)

    # bounds from lore - attempt to find branching/depth
    depth_match = re.search(r'Depth Constraints.*?(\d+)-(\d+)', lore_text, re.S|re.I)
    branching_match = re.search(r'Branching Factor.*?(\d+)-(\d+)', lore_text, re.S|re.I)
    depth_limit = 4
    branching_limit = 4
    try:
        if depth_match:
            a,b = int(depth_match.group(1)), int(depth_match.group(2))
            depth_limit = (a+b)//2
    except:
        depth_limit = 4
    try:
        if branching_match:
            a,b = int(branching_match.group(1)), int(branching_match.group(2))
            branching_limit = max(2, (a+b)//2)
    except:
        branching_limit = 4

    graph = build_story_graph(domain, problem, plan, lore_text, depth_limit, branching_limit)

    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, 'story_graph.json')
    html_path = os.path.join(output_dir, 'story_game.html')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE)

    print(f"Generati:\n - {json_path}\n - {html_path}")
    print("Apri story_game.html in un browser (stesso folder contiene story_graph.json)")

if __name__ == "__main__":
    # esempio: modifica i paths qui se vuoi
    BASE_PATH = r"C:\Users\ANGELICA\Desktop\ANGELICA\UNICAL\MAGISTRALE\I ANNO\SECONDO SEMESTRE\INTELLIGENZA ARTIFICIALE\PROGETTO\CODICE\QuestMaster"

    domain_file = os.path.join(BASE_PATH, 'ChatBot/pddl_output/domain.pddl')
    problem_file = os.path.join(BASE_PATH, 'ChatBot/pddl_output/problem.pddl')
    plan_file = os.path.join(BASE_PATH, 'ChatBot/pddl_output/sas_plan')
    lore_file = os.path.join(BASE_PATH, 'Lore/Generated_Lore/Lore.md')
    out_dir = os.path.join(BASE_PATH, 'Game/output_game')

    main(domain_file, problem_file, plan_file, lore_file, out_dir)
