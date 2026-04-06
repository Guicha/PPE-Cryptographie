# PPE-Cryptographie
Repo du PPE

## ECDSA - Labo attaques

- Fichier: `ecdsa.py`
- But: demonstration des 3 attaques (nonce reuse, SPA simule, omission de bornes)
- Execution: `.venv\Scripts\python.exe ecdsa.py`

## ECDSA - Version durcie

- Fichier: `ecdsa_hardened.py`
- But: correction des 3 attaques avec nonce RFC6979, flux ladder/blinding, verification stricte
- Execution: `.venv\Scripts\python.exe ecdsa_hardened.py`

## Rapports

- Attaques: `RAPPORT_ATTAQUES_ECDSA.md`
- Ameliorations: `RAPPORT_AMELIORATIONS_ECDSA.md`

## Comparaison run classique vs ameliore

- Script: `compare_ecdsa_runs.py`
- Sortie: `compare_ecdsa_runs.txt`
- Execution: `.venv\Scripts\python.exe compare_ecdsa_runs.py`
