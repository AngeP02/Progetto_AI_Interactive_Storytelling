```pddl
(define (domain keys-doors-simple)
  (:requirements :strips :typing) ; Specifies the use of STRIPS and typing features
  (:types location key door agent) ; Declares the types used in the domain
  (:predicates
    (at ?a - agent ?l - location) ; Specifies the agent's location
    (key-at ?k - key ?l - location) ; Specifies the location of a key
    (has-key ?a - agent ?k - key) ; Specifies the key possession of an agent
    (door-between ?d - door ?l1 ?l2 - location) ; Specifies the door's location between two locations
    (locked ?d - door) ; Specifies if a door is locked
    (unlocks ?k - key ?d - door) ; Specifies if a key can unlock a door
  )
  (:action move
   :parameters (?a - agent ?from ?to - location ?d - door) ; Parameters for the move action
   :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d))) ; Preconditions for moving
   :effect (and (not (at ?a ?from)) (at ?a ?to)) ; Effects of the move action
  )
  (:action pick-key
   :parameters (?a - agent ?k - key ?l - location) ; Parameters for the pick-key action
   :precondition (and (at ?a ?l) (key-at ?k ?l)) ; Preconditions for picking up a key
   :effect (and (not (key-at ?k ?l)) (has-key ?a ?k)) ; Effects of picking up a key
  )
  (:action unlock
   :parameters (?a - agent ?k - key ?d - door ?l - location) ; Parameters for the unlock action
   :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d)) ; Preconditions for unlocking a door
   :effect (not (locked ?d)) ; Effects of unlocking a door
  )
)
```