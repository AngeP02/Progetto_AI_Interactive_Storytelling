(define (domain logistics-simple)
                  (:requirements :strips :typing)
                  (:types location vehicle package)
                  (:predicates
                    (at-vehicle ?v - vehicle ?l - location)
                    (at-package ?p - package ?l - location)
                    (in-vehicle ?p - package ?v - vehicle)
                    (connected ?from ?to - location)
                  )
                
                  (:action move
                   :parameters (?v - vehicle ?from ?to - location)
                   :precondition (and (at-vehicle ?v ?from) (connected ?from ?to))
                   :effect (and (not (at-vehicle ?v ?from)) (at-vehicle ?v ?to))
                  )
                
                  (:action load
                   :parameters (?p - package ?v - vehicle ?l - location)
                   :precondition (and (at-package ?p ?l) (at-vehicle ?v ?l))
                   :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?v))
                  )
                
                  (:action unload
                   :parameters (?p - package ?v - vehicle ?l - location)
                   :precondition (and (in-vehicle ?p ?v) (at-vehicle ?v ?l))
                   :effect (and (not (in-vehicle ?p ?v)) (at-package ?p ?l))
                  )
                )