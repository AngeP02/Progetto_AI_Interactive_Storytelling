```lisp
(define (domain logistics-simple) ; Define the domain named logistics-simple
  (:requirements :strips :typing) ; Specify requirements: STRIPS and typing
  (:types location vehicle package) ; Declare types: location, vehicle, package
  (:predicates ; Start predicate declarations
    (at-vehicle ?v - vehicle ?l - location) ; Vehicle ?v is at location ?l
    (at-package ?p - package ?l - location) ; Package ?p is at location ?l
    (in-vehicle ?p - package ?v - vehicle) ; Package ?p is in vehicle ?v
    (connected ?from ?to - location) ; Location ?from is connected to location ?to
  ) ; End of predicate declarations

  (:action move ; Define the move action
   :parameters (?v - vehicle ?from ?to - location) ; Parameters: vehicle and locations
   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to)) ; Preconditions: vehicle at ?from and locations connected
   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to)) ; Effects: vehicle no longer at ?from and now at ?to
  )

  (:action load ; Define the load action
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: package, vehicle, and location
   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l)) ; Preconditions: package and vehicle at the same location
   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v)) ; Effects: package no longer at location and now in vehicle
  )

  (:action unload ; Define the unload action
   :parameters (?p - package ?v - vehicle ?l - location) ; Parameters: package, vehicle, and location
   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l)) ; Preconditions: package in vehicle and vehicle at location
   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l)) ; Effects: package no longer in vehicle and now at location
  )
)
```