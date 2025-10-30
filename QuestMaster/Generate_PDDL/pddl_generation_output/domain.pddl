(define (domain detective-world)
  (:requirements :strips :typing)
  (:types
    robot vehicle - mobile
    location place - object
    transportable-object
  )
  (:constants
    nova - robot
    new-eden-city-center - location
  )
  (:predicates
    (at ?r - robot ?l - location)
    (connected ?l1 - location ?l2 - location)
    (clean ?l - location)
    (holding ?r - robot ?o - transportable-object)
  )
  (:action move
    :parameters (?r - robot ?f - location ?t - location)
    :precondition (and
      (at ?r ?f)
      (connected ?f ?t)
    )
    :effect (and
      (not (at ?r ?f))
      (at ?r ?t)
    )
  )
  (:action clean-room
    :parameters (?r - robot ?s - location)
    :precondition (and
      (at ?r ?s)
      (not (clean ?s))
    )
    :effect (and
      (clean ?s)
    )
  )
)