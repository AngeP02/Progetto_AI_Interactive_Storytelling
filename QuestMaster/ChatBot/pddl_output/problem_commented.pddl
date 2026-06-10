```lisp
(define (problem quest-medium) ; Definisce il problema con il nome 'quest-medium'
  (:domain keys-doors-simple) ; Specifica il dominio usato: 'keys-doors-simple'
  (:objects
    ingresso_montagna_ombre sala_regia stanza_tesoro_thalorax cella_magica - location ; Definisce le locations
    eroe_prescelto - agent ; Definisce l'agente 'eroe_prescelto'
    chiave_bronzo chiave_oro - key ; Definisce le chiavi
    porta_principale_eldoria porta_tesoro - door ; Definisce le porte
  )
  (:init
    (at eroe_prescelto ingresso_montagna_ombre) ; L'eroe è inizialmente all'ingresso della montagna
    (key-at chiave_bronzo ingresso_montagna_ombre) ; La chiave di bronzo è all'ingresso della montagna
    (key-at chiave_oro sala_regia) ; La chiave d'oro è nella sala regia
    (door-between porta_principale_eldoria ingresso_montagna_ombre sala_regia) ; La porta principale collega l'ingresso e la sala regia
    (door-between porta_tesoro sala_regia stanza_tesoro_thalorax) ; La porta del tesoro collega la sala regia e la stanza del tesoro
    (locked porta_principale_eldoria) ; La porta principale è chiusa a chiave
    (locked porta_tesoro) ; La porta del tesoro è chiusa a chiave
    (unlocks chiave_bronzo porta_principale_eldoria) ; La chiave di bronzo sblocca la porta principale
    (unlocks chiave_oro porta_tesoro) ; La chiave d'oro sblocca la porta del tesoro
  )
  (:goal
    (at eroe_prescelto stanza_tesoro_thalorax) ; Obiettivo: l'eroe deve raggiungere la stanza del tesoro
  )
)
```