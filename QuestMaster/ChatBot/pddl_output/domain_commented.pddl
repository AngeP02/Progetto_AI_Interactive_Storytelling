```pddl
(define (domain logistics-simple) ; Define the domain named "logistics-simple"
  (:requirements :strips :typing) ; Declare requirements: STRIPS and typing
  (:types location vehicle package) ; Define types: location, vehicle, and package
  (:predicates ; Begin list of predicates
    (at-vehicle ?v - vehicle ?l - location) ; Predicate: vehicle ?v is at location ?l
    (at-package ?p - package ?l - location) ; Predicate: package ?p is at location ?l
    (in-vehicle ?p - package ?v - vehicle) ; Predicate: package ?p is in vehicle ?v
    (connected ?from ?to - location) ; Predicate: location ?from is connected to location ?to
  )

  (:action move ; Define action "move"
   :parameters (?v - vehicle ?from ?to - location) ; Parameters: vehicle ?v, locations ?from and ?to
   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to)) ; Preconditions: vehicle ?v at ?from and ?from connected to ?to
   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to)) ; Effects: vehicle ?v not at ?from and at ?to
  )

  (:action load ; Define action "load"
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: package ?p, vehicle ?v, location ?l
   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l)) ; Preconditions: package ?p and vehicle ?v at location ?l
   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v)) ; Effects: package ?p not at ?l, in vehicle ?v
  )

  (:action unload ; Define action "unload"
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: package ?p, vehicle ?v, location ?l
   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l)) ; Preconditions: package ?p in vehicle ?v, vehicle ?v at location ?l
   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l)) ; Effects: package ?p not in vehicle ?v, at location ?l
  )
)
```