# ETL-opgave: Webshop

  
## Kontekst

  
Kursisten arbejder som Data Engineer for en webshop, der sælger elektronik. Webshoppen vil bruge sine salgsdata til at arbejde med mere personlig markedsføring og til at undersøge sit sortiment og sine priser. Marketing- og salgskonsulenterne skal derfor kunne bruge relevante kunde-, ordre- og produktdata.

  
Webshoppens interne PostgreSQL-database indeholder kunde- og ordredata samt begrænsede produktoplysninger (kategori, producent og modelnavn). Produktdatabasen med specifikationer er en separat kilde. Opgaven er at hente, sammenstille og klargøre data fra kilderne og gøre de relevante produktdata tilgængelige via en API. Kundedata skal anonymiseres, før den deles med konsulenterne.

  

## Læringsmål

  
Efter opgaven skal kursisten kunne:

- Forklare og anvende ETL-processens trin: udtræk af data fra flere kilder, transformation og validering samt indlæsning til en database.

- Sammenstille produktdata fra forskellige kilder og begrunde, hvordan produkter matches, når oplysningerne ikke er identiske eller komplette.

- Arbejde med datakvalitet, herunder håndtering af manglende, ugyldige, dublerede og inkonsistente værdier.

- Beskrive, hvorfor personoplysninger skal anonymiseres, og kontrollere, at kundedata ikke kan føres tilbage til enkeltpersoner i de delte data.

- Designe en pipeline, der håndterer fejl i data og eksterne tjenester på en kontrolleret måde, og som kan genkøres uden utilsigtede dubletter.

- Bruge logs og test til at undersøge pipelineforløb, opdage fejl og kontrollere resultatet.


## Data


Produktdataene i CSV-filerne stammer fra disse Kaggle-datasæt:

- [Laptop Specification Dataset](https://www.kaggle.com/datasets/durgeshrao9993/laptop-specification-dataset)

- [Smartphone Specifications Dataset](https://www.kaggle.com/datasets/shraddha4ever20/smartphone-specifications-dataset)

- [Tablet Dataset 2024](https://www.kaggle.com/datasets/siddiquifaiznaeem/tablet-dataset-2024)
  
Kunde- og ordredata genereres syntetisk med Faker og Pandas. De syntetiske data kan blandt andet indeholde genkøb, adresseændringer og prisændringer. De indeholder ikke i udgangspunktet særlige købsmønstre, såsom at bestemte aldersgrupper køber oftere, eller at prisfald påvirker salget.


## Applikationer og konfiguration


### ETL-pipeline

ETL-koden ligger i [data_processing_pipeline/](./data_processing_pipeline/). Pipelinen henter produktdata fra CSV-filerne i [data/](./data/), genererer syntetiske kunde- og ordredata og indlæser data i projektets databaser.

Indstillinger for datagenerering findes i [data_processing_pipeline/config.yml](./data_processing_pipeline/config.yml):

- `orders.historical.days` og `orders.historical.orders_per_day` bestemmer mængden af historiske ordrer, der genereres ved første indlæsning.

- `orders.continuous.interval_seconds` og `orders.continuous.orders_per_interval` bestemmer, hvor ofte nye ordrer genereres, og hvor mange der genereres pr. interval.

- `orders.repeat_customer_probability` styrer sandsynligheden for, at en ordre kommer fra en eksisterende kunde.

- Værdierne under `generation` styrer blandt andet sandsynligheden for adresse- og prisændringer samt antal ordrelinjer og produktmængder.

Pipelinen indlæser kun historiske ordrer, hvis ordretabellen er tom, og produktdata, hvis produktdata mangler. Ændringer af historikindstillingerne har derfor ikke effekt på en database, der allerede er indlæst.


### Produkt-API

API-koden ligger i [product_api/](./product_api/). Når den normale API-service kører, er den tilgængelig på [http://localhost:8000](http://localhost:8000). API'en har også en Fault Engine, der kan simulere fejl og forsinkelser i svarene. Det gør det muligt at afprøve, hvordan en klient reagerer på ustabile kilder.



## Start-up Guide

1. Kopier ``.env.example`` til ``.env``


### ``etl_app_service``

- Start service: ``docker compose up --build etl_app``

- Stop service + dependency services: ``docker compose down``
	- Stop services og kasser volumes: ``docker compose down -v``

-  Kør tests: ``docker compose run --build --rm etl_tests``

- Ændrer run parametre i ``config.yml``


### ``api_app_service``

- Start service i ``normal`` mode: ``docker compose up --build api_app``

- Stop service + dependency services: ``docker compose down``
	- Stop services og kasser volumes: ``docker compose down -v``

 - Kør tests: ``docker compose run --build --rm api_tests

- Start service i specific Fault Mode: 
	- ``docker compose run --service-ports api_app python -m app-cli --fault-mode FAULT_MODE --flags``
	- F.eks: ``docker compose run --service-ports api_app python -m app-cli --fault-mode delay --delay-min-seconds 3 --delay-max-seconds 5``


| Mode                   | Beskrivelse                                                 | Flags                                              |
| ---------------------- | ----------------------------------------------------------- | -------------------------------------------------- |
| ``normal``             | Normal drift                                                | Ingen                                              |
| ``random``             | Anvender tilfældigt en fault i stedet for normal behandling | ``--random-fault-probability``                     |
| ``missing_values``     | Fjerner værdier fra svaret                                  | ``--missing-values-probability``                   |
| ``missing_fields``     | Fjerner felter fra svaret                                   | ``--missing-fields-probability``                   |
| ``wrong_data``         | Ændrer datatyper for værdier i svaret                       | ``--wrong-data-probability``                       |
| ``drop_records``       | Fjerner records fra svaret                                  | ``--drop-records-probability``                     |
| ``duplicate_records``  | Duplikerer records i svaret                                 | ``--duplicate-records-probability``                |
| ``empty_response``     | Returnerer et tomt svar                                     | Ingen                                              |
| ``malformed_json``     | Returnerer ugyldig JSON                                     | Ingen                                              |
| ``delay``              | Forsinker svaret                                            | ``--delay-min-seconds``<br>``--delay-max-seconds`` |
| ``service_uavailable`` | Returnerer HTTP 503                                         | ``--failure-probability``                          |
| ``rate_limit``         | Returnerer HTTP 429                                         | ``--failure-probability``                          |
| ``gateway_error``      | Returnerer HTTP 502, 503 eller 504                          | ``--failure-probability``                          |
| ``truncated_response`` | Afkorter svaret                                             | Ingen                                              |


Sandsynlighedsflag tager værdier mellem 0 og 1. Kør `docker compose run --rm api_app python -m app.cli --help` for at se alle CLI-flag og deres standardværdier.

  
## Mulige ændringer / udvidelser

- **Købsmønstre i dataen**: Hvis kursisterne skal lave data analyse eller visualiseringer som en del af opgave, kan der bages nogen købsmønstre ind i dataen.

- **API til webshoppens interne data**: Lige nu skal webshoppens data hentes direkte fra en intern Postgres database af kursisterne, da det giver mere mening ift. opgave konteksten. Hvis det er, at ønske, at de skal vende sig til at pole en API gentagne gange for real-time data, kan der bygges en API til webshoppens data. Fault Engine kan evt. genbruges.

- **Docker image deling**: Hvis kursisterne ikke skal have direkte adgang til koden burde det være muligt at dele projektet gennem Docker images istedet.

- **Produkt API deployment**: For nemhedens skyld kan kursisterne selv køre produkt API'en, men vi kan også deploye den, så de har mulighed for at bruge en API, der ikke er lokal. 