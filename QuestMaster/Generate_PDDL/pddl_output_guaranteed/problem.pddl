(define (problem quest-medium)
  (:domain keys-doors-simple)
  (:objects
    entrance hall treasure_room secret_chamber - location
    hero - agent
    bronze_key golden_key - key
    main_door treasure_door - door
  )
  (:init
    (at hero entrance)
    (key-at bronze_key entrance)
    (key-at golden_key hall)

    (door-between main_door entrance hall)
    (door-between treasure_door hall treasure_room)

    (locked main_door)
    (locked treasure_door)

    (unlocks bronze_key main_door)
    (unlocks golden_key treasure_door)
  )
  (:goal
    (at hero treasure_room)
  )
)