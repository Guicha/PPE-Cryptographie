import random
import statistics
import time

import ecdsa as classic
import ecdsa_hardened as hardened


def benchmark_classic(iterations=10):
    private_key = random.randrange(1, classic.n)
    public_key = classic.g_point.multiply(private_key)

    sign_times = []
    verify_times = []

    for i in range(iterations):
        message = f"classic-msg-{i}"

        t0 = time.perf_counter()
        signature = classic.sign_message(message, private_key)
        sign_times.append(time.perf_counter() - t0)

        t1 = time.perf_counter()
        ok = classic.verify_signature(signature, message, public_key)
        verify_times.append(time.perf_counter() - t1)

        if not ok:
            raise RuntimeError("classic verification failed")

    return {
        "sign_avg": statistics.mean(sign_times),
        "verify_avg": statistics.mean(verify_times),
        "sign_min": min(sign_times),
        "sign_max": max(sign_times),
        "verify_min": min(verify_times),
        "verify_max": max(verify_times),
    }


def benchmark_hardened(iterations=10):
    private_key, public_key = hardened.generate_keypair()

    sign_times = []
    verify_times = []

    for i in range(iterations):
        message = f"hardened-msg-{i}"

        t0 = time.perf_counter()
        signature = hardened.sign_message(message, private_key)
        sign_times.append(time.perf_counter() - t0)

        t1 = time.perf_counter()
        ok = hardened.verify_signature(signature, message, public_key)
        verify_times.append(time.perf_counter() - t1)

        if not ok:
            raise RuntimeError("hardened verification failed")

    return {
        "sign_avg": statistics.mean(sign_times),
        "verify_avg": statistics.mean(verify_times),
        "sign_min": min(sign_times),
        "sign_max": max(sign_times),
        "verify_min": min(verify_times),
        "verify_max": max(verify_times),
    }


def security_comparison():
    message1 = "Paiement A"
    message2 = "Paiement B"

    # Classic: nonce reuse attack should recover key.
    classic_priv = random.randrange(1, classic.n)
    shared_nonce = random.randrange(1, classic.n)
    sig1, _, _ = classic.sign_message_with_nonce(message1, classic_priv, nonce=shared_nonce)
    sig2, _, _ = classic.sign_message_with_nonce(message2, classic_priv, nonce=shared_nonce)
    _, recovered_classic_priv = classic.recover_private_key_from_reused_nonce(sig1, message1, sig2, message2)

    # Classic SPA simulation.
    spa_sig, leaked_nonce, _, trace = classic.sign_message_with_leaky_nonce("SPA", classic_priv)
    recovered_nonce = classic.recover_nonce_from_trace(trace)
    recovered_from_spa = classic.recover_private_key_from_known_nonce(spa_sig, "SPA", recovered_nonce)

    classic_pub = classic.g_point.multiply(classic_priv)
    classic_psychic = classic.verify_signature_no_bounds_buggy((0, 0), "admin", classic_pub)

    # Hardened checks.
    hardened_priv, hardened_pub = hardened.generate_keypair()
    k1 = hardened.deterministic_nonce_rfc6979(hardened_priv, message1)
    k1_repeat = hardened.deterministic_nonce_rfc6979(hardened_priv, message1)
    k2 = hardened.deterministic_nonce_rfc6979(hardened_priv, message2)
    hardened_psychic = hardened.verify_signature((0, 0), "admin", hardened_pub)

    leaky_low_hw = hardened.leaky_operation_count_for_scalar(int("10" * 128, 2))
    leaky_high_hw = hardened.leaky_operation_count_for_scalar(int("1" * 256, 2))
    hardened_fixed_ops = hardened.hardened_operation_count_for_scalar(scalar_blinding=True)

    return {
        "classic_nonce_reuse_private_key_recovered": recovered_classic_priv == classic_priv,
        "classic_spa_nonce_recovered": recovered_nonce == leaked_nonce,
        "classic_spa_private_key_recovered": recovered_from_spa == classic_priv,
        "classic_psychic_signature_accepted": classic_psychic,
        "hardened_nonce_stable_same_message": k1 == k1_repeat,
        "hardened_nonce_diff_different_messages": k1 != k2,
        "hardened_psychic_signature_accepted": hardened_psychic,
        "leaky_ops_low_hw": leaky_low_hw,
        "leaky_ops_high_hw": leaky_high_hw,
        "hardened_fixed_ops": hardened_fixed_ops,
    }


def fmt(sec):
    return f"{sec:.6f}"


def main():
    iterations = 10
    classic_perf = benchmark_classic(iterations)
    hardened_perf = benchmark_hardened(iterations)
    security = security_comparison()

    print("=== COMPARAISON RUN ECDSA CLASSIQUE vs AMELIORE ===")
    print(f"Iterations benchmark: {iterations}")
    print("")
    print("[SECURITE]")
    print("Classic - cle privee retrouvee via nonce reuse:", security["classic_nonce_reuse_private_key_recovered"])
    print("Classic - nonce reconstruit via SPA:", security["classic_spa_nonce_recovered"])
    print("Classic - cle privee retrouvee via SPA:", security["classic_spa_private_key_recovered"])
    print("Classic - signature forgee (0,0) acceptee en mode vulnerable:", security["classic_psychic_signature_accepted"])
    print("Hardened - nonce RFC6979 stable sur meme message:", security["hardened_nonce_stable_same_message"])
    print("Hardened - nonce RFC6979 different sur messages differents:", security["hardened_nonce_diff_different_messages"])
    print("Hardened - signature forgee (0,0) acceptee:", security["hardened_psychic_signature_accepted"])
    print("")
    print("[SIDE-CHANNEL OP PROFILE]")
    print("Leaky ops faible Hamming weight:", security["leaky_ops_low_hw"])
    print("Leaky ops forte Hamming weight:", security["leaky_ops_high_hw"])
    print("Hardened ops fixes:", security["hardened_fixed_ops"])
    print("")
    print("[PERFORMANCE]")
    print("Classic sign avg (s):", fmt(classic_perf["sign_avg"]))
    print("Classic verify avg (s):", fmt(classic_perf["verify_avg"]))
    print("Hardened sign avg (s):", fmt(hardened_perf["sign_avg"]))
    print("Hardened verify avg (s):", fmt(hardened_perf["verify_avg"]))

    sign_overhead = hardened_perf["sign_avg"] / classic_perf["sign_avg"]
    verify_overhead = hardened_perf["verify_avg"] / classic_perf["verify_avg"]

    print("Sign overhead hardened/classic:", f"{sign_overhead:.2f}x")
    print("Verify overhead hardened/classic:", f"{verify_overhead:.2f}x")


if __name__ == "__main__":
    main()
