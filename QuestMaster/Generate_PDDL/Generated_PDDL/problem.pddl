(define (problem narrative-problem)
  (:domain narrative-domain)
  (:objects
    protagonist - character
    start forest_path dark_cave ancient_castle treasure_vault start forest_path dark_cave ancient_castle - location
    torch iron_key crystal_orb magic_sword silver_key golden_artifact - object
    locked_gate_obs cave_guardian_obs puzzle_door_obs - obstacle
  )
    (:init
    (at protagonist start)
    (visited start)
    (at-obj torch start)
    (at-obj iron_key forest_path)
    (at-obj crystal_orb dark_cave)
    (at-obj magic_sword dark_cave)
    (at-obj silver_key forest_path)
    (at-obj golden_artifact ancient_castle)
    (obstacle-active locked_gate_obs)
    (obstacle-active cave_guardian_obs)
    (obstacle-active puzzle_door_obs)
    (at protagonist start)
    (at-obj torch start)
    (locked forest_path)
    (locked dark_cave)
    (at-obj torch start)
    (key-for torch forest_path)
    (at-obj iron_key forest_path)
    (key-for iron_key dark_cave)
    (connected start forest_path)
    (connected ancient_castle dark_cave)
    (connected ancient_castle forest_path)
    (connected dark_cave ancient_castle)
    (connected forest_path start)
    (connected forest_path dark_cave)
    (connected dark_cave forest_path)
    (connected forest_path ancient_castle)
  )
  (:goal
    (and
      (at protagonist ancient_castle)
      (has protagonist torch)
    )
  )
)