# Synthèse de Projet — PPE25-R-508

---

## Page de garde

| | |
|---|---|
| **Projet** | PPE25-R-508 |
| **Titre** | Sécurisation des transactions bancaires par signatures numériques via courbes elliptiques (ECDSA) |
| **Problématique** | Comment sécuriser efficacement les transactions bancaires à l'aide du protocole ECDSA, et en quoi cette méthode présente-t-elle des avantages par rapport aux signatures basées sur RSA ? |
| **Contexte actualisé** | La montée en puissance des paiements numériques et des API bancaires Open Banking rend critique la robustesse des protocoles de signature numérique. ECDSA, standard mondial (Bitcoin, TLS, cartes à puce), est massivement déployé mais reste vulnérable à des erreurs d'implémentation documentées. |
| **Solution en une phrase** | Implémentation complète d'ECDSA et RSA depuis les fondements, comparaison benchmarkée des deux algorithmes, démonstration de trois attaques critiques sur ECDSA, durcissement conforme RFC 6979, et interface web de simulation bancaire déployée sur Vercel. |
| **Nombre de mots** | ≈ 2 600 |

---

## Abstract

Ce projet explore la sécurisation des transactions bancaires par le protocole ECDSA (*Elliptic Curve Digital Signature Algorithm*). Partant d'une comparaison accessible avec RSA — l'algorithme de référence historique — nous avons implémenté les deux protocoles en Python depuis leurs bases, puis conduit une analyse comparative de leurs performances. Trois catégories d'attaques critiques sur ECDSA ont été étudiées et reproduites : la réutilisation de nonce, les canaux auxiliaires de type SPA (*Simple Power Analysis*), et l'omission de vérification des bornes — illustrée par le CVE-2022-21449 dit *Psychic Signatures*. Une version durcie a ensuite été développée, appliquant le nonce déterministe RFC 6979, la multiplication scalaire en style Montgomery ladder avec *scalar blinding*, et une validation stricte des entrées. Enfin, une application web de simulation de banque a été déployée sur Vercel, permettant de visualiser en temps réel les échanges signés, de comparer les algorithmes et d'observer les métriques des attaques et de leurs correctifs.

---

## 1. Concepts clés

### Chiffrement vs signature numérique : deux usages très différents

En sécurité informatique, on confond souvent deux opérations distinctes : **chiffrer** et **signer**. Elles ne répondent pas au même besoin.

| | Chiffrement | Signature numérique |
|---|---|---|
| **But** | Garder un message secret | Prouver l'identité de l'émetteur et l'intégrité du message |
| **Question posée** | "Qui peut lire ce message ?" | "Ce message vient-il vraiment de cette personne ?" |
| **Clé utilisée** | Clé publique du destinataire | Clé privée de l'émetteur |
| **Vérification** | Le destinataire déchiffre | N'importe qui peut vérifier avec la clé publique |

Dans le monde bancaire, ce qui importe avant tout c'est la **signature** : lorsque vous validez un virement, la banque doit être certaine que c'est **vous** qui avez autorisé l'opération, et que le montant n'a pas été modifié en transit. Le chiffrement protège la confidentialité des données ; la signature garantit l'**authenticité** et l'**intégrité**.

### Pourquoi les signatures numériques sont critiques en finance

Une signature numérique, c'est l'équivalent d'un sceau notarié infalsifiable. Concrètement :

- Sans signature, un attaquant positionné entre vous et votre banque (*man-in-the-middle*) pourrait modifier le bénéficiaire ou le montant d'un virement.
- Avec une signature cryptographique valide, toute modification du message invalide automatiquement la signature — la banque détecte l'altération immédiatement.
- La signature prouve également la **non-répudiation** : l'émetteur ne peut pas nier avoir signé le message, car seul le détenteur de la clé privée peut produire une signature valide.

Les protocoles ECDSA et RSA sont les deux grandes familles de signatures numériques déployées en production aujourd'hui. Ce projet les a tous deux implémentés, comparés et testés sous attaque.

---

## 2. Méthodologie de travail

### Objectifs SMART du projet

Le projet s'est structuré autour de cinq objectifs progressifs, définis dès le lancement :

| # | Objectif | Livrable associé |
|---|---|---|
| 1 | Comprendre les **fondements mathématiques** de la cryptographie elliptique et de RSA | État de l'art, note de cadrage |
| 2 | **Implémenter** les protocoles RSA et ECDSA pour signer et vérifier des transactions | Programmes de signature RSA, ECDSA et EdDSA |
| 3 | **Analyser les performances** ECDSA vs RSA | Benchmarks avec résultats mesurés et exportés |
| 4 | **Simuler une attaque** sur une mauvaise implémentation ECDSA | 3 scénarios d'attaque documentés et reproductibles |
| 5 | Trouver des **axes d'amélioration** et les appliquer | Version durcie et rapport d'améliorations |

### Organisation et progression

Le projet a suivi un phasage séquentiel calqué sur ces cinq objectifs, visible dans le diagramme de Gantt établi en début de projet :

| Phase | Contenu |
|---|---|
| 1 — Fondements | Étude mathématique, réunion de suivi, synthèse des concepts |
| 2 — Implémentation | Conception des programmes, développement des protocoles, tests et validation |
| 3 — Performances | Analyse comparative, mesures benchmarkées, soutenance mi-parcours |
| 4 — Attaques | Analyse des failles, conception des scénarios d'attaque, simulation |
| 5 — Améliorations | Recherche de correctifs, développement de la version durcie, simulation opérationnelle |
| 6 — Soutenance finale | Préparation, démo sur l'application web |

### Outils utilisés

| Catégorie | Outils |
|---|---|
| Langage principal | Python 3.12 |
| Fonctions cryptographiques | Hachage SHA-256/512, génération HMAC de nonce (RFC 6979) |
| Versionning | Git / GitHub |
| Références | RFC 6979, FIPS 186-5, SEC 1 v2.0, NIST SP 800-56A |
| Interface web / Démo | Next.js + Vercel |
| Documentation | Rapports techniques et sources scientifiques annotées |

Le référent projet a été consulté lors des jalons de validation : choix de la courbe elliptique, périmètre des attaques, arbitrage scope de l'interface web.

---

## 3. Conception et développement

### 3.1 Comment fonctionnent RSA et ECDSA — une analogie accessible

**RSA** (inventé en 1977) repose sur la difficulté de **factoriser de très grands nombres** : multiplier deux nombres premiers entre eux est facile, mais retrouver ces deux facteurs à partir du résultat est computationnellement impossible à l'échelle qu'emploie RSA. Pour atteindre un bon niveau de sécurité, les clés doivent être très longues — typiquement 2 048 bits, soit un nombre de plusieurs centaines de chiffres.

**ECDSA** (standard depuis 1999) s'appuie sur les **courbes elliptiques** : des courbes mathématiques aux propriétés particulières, définies sur des nombres entiers. L'opération fondamentale — multiplier un point de la courbe par un entier — est facile dans un sens mais impossible à inverser. L'intuition est proche de RSA, mais la structure géométrique de la courbe rend le problème beaucoup plus "concentré" : on obtient le même niveau de sécurité avec des clés **8 fois plus courtes**.

> Pour le contexte bancaire, c'est crucial : des clés plus petites signifient des signatures plus légères, des certificats TLS moins volumineux, et des appareils embarqués (cartes à puce, terminaux de paiement) moins sollicités.

### 3.2 ECDSA vs RSA — comparaison des performances

Les benchmarks réalisés en Python pur permettent de comparer objectivement les deux approches sur les mêmes opérations :

#### Génération de clés

| Algorithme | Niveau de sécurité équivalent | Taille de clé | Temps de génération |
|---|---|---|---|
| ECDSA secp256k1 | ~128 bits | **255 bits** | **62 ms** |
| RSA-1024 | ~80 bits | 1 024 bits | 238 ms |
| RSA-2048 | ~112 bits | 2 048 bits | 2 523 ms |

ECDSA génère une paire de clés offrant plus de sécurité que RSA-2048, en **40× moins de temps** et avec des clés **8× plus compactes**.

#### Signature et vérification

| Algorithme | Signature (moy.) | Vérification (moy.) |
|---|---|---|
| ECDSA secp256k1 | ~12 ms | ~24 ms |
| RSA-1024 | ~5 ms | ~0,2 ms |
| RSA-2048 | ~28 ms | ~0,3 ms |

RSA est plus rapide à la *signature* grâce à la structure de son exposant privé, et très rapide à la *vérification* (exposant public petit). ECDSA est plus équilibré entre les deux. Dans un contexte bancaire à haute fréquence, les deux approches sont viables, mais ECDSA l'emporte nettement sur le critère clé : la **taille des clés et certificats**, déterminante pour les systèmes embarqués.

#### Impact de la taille du message

| Taille message | Temps de signature ECDSA |
|---|---|
| 10 octets | 116 ms |
| 100 octets | 117 ms |
| 1 000 octets | 121 ms |
| 5 000 octets | 120 ms |

Le temps est quasi constant quelle que soit la taille du message : les deux algorithmes signent le *hash* du message (empreinte de taille fixe), pas le message lui-même. La taille du contenu à signer n'a donc pratiquement aucun impact.

### 3.3 Implémentation des protocoles

Les deux protocoles ont été codés **intégralement en Python**, sans bibliothèque cryptographique externe. Ce choix pédagogique force à comprendre chaque étape de l'algorithme et à gérer explicitement tous les cas limites — notamment les points à l'infini dans la géométrie des courbes elliptiques, dont la mauvaise gestion est à l'origine de failles réelles.

Une implémentation EdDSA — variante moderne plus robuste d'ECDSA, utilisée notamment dans le protocole Signal — a également été produite pour enrichir la comparaison algorithmique.

### 3.4 Les trois attaques sur ECDSA

À ce stade du projet, l'objectif était de montrer qu'une implémentation techniquement correcte sur le papier peut être totalement vulnérable si certains détails d'implémentation sont négligés.

#### Attaque 1 — Réutilisation du nonce

Lors de chaque signature ECDSA, un nombre aléatoire secret appelé *nonce* est tiré. Si ce nonce est réutilisé — même accidentellement — pour signer deux messages différents, un attaquant peut retrouver mathématiquement la clé privée en quelques opérations. C'est exactement ce qui a compromis la console **Sony PS3 en 2010** : le firmware utilisait le même nonce pour toutes ses signatures.

**Résultat observé** : lors de nos tests, la clé privée a été intégralement reconstituée par le programme simulant l'attaquant.

#### Attaque 2 — Canal auxiliaire SPA (simulation)

Dans l'algorithme de signature naïf, les calculs internes suivent un chemin différent selon les bits du nonce. Un attaquant qui peut observer la consommation électrique du processeur (ou le temps d'exécution) peut en déduire ces bits, puis reconstruire le nonce et la clé privée. C'est ce qu'on appelle une *side-channel attack*.

Notre programme simule cette trace d'opérations et démontre la reconstruction complète du nonce, puis la récupération de la clé privée. Le nombre d'opérations internes varie significativement selon la valeur du nonce — cette variation est précisément le signal qu'un attaquant réel exploiterait.

#### Attaque 3 — Omission des bornes (*Psychic Signatures*)

Le standard ECDSA impose que les deux composantes d'une signature respectent certaines bornes. Si le vérificateur omet cette vérification, une signature entièrement falsifiée — dont les valeurs sont délibérément invalides — peut être acceptée comme légitime. Cette faille a existé en production dans **Java 15, 16 et 17** (CVE-2022-21449, découvert en 2022) et permettait de contourner toute authentification basée sur ECDSA.

**Résultat observé** : notre vérificateur vulnérable a bien accepté cette signature frauduleuse lors des tests, tandis que le vérificateur strict l'a rejetée.

### 3.5 Version durcie

Trois correctifs ont été appliqués, un par vecteur d'attaque :

| Vecteur | Problème | Correctif appliqué |
|---|---|---|
| Réutilisation de nonce | Nonce aléatoire — risque de collision ou de bug RNG | **Nonce déterministe RFC 6979** : dérivé de la clé privée et du message via HMAC-SHA256, jamais répété |
| Canal auxiliaire | Profil d'opérations variable selon les bits du nonce | **Montgomery ladder** à longueur fixe (nombre d'opérations constant quelle que soit la clé) + *scalar blinding* |
| Omission de bornes | Aucune validation des composantes de signature | Vérification stricte des bornes + validation du point de clé publique sur la courbe |

#### Impact sur les performances

| Opération | ECDSA classique | ECDSA durci | Surcoût |
|---|---|---|---|
| Signature | 11,8 ms | 20,5 ms | ×1,74 |
| Vérification | 24,1 ms | 39,1 ms | ×1,62 |

Le surcoût d'environ ×1,7 est la contrepartie directe du profil fixe et des validations supplémentaires — un prix raisonnable pour bloquer les trois familles d'attaques.

### 3.6 Application web de simulation bancaire

En phase finale, une application web a été développée et déployée sur **Vercel** (infrastructure cloud sans serveur) pour rendre le projet démontrable à tout public. Elle permet de :

- **Simuler des échanges bancaires** : génération de clés, signature d'une transaction (montant, bénéficiaire), vérification côté banque
- **Comparer les algorithmes** RSA, ECDSA et ECDSA durci sur les mêmes transactions, avec affichage des métriques de performance
- **Visualiser les attaques** : reproduire les trois scénarios en direct et observer comment le correctif correspondant les neutralise

Cette couche de communication a été particulièrement utile lors de la soutenance finale pour rendre concrets des concepts mathématiquement abstraits.

---

## 4. Défis rencontrés

### Défi technique 1 — Implémenter sans bibliothèque externe

Développer les opérations sur courbes elliptiques de zéro exige de traiter explicitement tous les cas limites qu'une bibliothèque cryptographique gèrerait silencieusement — notamment les configurations géométriques dégénérées ou les valeurs mathématiquement invalides. Chacun de ces cas non traités correspond précisément à une faille réelle documentée dans la littérature. C'est exigeant, mais c'est aussi le cœur de l'apprentissage.

### Défi technique 2 — La limite du "temps constant" en Python

Le montgomery ladder et le *scalar blinding* éliminent les fuites au niveau *algorithmique* — le profil d'opérations devient fixe. Mais le langage Python ne garantit pas un temps d'exécution strictement constant au niveau machine : ses mécanismes internes de gestion mémoire et d'interprétation introduisent un bruit temporel que l'on ne contrôle pas. Nos résultats démontrent l'absence de fuite au niveau structurel de l'algorithme, pas une résistance physique certifiée. Une implémentation production nécessiterait un langage bas niveau (C ou Rust) avec des bibliothèques cryptographiques auditées.

### Défi technique 3 — Concevoir une démo web accessible

L'interface web devait être pédagogique sans être simpliste. Trouver l'équilibre — montrer le cycle complet de signature/vérification, rendre les métriques d'attaque lisibles — a demandé plusieurs itérations de design. Le choix d'exposer les résultats chiffrés (temps, taille de clé, résultat d'attaque) directement dans l'UI a finalement bien fonctionné.

### Défi méthodologique — Délimiter le scope

La frontière entre démonstration pédagogique et un vrai système de production n'est pas triviale à communiquer. Nos implémentations ne sont pas utilisables en production : elles ne couvrent pas l'ensemble des protections requises par les standards industriels. Documenter clairement cette limite — plutôt que la masquer — est une démarche d'honnêteté intellectuelle qui nous a guidés dans la rédaction de tous les livrables.

---

## 5. Résultats & livrables

### Livrables produits

| Livrable | Description |
|---|---|
| Programme ECDSA | Signature et vérification ECDSA intégrant 3 scénarios d'attaque reproductibles |
| Programme ECDSA durci | Version corrigée appliquant les trois correctifs de sécurité |
| Programme EdDSA | Signature et vérification selon la variante EdDSA (Ed25519) |
| Programme RSA | Signature et vérification RSA complètes |
| Benchmarks | Mesures de performance comparées ECDSA et RSA |
| Rapport de comparaison | Analyse automatisée côte-à-côte entre version vulnérable et version durcie |
| Rapport des attaques | Documentation détaillée des 3 attaques avec résultats d'exécution |
| Rapport des améliorations | Documentation des correctifs appliqués et analyse des gains obtenus |
| Application web Vercel | Simulation bancaire interactive : signature, comparaison algorithmique, attaques en direct |

### Résultats de sécurité synthétiques

| Test de sécurité | Version classique | Version durcie |
|---|---|---|
| Récupération de la clé privée via réutilisation de nonce | **Attaque réussie** | Bloquée par construction |
| Reconstruction du nonce via analyse de la trace d'exécution | **Attaque réussie** | Profil fixe — aucun signal exploitable |
| Acceptation d'une signature frauduleuse | **Acceptée** | **Rejetée** |
| Stabilité du nonce sur le même message | Non garantie | Garantie |
| Unicité du nonce sur des messages différents | Non garantie | Garantie |

Les trois vecteurs d'attaque sont bloqués dans la version durcie, de manière entièrement vérifiable et reproductible.

---

## 6. Analyse critique

### Ce qui fonctionne bien

Les scénarios d'attaque sont **totalement reproductibles** — chaque exécution produit le même résultat, documenté et archivé dans nos livrables. La comparaison automatisée entre version classique et version durcie permet à n'importe qui de reproduire les mesures sans configuration particulière. L'application web a rendu le projet communicable à un public non technique, ce qui était un vrai défi compte tenu de l'abstraction du sujet.

### Limites identifiées

- **Courbe unique** : seule secp256k1 a été implémentée. Tester P-256 (NIST) ou Curve25519 aurait enrichi la comparaison, mais dépassait le scope défini.
- **RSA simplifié** : notre implémentation RSA ne couvre pas toutes les protections supplémentaires requises en production, ce qui la rend suffisante pour la comparaison algorithmique mais pas déployable telle quelle.
- **Python ≠ production** : les temps mesurés illustrent des tendances algorithmiques, pas des performances système réelles.

### Ce qu'on ferait autrement

Anticiper la couche web dès la phase d'implémentation aurait permis de mieux structurer nos programmes pour qu'ils s'interfacent directement avec l'interface utilisateur, sans adaptation tardive. Nous aurions aussi mis en place des tests automatisés sur les cas aux limites dès le début — ils auraient accéléré le débogage des failles lors de la phase attaques.

---

## 7. Ouverture : l'ère post-quantique

Une question incontournable plane sur tous les algorithmes étudiés dans ce projet : **que se passera-t-il quand les ordinateurs quantiques seront suffisamment puissants ?**

L'algorithme de Shor, exécutable sur un ordinateur quantique de grande taille, peut résoudre le problème du logarithme discret (base d'ECDSA) et la factorisation de grands entiers (base de RSA) en temps raisonnable. Autrement dit, RSA, ECDSA et EdDSA seraient tous cassables.

| Algorithme | Base mathématique | Résistance quantique |
|---|---|---|
| RSA-2048 | Factorisation | ✗ Cassable par algorithme de Shor |
| ECDSA secp256k1 | Log. discret sur courbe | ✗ Cassable par algorithme de Shor |
| EdDSA (Ed25519) | Log. discret sur courbe | ✗ Cassable par algorithme de Shor |
| **CRYSTALS-Dilithium** | Réseaux euclidiens | ✓ Standard NIST PQC (FIPS 204, 2024) |
| **FALCON** | Réseaux NTRU | ✓ Standard NIST PQC (FIPS 206, 2024) |

Le NIST a publié en 2024 ses premiers standards de cryptographie post-quantique. **CRYSTALS-Dilithium** est le successeur désigné d'ECDSA pour les signatures numériques. Le secteur bancaire (SWIFT, EMVCo) planifie activement la migration. Ce projet constitue ainsi un socle de compréhension essentiel : maîtriser ECDSA aujourd'hui, c'est comprendre ce qu'il faudra remplacer — et pourquoi.

---

## 8. Conclusion

Ce projet nous a permis de parcourir l'intégralité de la chaîne de sécurité d'une signature numérique bancaire : des fondements mathématiques jusqu'à une interface de démonstration déployée en ligne. Les cinq objectifs SMART initiaux ont été atteints, du plus théorique (comprendre la cryptographie sur courbes elliptiques) au plus pratique (simuler des attaques et appliquer des correctifs).

La leçon centrale est que la solidité d'un algorithme cryptographique ne garantit pas la sécurité d'une implémentation. Un nonce répété, une vérification omise, un profil d'opérations observable — chacun de ces détails suffit à compromettre un système qui s'appuie sur un protocole mathématiquement irréprochable. C'est ce que ce projet démontre de manière concrète et reproductible.

Sur le plan humain, ce projet a développé notre capacité à lire des standards cryptographiques techniques, à produire du code documenté et rigoureusement testé, et à communiquer des résultats complexes à des audiences variées — des slides de soutenance jusqu'à l'application web accessible à tous.

---

## Références principales

| Référence | Type |
|---|---|
| RFC 6979 — Deterministic Usage of DSA and ECDSA | Standard IETF |
| FIPS 186-5 — Digital Signature Standard | Standard NIST |
| SEC 1 v2.0 — Elliptic Curve Cryptography (SECG) | Standard industriel |
| NIST SP 800-56A Rev. 3 | Guide NIST |
| CVE-2022-21449 (*Psychic Signatures* Java) | Vulnérabilité réelle |
| Kocher et al. — Differential Power Analysis (CRYPTO'99) | Recherche académique |
| Coron — Resistance Against DPA for ECC (CHES'99) | Recherche académique |
| NIST FIPS 204 — CRYSTALS-Dilithium (2024) | Standard post-quantique |
