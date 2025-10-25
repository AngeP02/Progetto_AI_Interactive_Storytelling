
(define (domain lost-code)
  (:requirements :strips :typing)

  (:types location ai agent code obstacle)

  (:predicates
    (at ?a - ai ?l - location)
    (has-code ?a - ai)
    (code-found ?c - code)
    (obstacle-present ?o - obstacle ?l - location)
    (rival-ai-present ?r - ai ?l - location)
    (corporate-agent-present ?ag - agent ?l - location)
    (safe ?l - location)
  )

  ;; Azioni
  (:action move
    :parameters (?a - ai ?from - location ?to - location)
    :precondition (and (at ?a ?from) (safe ?to))
    :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action hack
    :parameters (?a - ai ?o - obstacle ?l - location)
    :precondition (and (at ?a ?l) (obstacle-present ?o ?l))
    :effect (not (obstacle-present ?o ?l))
  )

  (:action confront-rival
    :parameters (?a - ai ?r - ai ?l - location)
    :precondition (and (at ?a ?l) (rival-ai-present ?r ?l))
    :effect (not (rival-ai-present ?r ?l))
  )

  (:action evade-corporate
    :parameters (?a - ai ?ag - agent ?l - location)
    :precondition (and (at ?a ?l) (corporate-agent-present ?ag ?l))
    :effect (not (corporate-agent-present ?ag ?l))
  )

  (:action recover-code
    :parameters (?a - ai ?c - code ?l - location)
    :precondition (and (at ?a ?l) (safe ?l))
    :effect (and (has-code ?a) (code-found ?c))
  )
)
