# Rapport - Amelioration ECDSA contre 3 attaques critiques

Ce document presente la version durcie du programme ECDSA et analyse les corrections apportees contre:

1. la reutilisation du nonce,
2. les fuites de type side-channel,
3. l omission des verifications de bornes.

## Programme complet ajoute

- Fichier: `ecdsa_hardened.py`
- Execution: `.venv\Scripts\python.exe ecdsa_hardened.py`
- Sortie capturee: `ecdsa_hardened_run.txt`
- Comparaison directe runs: `compare_ecdsa_runs.py`
- Sortie comparative: `compare_ecdsa_runs.txt`

## Comparaison directe des runs (classique vs ameliore)

Cette section compare les deux implementations a partir d'une meme methode de mesure
(10 iterations de signature + verification) via `compare_ecdsa_runs.py`.

### Resultats securite observes

| Test | ECDSA classique | ECDSA ameliore |
| :-- | :-- | :-- |
| Recuperation cle privee via nonce reuse | True (attaque reussie) | False par construction (nonce RFC6979) |
| Reconstruction nonce via SPA simulee | True (attaque reussie) | Profil d'operations fixe + blinding |
| Signature forgee `(0,0)` acceptee | True (mode vulnerable) | False |

Lecture:

- Le run classique reste exploitable sur les 3 axes etudies.
- Le run ameliore bloque la forge `(0,0)` et supprime la dependance a un nonce RNG fragile.
- Sur le risque side-channel, la version amelioree reduit fortement le signal structurel (profil fixe cote algorithme).

### Resultats performance observes

Extrait de `compare_ecdsa_runs.txt`:

- Classic sign avg (s): `0.011774`
- Classic verify avg (s): `0.024121`
- Hardened sign avg (s): `0.020517`
- Hardened verify avg (s): `0.039070`
- Sign overhead hardened/classic: `1.74x`
- Verify overhead hardened/classic: `1.62x`

Interpretation:

- Le hardening augmente le cout CPU (flux ladder fixe + scalar blinding + validations supplementaires).
- Le surcout reste modere pour un gain de securite majeur sur les attaques critiques.

## Correctif 1 - Nonce deterministe RFC 6979

### Probleme corrige
Quand le nonce $k$ est mal genere (reuse, faible entropie, bug RNG), la cle privee peut etre retrouvee.

### Correction implementee
Le nonce est derive de maniere deterministe via HMAC-SHA256 (RFC 6979):

- Fonction: `deterministic_nonce_rfc6979(...)`
- Signature: `sign_message(...)` utilise uniquement ce nonce.

### Resultat observe
Dans la sortie:

- `Nonce deterministic RFC6979 stable sur meme message: True`
- `Nonce differents sur messages differents: True`

Conclusion: le risque de collision de nonce due a un RNG defectueux est fortement reduit.

## Correctif 2 - Reduction du signal side-channel

### Probleme corrige
Le schema classique Double-and-Add fuit de l information sur les bits de $k$ via un profil d operations variable.

### Correction implementee
- Multiplication scalaire en style Montgomery ladder a longueur fixe.
- Scalar blinding: utilisation de $k' = k + t*n$ avec $t$ aleatoire.

Fonction: `scalar_multiply_ladder(..., scalar_blinding=True)`.

### Analyse
Le programme compare un compteur d operations:

- Leaky (faible Hamming weight): `382`
- Leaky (forte Hamming weight): `510`
- Hardened (fixe): `816`

Conclusion: le profil operationnel devient fixe cote algorithme, ce qui diminue fortement la fuite structurale la plus evidente.

Note importante: Python ne garantit pas un vrai temps constant au niveau machine (interpreter, GC, objets). Pour une securite materielle stricte, il faut une implementation bas niveau auditee (C/Rust + primitives constantes).

## Correctif 3 - Validation stricte des entrees (bornes + cle publique)

### Probleme corrige
Sans validation stricte de $(r,s)$, des signatures forgees (ex: `(0,0)`) peuvent etre acceptees.

### Correction implementee
Dans `verify_signature(...)`:

- verification de format de signature,
- verification stricte: $1 <= r,s < n$,
- validation de la cle publique (point sur courbe + test d ordre $nQ = O$),
- rejet des cas degeneres (point a l infini).

### Resultat observe
- `Signature forgee (0,0) acceptee: False`

Conclusion: la classe de bug type Psychic Signatures est bloquee.

## Impact performance

Mesure locale (10 iterations) issue de `ecdsa_hardened_run.txt`:

- `Sign avg (s): 0.02184`
- `Verify avg (s): 0.041086`
- `Sign min/max (s): 0.018716 / 0.032069`
- `Verify min/max (s): 0.033454 / 0.061615`

Interpretation:

- Le hardening side-channel augmente le cout de calcul (profil fixe + blinding).
- En contrepartie, le niveau de robustesse securite est nettement superieur.

## Resume des gains

| Axe | Avant | Apres |
| :-- | :-- | :-- |
| Nonce | aleatoire classique, risque RNG | deterministic RFC6979 |
| Side-channel | profil variable selon bits | ladder fixe + scalar blinding |
| Verification | depend de l implementation | bornes strictes + validation cle publique |

## Recommandations production

1. Conserver RFC6979 comme politique nonce par defaut.
2. Garder la validation stricte de `(r,s)` et des cles publiques.
3. Migrer la crypto critique vers une bibliotheque auditee en constant-time reel.
4. Ajouter des tests unitaires sur les cas limites (r=0, s=0, point infini, pubkey invalide).
