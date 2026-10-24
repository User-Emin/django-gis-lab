# Meewerken

## Branches
- `main` is altijd groen (tests en pre-commit). Niet direct op `main` werken, behalve de eerste opzet.
- Maak per wijziging een branch vanaf `main`: `feat/korte-naam`, `fix/korte-naam`, `docs/korte-naam`, `chore/korte-naam`.
- Open een pull request met het sjabloon; houd hem klein. Merge met squash, zodat `main` een leesbare lijst blijft.

## Conventional commits
`type(scope): omschrijving in de gebiedende wijs`, bijvoorbeeld `feat(rcs): laagnaam-whitelist uit bestand`.

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`. Een brekende wijziging markeer je met `!` (`feat!:`) of een `BREAKING CHANGE:`-regel.

## Voor je pusht
```
pre-commit run --all-files
set -a; . ./.env; set +a; uv run pytest -q
```
Commit nooit `.env`, `.run/`, databases of media. Gebruik alleen open data (zie `THIRD_PARTY.md`).

## Releases
Een les of mijlpaal krijgt een tag (`les-NN`) en een GitHub-release.

## Uitrollen (CD, les 26)

- Het image gaat alleen op `main` en op tags `les-*` naar `ghcr.io/user-emin/django-gis-lab` (PR's bouwen en testen, pushen niet). Tags: `sha-<7>`, `les-NN` (bij een tag) en `latest` (alleen main). De workflow gebruikt `GITHUB_TOKEN`; er is geen PAT.
- De job `deploy` hoort bij de environment `productie` en wacht op goedkeuring. Er is geen echte server: "uitrollen" betekent het image op digest (`@sha256:...`) pullen, `migrate` als one-shot draaien tegen een PostGIS-service, de web-container starten en `/health` controleren. Daarna volgt een rollback-oefening op de vorige digest (`scripts/ci/rooktest.sh`).
- Secrets staan nooit in image, compose of workflow: de CI genereert per run een wegwerp-`DJANGO_SECRET_KEY`. OIDC (`id-token: write`) komt pas bij een cloud-doel.
