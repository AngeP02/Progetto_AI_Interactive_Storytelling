(define (problem quest-problem)
    (:domain quest-domain)

    ; Objects
    (:locations
        (:kingdom-hall :location)
        (:enchanted-forest :location)
        (:dark-castle :location)
        (:magic-lake :location)
        (:ancient-ruins :location)
        (:lost-city :location)
        (:hidden-village :location))

    (:items
        (:key-of-light :item)
        (:map-of-truth :item)
        (:scroll-of-knowledge :item)
        (:crystal-ball :item)
        (:mystery-box :item)
        (:ancient-tome :item)
        (:magical-flask :item))

    (:characters
        (:hero :character))

    (:puzzles
        (:riddle-of-lumina :puzzle)
        (:code-of-the-ancients :puzzle)
        (:test-of-magic :puzzle))

    (:clues
        (:hint-of-light :clue)
        (:map-to-the-truth :clue)
        (:key-to-knowledge :clue))

    ; Initial State
    (init
        (and
            (at-location hero kingdom-hall)
            (has-item hero key-of-light)
            (has-item hero map-of-truth)
            (not (door-opened dark-castle))
            (not (puzzle-solved riddle-of-lumina))
            (not (puzzle-solved code-of-the-ancients))
            (not (puzzle-solved test-of-magic)))

    ; Goal
    (goal
        (and
            (at-location hero lost-city)
            (puzzle-solved riddle-of-lumina)
            (puzzle-solved code-of-the-ancients)))
)
```

This PDDL problem includes 7 locations, 8 items, 3 puzzles, and 3 clues. The initial state is challenging, as the player starts in the kingdom-hall with only two items, and all doors are initially locked except for the dark-castle door. The goal requires the player to reach the lost-city location while solving two key puzzles related to "Una missione per salvare il regno".