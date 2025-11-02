(define (problem quest-easy) ; defines a problem named 'quest-easy'
(:domain keys-doors-simple) ; specifies the domain of this problem as 'keys-doors-simple'
(:objects ; declares objects in the problem
  room1 room2 - location ; two locations: room1 and room2
  hero - agent ; the protagonist (hero)
  silver_key - key ; a key to unlock doors
  main_door - door ; the main door that needs unlocking
)
(:init ; initial state of the problem
  (at hero room1) ; the hero starts in room1
  (key-at silver_key room1) ; the silver key is located in room1
  (door-between main_door room1 room2) ; the main door connects room1 and room2
  (locked main_door) ; the main door is initially locked
  (unlocks silver_key main_door) ; the silver key can unlock the main door
)
(:goal ; goal state of the problem
  (at hero room2) ; the hero's goal is to be in room2
)