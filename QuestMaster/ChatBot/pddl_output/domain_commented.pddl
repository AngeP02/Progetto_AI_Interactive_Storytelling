```pddl
(define (domain logistics-simple) ; Define the domain called logistics-simple
  (:requirements :strips :typing) ; Specify that STRIPS and typing are required
  (:types location vehicle package) ; Declare types: location, vehicle, and package
  (:predicates ; Begin declaration of predicates
    (at-vehicle ?v - vehicle ?l - location) ; Predicate: vehicle ?v is at location ?l
    (at-package ?p - package ?l - location) ; Predicate: package ?p is at location ?l
    (in-vehicle ?p - package ?v - vehicle) ; Predicate: package ?p is in vehicle ?v
    (connected ?from ?to - location) ; Predicate: location ?from is connected to location ?to
  ) ; End of predicates declaration

  (:action move ; Begin definition of action move
   :parameters (?v - vehicle ?from ?to - location) ; Parameters: vehicle and two locations
   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to)) ; Precondition: vehicle at ?from and locations are connected
   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to)) ; Effect: vehicle is no longer at ?from, now at ?to
  ) ; End of action move

  (:action load ; Begin definition of action load
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: package, vehicle, and location
   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l)) ; Precondition: package and vehicle at the same location
   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v)) ; Effect: package is no longer at location, now in vehicle
  ) ; End of action load

  (:action unload ; Begin definition of action unload
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: package, vehicle, and location
   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l)) ; Precondition: package in vehicle, vehicle at location
   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l)) ; Effect: package is no longer in vehicle, now at location
  ) ; End of action unload
) ; End of domain definition
```