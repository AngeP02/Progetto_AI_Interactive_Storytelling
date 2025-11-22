```lisp
(define (domain logistics-simple) ; Definisce un dominio chiamato "logistics-simple"
                  (:requirements :strips :typing) ; Specifica i requisiti STRIPS e il supporto per i tipi
                  (:types location vehicle package) ; Definisce i tipi di oggetti: location, vehicle, package
                  (:predicates ; Inizio della definizione dei predicati
                    (at-vehicle ?v - vehicle ?l - location) ; Predicato: un veicolo è in una determinata posizione
                    (at-package ?p - package ?l - location) ; Predicato: un pacco è in una determinata posizione
                    (in-vehicle ?p - package ?v - vehicle) ; Predicato: un pacco è all'interno di un veicolo
                    (connected ?from ?to - location) ; Predicato: due posizioni sono collegate
                  ) ; Fine della definizione dei predicati
                
                  (:action move ; Definisce l'azione "move"
                   :parameters (?v - vehicle ?from ?to - location) ; Parametri: un veicolo, posizione di partenza e arrivo
                   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to)) ; Precondizioni: il veicolo è nella posizione iniziale e le posizioni sono collegate
                   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to)) ; Effetti: il veicolo non è più nella posizione iniziale ed è nella posizione finale
                  ) ; Fine della definizione dell'azione "move"
                
                  (:action load ; Definisce l'azione "load"
                   :parameters (?p - package ?v - vehicle ?l - location) ; Parametri: un pacco, un veicolo e una posizione
                   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l)) ; Precondizioni: il pacco e il veicolo sono nella stessa posizione
                   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v)) ; Effetti: il pacco non è più nella posizione ed è nel veicolo
                  ) ; Fine della definizione dell'azione "load"
                
                  (:action unload ; Definisce l'azione "unload"
                   :parameters (?p - package ?v - vehicle ?l - location) ; Parametri: un pacco, un veicolo e una posizione
                   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l)) ; Precondizioni: il pacco è nel veicolo e il veicolo è nella posizione
                   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l)) ; Effetti: il pacco non è più nel veicolo ed è nella posizione
                  ) ; Fine della definizione dell'azione "unload"
                ) ; Fine del dominio
```