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
