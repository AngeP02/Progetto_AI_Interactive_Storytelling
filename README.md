# QuestMaster AI

Un sistema che genera avventure narrative interattive combinando la creatività degli LLM con la precisione della pianificazione formale PDDL. Il risultato è un gioco testuale completo in un file HTML standalone, giocabile direttamente nel browser.

Progetto per il corso di **Intelligenza Artificiale**

## Il problema che risolve

Quando si chiede a un LLM di inventare un gioco narrativo con regole coerenti, prima o poi si contraddice. Dimentica oggetti già usati, apre porte che non esistevano, crea scorciatoie logiche che rompono la storia. QuestMaster separa due responsabilità:

1. **PDDL + Fast Downward** si occupa della struttura logica: stati, azioni, vincoli, goal. Se Fast Downward trova un piano, esiste almeno un percorso valido dalla situazione iniziale alla fine.
2. **GPT-4o** si occupa solo della narrazione: prende quella struttura verificata e la trasforma in un racconto.

In questo modo l'LLM non può allucinare regole di gioco perché non le decide lui.

## Come funziona

Il sistema è diviso in tre fasi sequenziali: configurazione chatbot, generazione Lore e PDDL e generazione del gioco HTML.

**Fase 0 — Chatbot di configurazione**
Un'interfaccia conversazionale raccoglie le preferenze dell'utente: genere, lunghezza, tono, tema, grafica. Si può configurare manualmente step by step o usare la modalità casuale che genera tutto in un colpo solo. Le scelte vengono trasformate in vincoli numerici concreti:

| Lunghezza | Branching factor | Depth (passi) |
|-----------|-----------------|---------------|
| Short     | 2–3 scelte/nodo | 3–6 azioni    |
| Medium    | 3–4 scelte/nodo | 7–12 azioni   |
| Long      | 4–5 scelte/nodo | 13–25 azioni  |

**Fase 1 — Generazione Lore e PDDL**
A partire dalla configurazione vengono generati due documenti complementari:

1. **Documento di Lore**, un Markdown narrativo con ambientazione, personaggi, luoghi e già integrati i vincoli di branching e depth nelle sezioni apposite.
2. **File PDDL** (domain + problem) generati con una strategia ibrida:
   
   2.1 Primo tentativo di generazione diretta da Lore con GPT-4o;
   
   2.2 Se fallisce si fa fallback su template pre-validati scelti automaticamente in base alla storia;
   
   2.3 Personalizzazione semantica;

   2.4 Validazione con Fast Downward in cui, se il planner non trova soluzione, si attiva il Reflection Agent che analizza l'errore e propone una correzione (fino a 3 tentativi)

Infine, si ha la fase di **Human in the Loop**, in cui prima di procedere l'utente può modificare la Lore, rinominare personaggi e luoghi, e il sistema riverifica la giocabilità dopo ogni modifica.

**Fase 2 — Generazione del gioco HTML**
Il modulo `QuestPlan.py` unisce Lore e PDDL in un documento guida (`quest_plan.md`) che traduce le azioni PDDL in eventi narrativi leggibili. Questo documento diventa il system prompt persistente durante la partita.
Il file HTML finale include:
1. Un motore narrativo JavaScript che interroga GPT-4o a ogni turno;
2. I vincoli MaxDepth e Branching hardcoded nel codice, estratti dal Quest Plan;
3. Una logica di pacing dinamico secondo cui negli ultimi 2 turni l'LLM viene forzato a convergere verso il finale;
4. Gestione della cronologia limitata agli ultimi 8 scambi per non sforare la finestra di contesto;
5. Export della storia come PDF a fine partita.
