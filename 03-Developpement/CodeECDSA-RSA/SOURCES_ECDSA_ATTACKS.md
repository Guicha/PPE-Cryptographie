# Sources fiables pour les 3 attaques ECDSA

## 1) Reutilisation du nonce

1. RFC 6979 - Deterministic Usage of DSA and ECDSA
   https://datatracker.ietf.org/doc/html/rfc6979

2. FIPS 186-5 - Digital Signature Standard (DSS)
   https://csrc.nist.gov/publications/detail/fips/186/5/final

3. Sony PS3 ECDSA fail (nonce non aleatoire / repete) - analyse historique
   https://www.schneier.com/blog/archives/2011/01/sony_ps3_securi.html

## 2) Canaux auxiliaires (SPA / DPA)

1. Kocher et al. - Differential Power Analysis (CRYPTO'99)
   https://www.iacr.org/cryptodb/data/paper.php?pubkey=1471

2. Coron - Resistance against Differential Power Analysis for ECC (CHES 1999)
   https://www.iacr.org/cryptodb/data/paper.php?pubkey=660

3. NIST SP 800-56A Rev. 3 (guidance generale ECC + implementation considerations)
   https://csrc.nist.gov/publications/detail/sp/800-56a/rev-3/final

## 3) Omission des bornes (Psychic Signatures)

1. CVE-2022-21449
   https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-21449

2. Oracle Critical Patch Update Advisory (avril 2022)
   https://www.oracle.com/security-alerts/cpuapr2022.html

3. Neil Madden - Psychic Signatures in Java
   https://neilmadden.blog/2022/04/19/psychic-signatures-in-java/

## Conseils de lecture complementaires

1. SEC 1 v2.0 - Elliptic Curve Cryptography (standards SECG)
   https://www.secg.org/sec1-v2.pdf

2. BSI - TR-02102 (recommandations crypto, signatures et implementation)
   https://www.bsi.bund.de
