
(define (problem lost-code-problem)
  (:domain lost-code)

  (:objects
    the lost code you megacorps initial state in uncover maximum find minimum your rival goal world background obstacles quest description branching factor echo depth constraints the corrupt context
    
    ai1 ai2
    agent1 agent2
    firewall security-system ice-wall
    lost-code
  )

  (:init
    (at ai1 alleyway)
    (rival-ai-present rival1 street)
    (rival-ai-present rival2 rooftop)
    (corporate-agent-present agent1 street)
    (corporate-agent-present agent2 lab)
    (obstacle-present firewall street)
    (obstacle-present security-system lab)
    (obstacle-present ice-wall underground)
    (safe alleyway)
    (safe street)
    (safe rooftop)
    (safe lab)
    (safe underground)
  )

  (:goal
    (and (has-code ai1) (code-found lost-code))
  )
)
