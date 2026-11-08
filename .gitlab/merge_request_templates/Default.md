## JIRA

<!-- Eén issue-key, ook in de branchnaam en in elke commit: bv. GEO-42 -->
Issue: GEO-

## Wat en waarom

<!-- Wat verandert er (1-3 zinnen) en welk probleem uit de user story lost het op? -->

## Solution outline

<!-- Link naar de solution outline uit de refinement (Confluence/JIRA-comment of docs/). -->
Link:

## Testbewijs

<!-- Plak de uitvoer van `make check` en `make test`, of link naar de Jenkins-run. -->
- Jenkins-run:
- Handmatig getest:

## Checklist (definition of done)

- [ ] Branch en commits beginnen met de JIRA-key
- [ ] `make check` (ruff) is groen
- [ ] Tests toegevoegd of aangepast; `make test` is groen
- [ ] Jenkins-pipeline is groen
- [ ] Migraties nagekeken (en terug te draaien)
- [ ] Geen geheimen of wachtwoorden in de diff
- [ ] Documentatie/README bijgewerkt waar nodig
- [ ] Reviewer toegewezen
