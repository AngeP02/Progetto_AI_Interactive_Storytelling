```pddl
(define (domain keys-doors-simple)
  (:requirements :strips :typing) ; Specifies the use of STRIPS and typing in the domain.
  (:types location key door agent) ; Defines the types of objects in the domain.
  (:predicates
    (at ?a - agent ?l - location) ; Predicate to check if an agent is at a specific location.
    (key-at ?k - key ?l - location) ; Predicate to check if a key is at a specific location.
    (has-key ?a - agent ?k - key) ; Predicate to check if an agent has a specific key.
    (door-between ?d - door ?l1 ?l2 - location) ; Predicate to check if a door is between two locations.
    (locked ?d - door) ; Predicate to check if a door is locked.
    (unlocks ?k - key ?d - door) ; Predicate to check if a key can unlock a specific door.
  )
  (:action move
    :parameters (?a - agent ?from ?to - location ?d - door) ; Parameters for the move action.
    :precondition (and (at ?a ?from) (door-between ?d ?from ?to) (not (locked ?d))) ; Preconditions for moving: agent at 'from' location, door between locations, door unlocked.
    :effect (and (not (at ?a ?from)) (at ?a ?to)) ; Effect of moving: agent no longer at 'from' location, now at 'to' location.
  )
  (:action pick-key
    :parameters (?a - agent ?k - key ?l - location) ; Parameters for the pick-key action.
    :precondition (and (at ?a ?l) (key-at ?k ?l)) ; Preconditions for picking a key: agent and key at the same location.
    :effect (and (not (key-at ?k ?l)) (has-key ?a ?k)) ; Effect of picking a key: key no longer at location, agent has the key.
  )
  (:action unlock
    :parameters (?a - agent ?k - key ?d - door ?l - location) ; Parameters for the unlock action.
    :precondition (and (at ?a ?l) (has-key ?a ?k) (unlocks ?k ?d) (locked ?d)) ; Preconditions for unlocking: agent at location, agent has the key, key can unlock the door, door is locked.
    :effect (not (locked ?d)) ; Effect of unlocking: door is no longer locked.
  )
)
```