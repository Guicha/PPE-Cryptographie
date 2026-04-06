# Rapport de laboratoire - 3 attaques critiques ECDSA

Ce rapport decrit les trois attaques implementees dans le projet, avec un scenario reproductible pour chacune, les consequences cryptographiques, et les contre-mesures.

## Contexte

- Courbe utilisee: secp256k1
- Fichier principal: ecdsa.py
- Objectif: montrer concretement comment une faiblesse d'implementation ECDSA peut mener a la recuperation de la cle privee ou au contournement de verification.

## Commande de reproduction

```powershell
.venv\Scripts\python.exe ecdsa.py
```

La derniere execution est enregistree dans `ecdsa_attack_run.txt`.

---

## 1) Attaque par reutilisation du nonce

### Idee
Si deux signatures ECDSA utilisent le meme nonce $k$, elles partagent la meme valeur $r$. Cela suffit pour retrouver $k$, puis la cle privee $d$.

Equation ECDSA:

$$
s \equiv k^{-1}(z + r d) \pmod n
$$

Avec deux signatures sur deux messages differents:

$$
k \equiv (z_1 - z_2)(s_1 - s_2)^{-1} \pmod n
$$

Puis:

$$
d \equiv (s_1 k - z_1) r^{-1} \pmod n
$$

### Scenario implemente
- Generation d'une cle privee aleatoire.
- Signature de deux messages differents avec le meme nonce force.
- Recuperation de $k$ et de la cle privee par un attaquant.
- Verification que la cle retrouvee est identique a la cle reelle.

### Fonctions associees
- `sign_message_with_nonce(...)`
- `recover_private_key_from_reused_nonce(...)`
- `scenario_nonce_reuse_attack()`

### Resultat observe
- `Meme r entre les deux signatures: True`
- `Nonce retrouve correct: True`
- `Cle privee retrouvee: True`

---

## 2) Attaque par canal auxiliaire SPA (simulation)

### Idee
Dans un algorithme Double-and-Add non protege, la sequence des operations depend des bits du nonce $k$:
- bit 0: `D` (doublement)
- bit 1: `D` + `A` (doublement + addition)

Une trace de consommation (ou de timing) peut donc reveler la representation binaire de $k$.

### Scenario implemente
- Signature avec une multiplication scalaire qui renvoie une trace d'operations (`D`/`A`).
- Reconstruction du nonce a partir de la trace.
- Recuperation de la cle privee depuis la signature et le nonce expose.

### Fonctions associees
- `scalar_multiply_with_trace(...)`
- `recover_nonce_from_trace(...)`
- `recover_private_key_from_known_nonce(...)`
- `scenario_side_channel_spa_attack()`

### Resultat observe
- `Nonce reconstruit depuis trace: True`
- `Cle privee retrouvee depuis nonce expose: True`

### Remarque
Cette partie est une simulation pedagogique de SPA. En pratique, la fuite vient d'un trace de puissance, d'EM, ou de temps d'execution.

---

## 3) Omission de verification des bornes (Psychic-style)

### Idee
Le standard ECDSA impose:

$$
1 \le r,s < n
$$

Si ces bornes ne sont pas verifiees, des signatures invalides (ex: $(0,0)$) peuvent etre acceptees selon les bugs de l'implementation (inverse de 0, gestion du point a l'infini, etc.).

### Scenario implemente
- Verificateur volontairement vulnerable:
  - pas de controle de bornes;
  - comportement buggy sur inverse(0);
  - handling invalide de cas degeneres.
- Test d'une signature forgee `(0, 0)`.
- Comparaison avec un verificateur strict qui applique les controles.

### Fonctions associees
- `verify_signature_no_bounds_buggy(...)`
- `verify_signature(...)`
- `scenario_missing_bounds_attack()`

### Resultat observe
- `Verifier vulnerable accepte (attendu=True): True`
- `Verifier strict accepte (attendu=False): False`

---

## Extrait de sortie de la derniere execution

```text
=== SCENARIO 1: Reutilisation du nonce ===
Meme r entre les deux signatures: True
Nonce retrouve correct: True
Cle privee retrouvee: True

=== SCENARIO 2: Canal auxiliaire SPA (simulation) ===
Nonce reconstruit depuis trace: True
Cle privee retrouvee depuis nonce expose: True

=== SCENARIO 3: Omission des bornes (Psychic-style) ===
Verifier vulnerable accepte (attendu=True): True
Verifier strict accepte (attendu=False): False
```

---

## Sources

### Reutilisation du nonce
1. RFC 6979 - Deterministic Usage of DSA and ECDSA  
   https://datatracker.ietf.org/doc/html/rfc6979
2. FIPS 186-5 - Digital Signature Standard (DSS)  
   https://csrc.nist.gov/publications/detail/fips/186/5/final
3. Sony PS3 ECDSA fail (analyse historique)  
   https://www.schneier.com/blog/archives/2011/01/sony_ps3_securi.html

### Canaux auxiliaires
1. Kocher et al. - Differential Power Analysis (CRYPTO'99)  
   https://www.iacr.org/cryptodb/data/paper.php?pubkey=1471
2. Coron - Resistance against Differential Power Analysis for ECC (CHES 1999)  
   https://www.iacr.org/cryptodb/data/paper.php?pubkey=660
3. NIST SP 800-56A Rev.3  
   https://csrc.nist.gov/publications/detail/sp/800-56a/rev-3/final

### Omission des bornes / Psychic Signatures
1. CVE-2022-21449  
   https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-21449
2. Oracle Critical Patch Update Advisory (April 2022)  
   https://www.oracle.com/security-alerts/cpuapr2022.html
3. Neil Madden - Psychic Signatures in Java  
   https://neilmadden.blog/2022/04/19/psychic-signatures-in-java/

---

## Conclusion

Les trois scenarios montrent trois familles de risques ECDSA:
- erreur de generation (nonce),
- fuite physique (side-channel),
- bug de verification (input validation).

Dans un contexte production (banque, API de paiement, signature de transactions), la combinaison de ces trois protections est obligatoire:
- nonce deterministe RFC 6979,
- implementation constante en temps + hardening side-channel,
- validation stricte de toutes les bornes d'entree.
