```lisp
(define (problem delivery-medium) ; Definisce il problema chiamato "delivery-medium".
  (:domain logistics-simple) ; Specifica che il problema appartiene al dominio "logistics-simple".
  (:objects ; Inizia la dichiarazione degli oggetti usati nel problema.
    warehouse depot shop home - location ; Definisce i luoghi disponibili: magazzino, deposito, negozio, casa.
    truck - vehicle ; Definisce un veicolo: il camion.
    package1 package2 - package ; Definisce due pacchi: package1 e package2.
  )
  (:init ; Inizia la specifica dello stato iniziale del problema.
    (at-vehicle truck warehouse) ; Il camion si trova inizialmente al magazzino.
    (at-package package1 warehouse) ; Il pacco1 si trova inizialmente al magazzino.
    (at-package package2 depot) ; Il pacco2 si trova inizialmente al deposito.
    
    (connected warehouse depot) ; Il magazzino è connesso al deposito.
    (connected depot warehouse) ; Il deposito è connesso al magazzino.
    (connected depot shop) ; Il deposito è connesso al negozio.
    (connected shop depot) ; Il negozio è connesso al deposito.
    (connected shop home) ; Il negozio è connesso alla casa.
    (connected home shop) ; La casa è connessa al negozio.
  )
  (:goal ; Inizia la specifica delle condizioni obiettivo del problema.
    (and ; Tutte le condizioni seguenti devono essere soddisfatte.
      (at-package package1 home) ; Il pacco1 deve essere consegnato a casa.
      (at-package package2 shop) ; Il pacco2 deve essere consegnato al negozio.
    )
  )
)
```