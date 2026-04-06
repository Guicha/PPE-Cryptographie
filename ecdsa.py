import hashlib
import random


def find_inverse(number, modulus):
    return pow(number, -1, modulus)


def find_inverse_buggy(number, modulus):
    # Vulnerable behavior: incorrect inverse(0) handling used by some buggy implementations.
    if number % modulus == 0:
        return 0
    return pow(number, -1, modulus)


def hash_message(message):
    if isinstance(message, str):
        message = message.encode("utf-8")
    return int(hashlib.sha256(message).hexdigest(), 16)


class Point:
    def __init__(self, x, y, curve_config):
        a = curve_config["a"]
        b = curve_config["b"]
        p = curve_config["p"]

        if (y ** 2) % p != (x ** 3 + a * x + b) % p:
            raise Exception("The point is not on the curve")

        self.x = x
        self.y = y
        self.curve_config = curve_config

    def is_equal_to(self, point):
        return self.x == point.x and self.y == point.y

    def add(self, point):
        p = self.curve_config["p"]

        if self.is_equal_to(point):
            slope = (3 * point.x ** 2) * find_inverse(2 * point.y, p) % p
        else:
            slope = (point.y - self.y) * find_inverse(point.x - self.x, p) % p

        x = (slope ** 2 - point.x - self.x) % p
        y = (slope * (self.x - x) - self.y) % p
        return Point(x, y, self.curve_config)

    def multiply(self, times):
        current_point = self
        current_coefficient = 1

        previous_points = []
        while current_coefficient < times:
            previous_points.append((current_coefficient, current_point))
            if 2 * current_coefficient <= times:
                current_point = current_point.add(current_point)
                current_coefficient = 2 * current_coefficient
            else:
                next_point = self
                next_coefficient = 1
                for previous_coefficient, previous_point in previous_points:
                    if previous_coefficient + current_coefficient <= times:
                        if previous_point.x != current_point.x:
                            next_coefficient = previous_coefficient
                            next_point = previous_point
                current_point = current_point.add(next_point)
                current_coefficient = current_coefficient + next_coefficient

        return current_point


secp256k1_curve_config = {
    "a": 0,
    "b": 7,
    "p": 115792089237316195423570985008687907853269984665640564039457584007908834671663,
}
x = 55066263022277343669578718895168534326250603453777594175500187360389116729240
y = 32670510020758816978083085130507043184471273380659243275938904335757337482424
n = 115792089237316195423570985008687907852837564279074904382605163141518161494337
g_point = Point(x, y, secp256k1_curve_config)


def scalar_multiply_with_trace(base_point, scalar):
    """
    Leaky scalar multiplication for SPA demo.
    Trace uses:
      - 'D' for doubling
      - 'A' for addition
    For a left-to-right double-and-add routine, each bit always does one D,
    and bit=1 adds an extra A.
    """
    if scalar <= 0:
        raise ValueError("scalar must be >= 1")

    bits = bin(scalar)[2:]
    result = base_point
    trace = []

    for bit in bits[1:]:
        result = result.add(result)
        trace.append("D")
        if bit == "1":
            result = result.add(base_point)
            trace.append("A")

    return result, trace


def recover_nonce_from_trace(trace):
    if not trace:
        return 1

    bits = ["1"]
    index = 0
    while index < len(trace):
        if trace[index] != "D":
            raise ValueError("invalid trace format")

        bit = "0"
        if index + 1 < len(trace) and trace[index + 1] == "A":
            bit = "1"
            index += 2
        else:
            index += 1
        bits.append(bit)

    return int("".join(bits), 2)


def sign_message_with_nonce(message, private_key, nonce=None):
    z = hash_message(message)

    if nonce is None:
        k = random.randrange(1, n)
    else:
        k = nonce % n
        if k == 0:
            raise ValueError("nonce must be in [1, n-1]")

    r_point = g_point.multiply(k)
    r = r_point.x % n
    if r == 0:
        raise ValueError("invalid nonce produced r=0")

    k_inverse = find_inverse(k, n)
    s = (k_inverse * (z + r * private_key)) % n
    if s == 0:
        raise ValueError("invalid nonce produced s=0")

    return (r, s), k, z


def sign_message_with_leaky_nonce(message, private_key, nonce=None):
    z = hash_message(message)

    if nonce is None:
        k = random.randrange(1, n)
    else:
        k = nonce % n
        if k == 0:
            raise ValueError("nonce must be in [1, n-1]")

    r_point, trace = scalar_multiply_with_trace(g_point, k)
    r = r_point.x % n
    if r == 0:
        raise ValueError("invalid nonce produced r=0")

    k_inverse = find_inverse(k, n)
    s = (k_inverse * (z + r * private_key)) % n
    if s == 0:
        raise ValueError("invalid nonce produced s=0")

    return (r, s), k, z, trace


def sign_message(message, private_key):
    signature, _, _ = sign_message_with_nonce(message, private_key)
    return signature


def verify_signature(signature, message, public_key):
    """Secure verifier: enforces bounds before any modular inverse."""
    r, s = signature

    if not (1 <= r < n and 1 <= s < n):
        return False

    z = hash_message(message)
    s_inverse = find_inverse(s, n)
    u = (z * s_inverse) % n
    v = (r * s_inverse) % n

    points = []
    if u != 0:
        points.append(g_point.multiply(u))
    if v != 0:
        points.append(public_key.multiply(v))

    if not points:
        return False

    c_point = points[0]
    if len(points) == 2:
        c_point = c_point.add(points[1])

    return (c_point.x % n) == r


def verify_signature_no_bounds_buggy(signature, message, public_key):
    """
    Vulnerable verifier for demo only:
      - no bounds check for r,s
      - inverse(0) silently mapped to 0
      - treats (u,v)=(0,0) as x=0 (bad point-at-infinity handling)
    This reproduces the logic behind "Psychic Signatures" style bypasses.
    """
    r, s = signature

    z = hash_message(message)
    s_inverse = find_inverse_buggy(s, n)
    u = (z * s_inverse) % n
    v = (r * s_inverse) % n

    if u == 0 and v == 0:
        computed_x = 0
    else:
        points = []
        if u != 0:
            points.append(g_point.multiply(u))
        if v != 0:
            points.append(public_key.multiply(v))

        if not points:
            computed_x = 0
        else:
            c_point = points[0]
            if len(points) == 2:
                c_point = c_point.add(points[1])
            computed_x = c_point.x % n

    return computed_x == r


def recover_private_key_from_reused_nonce(sig1, msg1, sig2, msg2):
    r1, s1 = sig1
    r2, s2 = sig2
    if r1 != r2:
        raise ValueError("signatures must reuse the same nonce => same r")

    z1 = hash_message(msg1)
    z2 = hash_message(msg2)

    k = ((z1 - z2) * find_inverse((s1 - s2) % n, n)) % n
    private_key = (((s1 * k) - z1) * find_inverse(r1, n)) % n
    return k, private_key


def recover_private_key_from_known_nonce(signature, message, known_nonce):
    r, s = signature
    z = hash_message(message)
    return (((s * known_nonce) - z) * find_inverse(r, n)) % n


def scenario_nonce_reuse_attack():
    print("\n=== SCENARIO 1: Reutilisation du nonce ===")
    private_key = random.randrange(1, n)
    public_key = g_point.multiply(private_key)

    message_1 = "Paiement: Alice -> Bob : 500 EUR"
    message_2 = "Paiement: Alice -> Bob : 900 EUR"

    shared_nonce = random.randrange(1, n)
    sig1, _, _ = sign_message_with_nonce(message_1, private_key, nonce=shared_nonce)
    sig2, _, _ = sign_message_with_nonce(message_2, private_key, nonce=shared_nonce)

    recovered_nonce, recovered_private_key = recover_private_key_from_reused_nonce(
        sig1, message_1, sig2, message_2
    )

    print("Signature 1:", sig1)
    print("Signature 2:", sig2)
    print("Meme r entre les deux signatures:", sig1[0] == sig2[0])
    print("Nonce retrouve correct:", recovered_nonce == shared_nonce)
    print("Cle privee retrouvee:", recovered_private_key == private_key)
    print("Verification legitime apres attaque:", verify_signature(sig1, message_1, public_key))


def scenario_side_channel_spa_attack():
    print("\n=== SCENARIO 2: Canal auxiliaire SPA (simulation) ===")
    private_key = random.randrange(1, n)

    message = "Autorisation virement 2500 EUR"
    signature, leaked_nonce, _, trace = sign_message_with_leaky_nonce(message, private_key)

    recovered_nonce = recover_nonce_from_trace(trace)
    recovered_private_key = recover_private_key_from_known_nonce(
        signature, message, recovered_nonce
    )

    trace_preview = "".join(trace[:40])

    print("Longueur trace (ops):", len(trace))
    print("Apercu trace (40 premieres ops):", trace_preview)
    print("Nonce reconstruit depuis trace:", recovered_nonce == leaked_nonce)
    print("Cle privee retrouvee depuis nonce expose:", recovered_private_key == private_key)


def scenario_missing_bounds_attack():
    print("\n=== SCENARIO 3: Omission des bornes (Psychic-style) ===")
    private_key = random.randrange(1, n)
    public_key = g_point.multiply(private_key)

    forged_signature = (0, 0)
    message = "Connexion admin"

    vulnerable_accepts = verify_signature_no_bounds_buggy(
        forged_signature, message, public_key
    )
    secure_accepts = verify_signature(forged_signature, message, public_key)

    print("Signature forgee:", forged_signature)
    print("Verifier vulnerable accepte (attendu=True):", vulnerable_accepts)
    print("Verifier strict accepte (attendu=False):", secure_accepts)


if __name__ == "__main__":
    scenario_nonce_reuse_attack()
    scenario_side_channel_spa_attack()
    scenario_missing_bounds_attack()
