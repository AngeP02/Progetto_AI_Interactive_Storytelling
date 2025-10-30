(define (problem detective-problem)
  (:domain detective-world)
  (:objects
    nova - robot
    new-eden-city-center - location
    warehouse - location
    omicron-tower - location
  )
  (:init
    (at nova new-eden-city-center)
    (connected new-eden-city-center warehouse)
    (clean warehouse)
  )
  (:goal
    (and
      (at nova omicron-tower)
      (clean warehouse)
    )
  )
)