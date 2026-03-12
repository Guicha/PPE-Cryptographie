"""
ECDSA Engine - Wrapper autour du module ecdsa.py original
Supprime les prints pour une intégration propre dans l'API
"""
import random
import hashlib
import time

# ============================================================
# PARAMETRES DE LA COURBE Ed25519
# ============================================================

PRIME = pow(2, 255) - 19

BASE_POINT_X = 15112221349535400772501151409588531511454012693041857206046113283949847762202
BASE_POINT_Y = 46316835694926478169428394003475163141307993866256225615783033603165251855960
BASE_POINT = (BASE_POINT_X, BASE_POINT_Y)

A = -1

D_NUMERATOR = -121665
D_DENOMINATOR = 121666


def _mod_inverse_init(a, m):
    if a < 0:
        a = (a % m + m) % m
    u1, u2, u3 = 1, 0, a
    v1, v2, v3 = 0, 1, m
    while v3 != 0:
        q = u3 // v3
        v1, v2, v3, u1, u2, u3 = (u1 - q*v1), (u2 - q*v2), (u3 - q*v3), v1, v2, v3
    return u1 % m


D = (D_NUMERATOR * _mod_inverse_init(D_DENOMINATOR, PRIME)) % PRIME


# ============================================================
# FONCTIONS MATHEMATIQUES
# ============================================================

def mod_inverse(a, m):
    if a < 0:
        a = (a % m + m) % m
    u1, u2, u3 = 1, 0, a
    v1, v2, v3 = 0, 1, m
    while v3 != 0:
        q = u3 // v3
        v1, v2, v3, u1, u2, u3 = (u1 - q*v1), (u2 - q*v2), (u3 - q*v3), v1, v2, v3
    return u1 % m


def gcd(a, b):
    while a != 0:
        a, b = b % a, a
    return b


def message_to_int(message):
    if isinstance(message, str):
        message_bytes = message.encode('utf-8')
    else:
        message_bytes = message
    return int(message_bytes.hex(), 16)


def hash_elements(*elements):
    hasher = hashlib.sha512()
    for element in elements:
        hasher.update(str(element).encode('utf-8'))
    return int(hasher.hexdigest(), 16)


# ============================================================
# OPERATIONS SUR LA COURBE
# ============================================================

def point_addition(point1, point2):
    x1, y1 = point1
    x2, y2 = point2

    x3_num = (x1 * y2 + y1 * x2) % PRIME
    x3_den = (1 + D * x1 * x2 * y1 * y2) % PRIME
    y3_num = (y1 * y2 - A * x1 * x2) % PRIME
    y3_den = (1 - D * x1 * x2 * y1 * y2) % PRIME

    x3 = (x3_num * mod_inverse(x3_den, PRIME)) % PRIME
    y3 = (y3_num * mod_inverse(y3_den, PRIME)) % PRIME

    return (x3, y3)


def scalar_multiplication(point, scalar):
    if scalar == 0:
        return (0, 1)
    if scalar == 1:
        return point

    binary = bin(scalar)[2:]
    result = point

    for bit in binary[1:]:
        result = point_addition(result, result)
        if bit == '1':
            result = point_addition(result, point)

    return result


# ============================================================
# GENERATION DES CLES
# ============================================================

def generate_keypair():
    """
    Génère une paire de clés ECC.
    Retourne (private_key, public_key, metadata)
    """
    t_start = time.perf_counter()

    private_key = random.getrandbits(256)
    private_key = private_key % (PRIME - 1) + 1
    public_key = scalar_multiplication(BASE_POINT, private_key)

    t_end = time.perf_counter()
    keygen_time = (t_end - t_start) * 1000

    metadata = {
        "curve": "Ed25519",
        "bits": 256,
        "keygen_time_ms": keygen_time,
        "security_bits": 128,
    }

    return private_key, public_key, metadata


# ============================================================
# SIGNATURE / VERIFICATION
# ============================================================

def sign_message(message, private_key):
    """
    Signe un message. Retourne (signature, temps_ms)
    """
    t_start = time.perf_counter()

    if isinstance(message, str):
        message_int = message_to_int(message)
    else:
        message_int = int.from_bytes(message, 'big')

    r_seed = hash_elements(message_int, private_key, "nonce")
    r = r_seed % (PRIME - 1) + 1

    R = scalar_multiplication(BASE_POINT, r)
    public_key = scalar_multiplication(BASE_POINT, private_key)

    h = hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME
    s = r + h * private_key

    t_end = time.perf_counter()
    sign_time = (t_end - t_start) * 1000

    return (R, s), sign_time


def verify_signature(message, signature, public_key):
    """
    Vérifie une signature. Retourne (bool, temps_ms)
    """
    t_start = time.perf_counter()

    R, s = signature

    if isinstance(message, str):
        message_int = message_to_int(message)
    else:
        message_int = int.from_bytes(message, 'big')

    h = hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME

    P1 = scalar_multiplication(BASE_POINT, s)
    h_times_pub = scalar_multiplication(public_key, h)
    P2 = point_addition(R, h_times_pub)

    is_valid = (P1[0] == P2[0]) and (P1[1] == P2[1])

    t_end = time.perf_counter()
    verify_time = (t_end - t_start) * 1000

    return is_valid, verify_time
