import hashlib
import hmac
import secrets
import statistics
import time


# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A = 0
B = 7
Gx = 55066263022277343669578718895168534326250603453777594175500187360389116729240
Gy = 32670510020758816978083085130507043184471273380659243275938904335757337482424
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (Gx, Gy)


def inverse_mod(k, modulus):
    if k % modulus == 0:
        raise ZeroDivisionError("inverse does not exist")
    return pow(k, -1, modulus)


def hash_message_bytes(message):
    if isinstance(message, str):
        message = message.encode("utf-8")
    return hashlib.sha256(message).digest()


def bits2int(data, qlen):
    value = int.from_bytes(data, "big")
    data_bits = len(data) * 8
    if data_bits > qlen:
        value >>= data_bits - qlen
    return value


def hash_message_to_int(message):
    digest = hash_message_bytes(message)
    return bits2int(digest, N.bit_length())


def int2octets(value, octet_len):
    return value.to_bytes(octet_len, "big")


def bits2octets(data):
    qlen = N.bit_length()
    z1 = bits2int(data, qlen)
    z2 = z1 - N
    if z2 < 0:
        z2 = z1
    return int2octets(z2, (qlen + 7) // 8)


def deterministic_nonce_rfc6979(private_key, message):
    """
    RFC 6979 deterministic nonce generation for ECDSA with SHA-256.
    """
    if not (1 <= private_key < N):
        raise ValueError("private key out of range")

    h1 = hash_message_bytes(message)
    qlen = N.bit_length()
    holen = hashlib.sha256().digest_size
    rolen = (qlen + 7) // 8

    bx = int2octets(private_key, rolen)
    bh = bits2octets(h1)

    v = b"\x01" * holen
    k = b"\x00" * holen

    k = hmac.new(k, v + b"\x00" + bx + bh, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b"\x01" + bx + bh, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()

    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        candidate = bits2int(v, qlen)
        if 1 <= candidate < N:
            return candidate

        k = hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def is_on_curve(point):
    if point is None:
        return True
    x, y = point
    return (y * y - (x * x * x + A * x + B)) % P == 0


def point_add(point1, point2):
    if point1 is None:
        return point2
    if point2 is None:
        return point1

    x1, y1 = point1
    x2, y2 = point2

    if x1 == x2 and (y1 + y2) % P == 0:
        return None

    if point1 == point2:
        if y1 % P == 0:
            return None
        slope = ((3 * x1 * x1 + A) * inverse_mod(2 * y1, P)) % P
    else:
        slope = ((y2 - y1) * inverse_mod((x2 - x1) % P, P)) % P

    x3 = (slope * slope - x1 - x2) % P
    y3 = (slope * (x1 - x3) - y1) % P
    return (x3, y3)


def scalar_multiply_ladder(scalar, point, scalar_blinding=False):
    """
    Montgomery-ladder style flow with fixed iteration length.
    Note: Python cannot guarantee true constant time, but this avoids
    the obvious bit-dependent add-vs-no-add pattern from naive double-and-add.
    """
    if point is None:
        return None

    k = scalar % N
    if k == 0:
        return None

    fixed_bits = N.bit_length() + (16 if scalar_blinding else 0)
    if scalar_blinding:
        k += secrets.randbelow(1 << 16) * N

    bitstring = format(k, "0{}b".format(fixed_bits))[-fixed_bits:]

    r0 = None
    r1 = point

    for bit_char in bitstring:
        bit = ord(bit_char) - ord("0")

        add_r0_r1 = point_add(r0, r1)
        dbl_r0 = point_add(r0, r0)
        dbl_r1 = point_add(r1, r1)

        r0 = (dbl_r0, add_r0_r1)[bit]
        r1 = (add_r0_r1, dbl_r1)[bit]

    return r0


def generate_keypair():
    private_key = secrets.randbelow(N - 1) + 1
    public_key = scalar_multiply_ladder(private_key, G, scalar_blinding=True)
    return private_key, public_key


def is_valid_public_key(public_key):
    if public_key is None:
        return False
    if not is_on_curve(public_key):
        return False
    # secp256k1 has cofactor 1; a valid key must satisfy n * Q = O.
    return scalar_multiply_ladder(N, public_key, scalar_blinding=False) is None


def sign_message(message, private_key):
    if not (1 <= private_key < N):
        raise ValueError("private key out of range")

    z = hash_message_to_int(message)

    while True:
        k = deterministic_nonce_rfc6979(private_key, message)
        r_point = scalar_multiply_ladder(k, G, scalar_blinding=True)
        if r_point is None:
            raise RuntimeError("unexpected point at infinity during signing")

        r = r_point[0] % N
        if r == 0:
            raise RuntimeError("rare invalid r=0; retry policy required")

        s = (inverse_mod(k, N) * (z + r * private_key)) % N
        if s == 0:
            raise RuntimeError("rare invalid s=0; retry policy required")

        # Canonical low-s form to reduce malleability.
        if s > N // 2:
            s = N - s

        return (r, s)


def verify_signature(signature, message, public_key):
    if not isinstance(signature, tuple) or len(signature) != 2:
        return False

    r, s = signature
    if not isinstance(r, int) or not isinstance(s, int):
        return False

    # Strict bounds check blocks Psychic-style forged signatures.
    if not (1 <= r < N and 1 <= s < N):
        return False

    if not is_valid_public_key(public_key):
        return False

    z = hash_message_to_int(message)

    try:
        w = inverse_mod(s, N)
    except ZeroDivisionError:
        return False

    u1 = (z * w) % N
    u2 = (r * w) % N

    p1 = scalar_multiply_ladder(u1, G, scalar_blinding=False)
    p2 = scalar_multiply_ladder(u2, public_key, scalar_blinding=False)
    result_point = point_add(p1, p2)

    if result_point is None:
        return False

    return (result_point[0] % N) == r


def leaky_operation_count_for_scalar(scalar):
    bits = bin(scalar)[2:]
    op_count = 0
    for bit in bits[1:]:
        op_count += 1  # Double
        if bit == "1":
            op_count += 1  # Add
    return op_count


def hardened_operation_count_for_scalar(scalar_blinding=False):
    fixed_bits = N.bit_length() + (16 if scalar_blinding else 0)
    # Per bit we compute add_r0_r1, dbl_r0, dbl_r1.
    return fixed_bits * 3


def benchmark_sign_verify(iterations=10):
    private_key, public_key = generate_keypair()
    sign_times = []
    verify_times = []

    for i in range(iterations):
        message = f"msg-{i}-paiement"

        start_sign = time.perf_counter()
        signature = sign_message(message, private_key)
        sign_times.append(time.perf_counter() - start_sign)

        start_verify = time.perf_counter()
        is_valid = verify_signature(signature, message, public_key)
        verify_times.append(time.perf_counter() - start_verify)

        if not is_valid:
            raise RuntimeError("verification failed during benchmark")

    return {
        "avg_sign_s": statistics.mean(sign_times),
        "avg_verify_s": statistics.mean(verify_times),
        "min_sign_s": min(sign_times),
        "max_sign_s": max(sign_times),
        "min_verify_s": min(verify_times),
        "max_verify_s": max(verify_times),
    }


def analyze_improvements():
    print("=== ECDSA HARDENED: ANALYSE DES AMELIORATIONS ===")

    private_key, public_key = generate_keypair()
    base_message = "Virement 500 EUR"
    other_message = "Virement 900 EUR"

    signature = sign_message(base_message, private_key)
    print("Signature valide:", verify_signature(signature, base_message, public_key))

    k1 = deterministic_nonce_rfc6979(private_key, base_message)
    k1_repeat = deterministic_nonce_rfc6979(private_key, base_message)
    k2 = deterministic_nonce_rfc6979(private_key, other_message)

    print("[Fix 1] Nonce deterministic RFC6979 stable sur meme message:", k1 == k1_repeat)
    print("[Fix 1] Nonce differents sur messages differents:", k1 != k2)

    leaky_low_hw = leaky_operation_count_for_scalar(int("10" * 128, 2))
    leaky_high_hw = leaky_operation_count_for_scalar(int("1" * 256, 2))
    hardened_ops = hardened_operation_count_for_scalar(scalar_blinding=True)

    print("[Fix 2] Leaky op count faible Hamming weight:", leaky_low_hw)
    print("[Fix 2] Leaky op count forte Hamming weight:", leaky_high_hw)
    print("[Fix 2] Hardened op count fixe:", hardened_ops)

    forged_signature = (0, 0)
    forged_ok = verify_signature(forged_signature, base_message, public_key)
    print("[Fix 3] Signature forgee (0,0) acceptee:", forged_ok)

    perf = benchmark_sign_verify(iterations=10)
    print("[Perf] Sign avg (s):", round(perf["avg_sign_s"], 6))
    print("[Perf] Verify avg (s):", round(perf["avg_verify_s"], 6))
    print("[Perf] Sign min/max (s):", round(perf["min_sign_s"], 6), round(perf["max_sign_s"], 6))
    print("[Perf] Verify min/max (s):", round(perf["min_verify_s"], 6), round(perf["max_verify_s"], 6))


if __name__ == "__main__":
    analyze_improvements()
