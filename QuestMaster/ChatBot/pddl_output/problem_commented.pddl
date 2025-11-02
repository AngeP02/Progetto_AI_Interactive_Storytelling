(define (problem delivery-easy) ; defines a problem named "delivery-easy"
(:domain logistics-simple) ; specifies the domain as "logistics-simple"
(:objects ; declares objects in the domain
  warehouse shop home - location ; declares locations: warehouse, shop, and home
  truck - vehicle ; declares a vehicle (truck)
  parcel - package ; declares a package (parcel)
)
(:init ; initializes the problem with certain facts
  (at-vehicle truck warehouse) ; truck is initially at the warehouse
  (at-package parcel warehouse) ; parcel is initially at the warehouse

  (connected warehouse shop) ; warehouse and shop are connected
  (connected shop warehouse) ; shop and warehouse are connected
  (connected shop home) ; shop and home are connected
  (connected home shop) ; home and shop are connected
)
(:goal ; specifies the goal of the problem
  (at-package parcel home) ; move parcel to be at home