(define (problem delivery-easy)
  (:domain logistics-simple)
  (:objects
    warehouse shop home - location
    truck - vehicle
    parcel - package
  )
  (:init
    (at-vehicle truck warehouse)
    (at-package parcel warehouse)

    (connected warehouse shop)
    (connected shop warehouse)
    (connected shop home)
    (connected home shop)
  )
  (:goal
    (at-package parcel home)
  )
)