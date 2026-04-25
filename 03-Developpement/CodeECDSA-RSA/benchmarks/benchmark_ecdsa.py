"""
benchmark_ecdsa.py

Script pour mesurer les performances de ton implémentation ECDSA/Ed25519 (ecdsa.py) :

- Temps de génération des clés
- Taille des clés (privée et publique)
- Temps de hachage (hash_elements / SHA-512)
- Temps de signature
- Temps de vérification
- Impact de la taille du message sur les temps de hash, signature et vérification

⚠️ Pré-requis :
    - Ce fichier doit être dans le même dossier que `ecdsa.py`
    - Le module sera importé sous le nom ECDSA
"""

import time
import csv
import statistics
import hashlib
import random  # pour régénérer nous-mêmes les clés sans les prints
import ecdsa as ECDSA  # ton fichier ecdsa.py (assure-toi que le nom est bien celui-là)


# ============================================================
# UTILITAIRE : MESURER LE TEMPS D'UNE FONCTION
# ============================================================

def measure_time(func, *args, **kwargs):
    """
    Mesure le temps d'exécution d'une fonction.

    Retourne :
        result  : ce que retourne la fonction
        elapsed : temps écoulé en secondes (float)
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    elapsed = end - start
    return result, elapsed

def safe_hash_elements(*elements):
    """
    Version locale et sûre de hash_elements pour le benchmark :
    - convertit les grands entiers en bytes (au lieu de str(int))
    - évite l'erreur "Exceeds the limit (4300 digits)" de Python
    """
    hasher = hashlib.sha512()

    for element in elements:
        # Cas 1 : entier
        if isinstance(element, int):
            if element == 0:
                b = b"\x00"
            else:
                length = (element.bit_length() + 7) // 8
                b = element.to_bytes(length, "big", signed=False)
            hasher.update(b)

        # Cas 2 : déjà en bytes
        elif isinstance(element, (bytes, bytearray)):
            hasher.update(element)

        # Cas 3 : tuple / liste (ex : point (x, y))
        elif isinstance(element, (tuple, list)):
            for sub in element:
                if isinstance(sub, int):
                    if sub == 0:
                        sb = b"\x00"
                    else:
                        length = (sub.bit_length() + 7) // 8
                        sb = sub.to_bytes(length, "big", signed=False)
                    hasher.update(sb)
                elif isinstance(sub, (bytes, bytearray)):
                    hasher.update(sub)
                else:
                    hasher.update(str(sub).encode("utf-8"))

        # Cas 4 : string ou autre
        else:
            hasher.update(str(element).encode("utf-8"))

    return int(hasher.hexdigest(), 16)



# ============================================================
# GENERATION DE CLES (SANS PRINTS)
# ============================================================

def generate_keypair_core():
    """
    Reproduit la logique de generate_keypair() dans ecdsa.py,
    mais SANS les print, pour avoir des mesures propres.

    private_key : entier aléatoire dans [1, PRIME-1]
    public_key  : point sur la courbe = private_key * BASE_POINT
    """
    # Clé privée 256 bits (comme dans ecdsa.py)
    private_key = random.getrandbits(256)
    private_key = private_key % (ECDSA.PRIME - 1) + 1

    # Clé publique = scalaire * point de base
    public_key = ECDSA.scalar_multiplication(ECDSA.BASE_POINT, private_key)

    return private_key, public_key


def benchmark_key_generation(repeat=10):
    """
    Mesure le temps de génération de paires de clés ECDSA/Ed25519.

    Paramètres :
        repeat : nombre de fois où on génère une nouvelle paire pour faire une moyenne

    Retourne un dict :
        {
            "curve_bits": taille du module PRIME (255 bits pour Ed25519),
            "avg_time":   temps moyen pour générer une paire de clés,
            "min_time":   temps minimal observé,
            "max_time":   temps maximal observé,
            "priv_key_bits": taille de la clé privée en bits,
            "pub_x_bits":    taille de la coordonnée x de la clé publique,
            "pub_y_bits":    taille de la coordonnée y de la clé publique,
        }
    """
    times = []
    last_priv = None
    last_pub = None

    curve_bits = ECDSA.PRIME.bit_length()
    print(f"\n=== Benchmark génération de clés sur une courbe de {curve_bits} bits ===")

    for i in range(repeat):
        (priv, pub), t = measure_time(generate_keypair_core)
        times.append(t)
        last_priv = priv
        last_pub = pub
        print(f"  Essai {i+1}/{repeat} : {t:.6f} s")

    priv_key_bits = last_priv.bit_length()
    pub_x_bits = last_pub[0].bit_length()
    pub_y_bits = last_pub[1].bit_length()

    result = {
        "curve_bits": curve_bits,
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
        "priv_key_bits": priv_key_bits,
        "pub_x_bits": pub_x_bits,
        "pub_y_bits": pub_y_bits,
    }

    print(f"  -> Temps moyen keygen : {result['avg_time']:.6f} s")
    print(f"  -> Taille clé privée  : {priv_key_bits} bits")
    print(f"  -> Taille clé publique x : {pub_x_bits} bits")
    print(f"  -> Taille clé publique y : {pub_y_bits} bits")

    return result, last_priv, last_pub


# ============================================================
# HACHAGE (SHA-512 via hash_elements)
# ============================================================

def benchmark_hash(message, repeat=10):
    """
    Mesure le temps de hachage avec safe_hash_elements(message).
    On passe directement le message (string) à la fonction de hash.
    """
    curve_bits = ECDSA.PRIME.bit_length()
    times = []

    print(f"\n=== Benchmark hachage pour message de longueur {len(message)} ===")

    for i in range(repeat):
        _, t = measure_time(safe_hash_elements, message)
        times.append(t)
        print(f"  Essai {i+1}/{repeat} : {t:.8f} s")

    result = {
        "curve_bits": curve_bits,
        "message_length": len(message),
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
    }

    print(f"  -> Temps moyen hash_elements (safe) : {result['avg_time']:.8f} s")

    return result

def hash_elements(*elements):
    """
    Hache une série d'éléments avec SHA-512
    Correction : conversion sécurisée des grands entiers en bytes.
    """
    hasher = hashlib.sha512()

    for element in elements:

        # 🧩 Cas 1 — ENTIER
        if isinstance(element, int):
            if element == 0:
                element_bytes = b"\x00"
            else:
                length = (element.bit_length() + 7) // 8
                element_bytes = element.to_bytes(length, "big")
            hasher.update(element_bytes)

        # 🧩 Cas 2 — BYTES
        elif isinstance(element, (bytes, bytearray)):
            hasher.update(element)

        # 🧩 Cas 3 — TUPLE/LISTE
        elif isinstance(element, (tuple, list)):
            for sub in element:
                if isinstance(sub, int):
                    if sub == 0:
                        sub_bytes = b"\x00"
                    else:
                        length = (sub.bit_length() + 7) // 8
                        sub_bytes = sub.to_bytes(length, "big")
                    hasher.update(sub_bytes)
                elif isinstance(sub, (bytes, bytearray)):
                    hasher.update(sub)
                else:
                    hasher.update(str(sub).encode("utf-8"))

        # 🧩 Cas 4 — AUTRES TYPES
        else:
            hasher.update(str(element).encode("utf-8"))

    return int(hasher.hexdigest(), 16)

# ============================================================
# SIGNATURE (réimplémentée sans print)
# ============================================================

def sign_core(message, private_key):
    """
    Version "benchmark" de sign_message, sans print
    et utilisant safe_hash_elements au lieu de ECDSA.hash_elements.
    """
    PRIME = ECDSA.PRIME

    # 1) Convertir le message en entier (comme avant)
    if isinstance(message, str):
        message_int = ECDSA.message_to_int(message)
    else:
        message_int = int.from_bytes(message, 'big')

    # 2) Générer le nonce r avec safe_hash_elements
    r_seed = safe_hash_elements(message_int, private_key, "nonce")
    r = r_seed % (PRIME - 1) + 1

    # 3) Calculer R = r * G
    R = ECDSA.scalar_multiplication(ECDSA.BASE_POINT, r)

    # 4) Clé publique à partir de la clé privée
    public_key = ECDSA.scalar_multiplication(ECDSA.BASE_POINT, private_key)

    # 5) Challenge h avec safe_hash_elements
    h = safe_hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME

    # 6) s = r + h * private_key
    s = r + h * private_key

    return (R, s)



def benchmark_sign(message, private_key, repeat=10):
    """
    Mesure le temps de signature ECDSA/Ed25519 pour un message donné
    et une clé privée donnée.

    On utilise la fonction sign_core() qui ne fait que les calculs,
    sans affichage.

    Paramètres :
        message     : string (ou bytes)
        private_key : entier (clé privée)
        repeat      : nombre de répétitions

    Retourne :
        {
            "curve_bits": taille de la courbe,
            "message_length": longueur du message,
            "avg_total_time": temps moyen de signature,
            "min_total_time": min,
            "max_total_time": max,
        }
    """
    curve_bits = ECDSA.PRIME.bit_length()
    times = []

    print(f"\n=== Benchmark signature pour message de longueur {len(message)} ===")

    for i in range(repeat):
        _, t = measure_time(sign_core, message, private_key)
        times.append(t)
        print(f"  Essai {i+1}/{repeat} : {t:.8f} s")

    result = {
        "curve_bits": curve_bits,
        "message_length": len(message),
        "avg_total_time": statistics.mean(times),
        "min_total_time": min(times),
        "max_total_time": max(times),
    }

    print(f"  -> Temps moyen signature : {result['avg_total_time']:.8f} s")

    return result


# ============================================================
# VERIFICATION (réimplémentée sans print)
# ============================================================

def verify_core(message, signature, public_key):
    """
    Version "benchmark" de verify_signature, sans print,
    utilisant safe_hash_elements à la place de ECDSA.hash_elements.
    """
    PRIME = ECDSA.PRIME
    R, s = signature

    # Conversion du message
    if isinstance(message, str):
        message_int = ECDSA.message_to_int(message)
    else:
        message_int = int.from_bytes(message, 'big')

    # Challenge h avec safe_hash_elements
    h = safe_hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME

    # P1 = s * G
    P1 = ECDSA.scalar_multiplication(ECDSA.BASE_POINT, s)

    # P2 = R + h * PublicKey
    h_times_pub = ECDSA.scalar_multiplication(public_key, h)
    P2 = ECDSA.point_addition(R, h_times_pub)

    return (P1[0] == P2[0]) and (P1[1] == P2[1])


def benchmark_verify(message, signature, public_key, repeat=10):
    """
    Mesure le temps de vérification de signature.

    Paramètres :
        message     : string (ou bytes)
        signature   : (R, s)
        public_key  : point (x, y)
        repeat      : nombre de répétitions

    Retourne :
        {
            "curve_bits": taille courbe,
            "message_length": longueur message,
            "avg_total_time": temps moyen,
            "min_total_time": min,
            "max_total_time": max,
        }
    """
    curve_bits = ECDSA.PRIME.bit_length()
    times = []

    print(f"\n=== Benchmark vérification pour message de longueur {len(message)} ===")

    for i in range(repeat):
        (valid, t) = measure_time(verify_core, message, signature, public_key)
        times.append(t)
        print(f"  Essai {i+1}/{repeat} : {t:.8f} s (valide={valid})")

    result = {
        "curve_bits": curve_bits,
        "message_length": len(message),
        "avg_total_time": statistics.mean(times),
        "min_total_time": min(times),
        "max_total_time": max(times),
    }

    print(f"  -> Temps moyen vérification : {result['avg_total_time']:.8f} s")

    return result


# ============================================================
# SAUVEGARDE EN CSV
# ============================================================

def write_csv(filename, header, rows):
    """
    Écrit une liste de dictionnaires dans un fichier CSV.

    filename : nom du fichier
    header   : liste des noms de colonnes
    rows     : liste de dicts avec ces colonnes
    """
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"\n[OK] Résultats sauvegardés dans {filename}")


# ============================================================
# MAIN : LANCER TOUS LES BENCHMARKS
# ============================================================

def main():
    # Tailles de messages à tester
    MESSAGE_SIZES = [10, 50, 100, 500, 1000, 5000]

    BASE_MESSAGE = "Bonjour j'aime les falafels et la crypto ! "

    # Listes pour stocker tous les résultats
    keygen_results = []
    hash_results = []
    sign_results = []
    verify_results = []

    # 1) Benchmark génération de clés
    keygen_res, priv_key, pub_key = benchmark_key_generation(repeat=10)
    keygen_results.append(keygen_res)

    # 2) Pour chaque taille de message, on fait hash + sign + verify
    for L in MESSAGE_SIZES:
        # On fabrique un message de longueur L en répétant BASE_MESSAGE
        message = (BASE_MESSAGE * ((L // len(BASE_MESSAGE)) + 1))[:L]

        # a) Hachage
        h_res = benchmark_hash(message, repeat=10)
        hash_results.append(h_res)

        # b) Signature (on obtient aussi une signature une fois pour la vérif)
        #    On utilise sign_core une fois "hors benchmark" pour générer une signature de référence.
        signature = sign_core(message, priv_key)
        s_res = benchmark_sign(message, priv_key, repeat=10)
        sign_results.append(s_res)

        # c) Vérification
        v_res = benchmark_verify(message, signature, pub_key, repeat=10)
        verify_results.append(v_res)

    # 3) Sauvegarde des résultats dans des CSV
    write_csv(
        "ecdsa_keygen_results.csv",
        ["curve_bits", "avg_time", "min_time", "max_time", "priv_key_bits", "pub_x_bits", "pub_y_bits"],
        keygen_results,
    )

    write_csv(
        "ecdsa_hash_results.csv",
        ["curve_bits", "message_length", "avg_time", "min_time", "max_time"],
        hash_results,
    )

    write_csv(
        "ecdsa_sign_results.csv",
        ["curve_bits", "message_length", "avg_total_time", "min_total_time", "max_total_time"],
        sign_results,
    )

    write_csv(
        "ecdsa_verify_results.csv",
        ["curve_bits", "message_length", "avg_total_time", "min_total_time", "max_total_time"],
        verify_results,
    )

    print("\n=== Benchmarks ECDSA terminés 🎉 ===")


# Point d'entrée
if __name__ == "__main__":
    main()
