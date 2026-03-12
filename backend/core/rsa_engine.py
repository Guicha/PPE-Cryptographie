"""
RSA Engine - Wrapper autour du module RSA.py original
Supprime les prints pour une intégration propre dans l'API
"""
import random
import hashlib
import time


# ============================================================
# FONCTIONS MATHEMATIQUES
# ============================================================

def est_premier(n, k=5):
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generer_nombre_premier(bits=512):
    while True:
        n = random.randrange(2**(bits-1), 2**bits)
        if est_premier(n):
            return n


def pgcd(a, b):
    while b:
        a, b = b, a % b
    return a


def inverse_modulaire(e, phi):
    def euclide_etendu(a, b):
        if a == 0:
            return b, 0, 1
        g, x1, y1 = euclide_etendu(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return g, x, y
    _, x, _ = euclide_etendu(e, phi)
    return x % phi


# ============================================================
# GENERATION DES CLES
# ============================================================

def creer_cles(bits=2048):
    """
    Génère une paire de clés RSA.
    Retourne (cle_publique, cle_privee, metadata)
    """
    t_start = time.perf_counter()

    p = generer_nombre_premier(bits)
    q = generer_nombre_premier(bits)
    while p == q:
        q = generer_nombre_premier(bits)

    n = p * q
    phi = (p - 1) * (q - 1)

    e = 65537
    if e >= phi or pgcd(e, phi) != 1:
        e = random.randrange(2, phi)
        while pgcd(e, phi) != 1:
            e = random.randrange(2, phi)

    d = inverse_modulaire(e, phi)

    cle_publique = (e, n)
    cle_privee = (d, n)

    t_end = time.perf_counter()
    keygen_time = (t_end - t_start) * 1000  # ms

    metadata = {
        "bits": bits * 2,  # module n = 2 * bits
        "keygen_time_ms": keygen_time,
        "e": e,
        "n_bits": n.bit_length(),
    }

    return cle_publique, cle_privee, metadata


# ============================================================
# SIGNATURE / VERIFICATION
# ============================================================

def hacher_message(message):
    hasher = hashlib.sha512()
    if isinstance(message, str):
        message_bytes = message.encode('utf-8')
    else:
        message_bytes = message
    hasher.update(message_bytes)
    return int(hasher.hexdigest(), 16)


def signer(message, cle_privee):
    """
    Signe un message. Retourne (signature, hash_message, temps_ms)
    """
    d, n = cle_privee
    t_start = time.perf_counter()

    hash_message = hacher_message(message)
    # Réduction du hash modulo n pour compatibilité
    hash_reduit = hash_message % n
    signature = pow(hash_reduit, d, n)

    t_end = time.perf_counter()
    sign_time = (t_end - t_start) * 1000

    return signature, hash_message, sign_time


def verifier(message, signature, cle_publique):
    """
    Vérifie une signature. Retourne (bool, temps_ms)
    """
    e, n = cle_publique
    t_start = time.perf_counter()

    hash_message = hacher_message(message)
    hash_reduit = hash_message % n
    hash_dechiffre = pow(signature, e, n)

    is_valid = (hash_reduit == hash_dechiffre)

    t_end = time.perf_counter()
    verify_time = (t_end - t_start) * 1000

    return is_valid, verify_time
