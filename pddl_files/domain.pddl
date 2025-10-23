(define (domain quest-domain)

    ; Types
    (:location :types)
    (:item :types)
    (:character :types)
    (:puzzle :types)
    (:clue :types)

    ; Predicates
    (predicates
        (at-location ?loc - location)
        (has-item ?agent ?item - item)
        (door-opened ?door - door)
        (puzzle-solved ?puzzle - puzzle)
        (clue-found ?clue - clue))

    ; Actions
    (actions

        ; Move between locations
        (move-to-location
            :parameters (?agent - character ?loc1 - location ?loc2 - location)
            :preconditions (and (at-location ?agent ?loc1) (not (door-opened ?door)))
            :effects (and (not (at-location ?agent ?loc1)) (at-location ?agent ?loc2)))

        ; Pick up items
        (pick-up-item
            :parameters (?agent - character ?item1 - item)
            :preconditions (and (has-item ?agent ?other) (not (has-item ?agent ?item1)))
            :effects (and (not (has-item ?agent ?other)) (has-item ?agent ?item1)))

        ; Use items
        (use-item
            :parameters (?agent - character ?item1 - item)
            :preconditions (and (has-item ?agent ?item1) (not (puzzle-solved ?puzzle)))
            :effects (and (not (has-item ?agent ?item1)) (puzzle-solved ?puzzle)))

        ; Solve puzzles
        (solve-puzzle
            :parameters (?puzzle - puzzle)
            :preconditions (and (has-item ?agent ?clue) (not (puzzle-solved ?puzzle)))
            :effects (and (not (has-item ?agent ?clue)) (puzzle-solved ?puzzle)))

        ; Interact with characters
        (talk-to-character
            :parameters (?agent - character ?character1 - character)
            :preconditions (and (at-location ?agent ?loc) (at-location ?character1 ?loc))
            :effects (and (not (at-location ?agent ?loc)) (has-item ?agent ?clue)))

        ; Open doors
        (open-door
            :parameters (?door - door)
            :preconditions (and (at-location ?agent ?loc) (not (door-opened ?door)))
            :effects (and (not (at-location ?agent ?loc)) (door-opened ?door)))

    )

    ; Puzzles and clues
    (puzzles
        (:puzzle1 - puzzle
            :clue1 - clue
            :clues-need (?clue1)
            :solve-action (solve-puzzle ?puzzle1))

        (:puzzle2 - puzzle
            :clue2 - clue
            :clues-need (?clue2)
            :solve-action (solve-puzzle ?puzzle2))

        (:puzzle3 - puzzle
            :clue3 - clue
            :clues-need (?clue1 ?clue2)
            :solve-action (solve-puzzle ?puzzle3)))

)