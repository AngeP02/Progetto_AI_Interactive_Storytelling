(define (domain grid-navigation)
  (:requirements :strips :typing)
  (:types position agent)
  (:predicates
    (at ?a - agent ?p - position)
    (adjacent ?p1 ?p2 - position)
    (clear ?p - position)
    (goal-pos ?p - position)
  )

  (:action move
   :parameters (?a - agent ?from ?to - position)
   :precondition (and (at ?a ?from) (adjacent ?from ?to) (clear ?to))
   :effect (and (not (at ?a ?from)) (not (clear ?to)) (at ?a ?to) (clear ?from))
  )

)