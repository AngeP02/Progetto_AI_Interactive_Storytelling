```lisp
(define (domain logistics-simple) ; Define the domain named logistics-simple
  (:requirements :strips :typing) ; Specify that the domain uses STRIPS and typing
  (:types location vehicle package) ; Declare the types: location, vehicle, and package
  (:predicates ; Start defining predicates
    (at-vehicle ?v - vehicle ?l - location) ; Predicate to check if a vehicle is at a location
    (at-package ?p - package ?l - location) ; Predicate to check if a package is at a location
    (in-vehicle ?p - package ?v - vehicle) ; Predicate to check if a package is in a vehicle
    (connected ?from ?to - location) ; Predicate to check if two locations are connected
  )

  (:action move ; Define the move action
   :parameters (?v - vehicle ?from ?to - location) ; Parameters: a vehicle and two locations
   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to)) ; Preconditions: vehicle is at the starting location and locations are connected
   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to)) ; Effects: vehicle is no longer at the starting location, but at the destination
  )

  (:action load ; Define the load action
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: a package, a vehicle, and a location
   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l)) ; Preconditions: package and vehicle are at the same location
   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v)) ; Effects: package is no longer at the location, but in the vehicle
  )

  (:action unload ; Define the unload action
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: a package, a vehicle, and a location
   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l)) ; Preconditions: package is in the vehicle and vehicle is at the location
   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l)) ; Effects: package is no longer in the vehicle, but at the location
  )
)
```