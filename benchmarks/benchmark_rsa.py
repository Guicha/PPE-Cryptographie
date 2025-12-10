"""
benchmark_rsa.py

Script pour mesurer les performances de ton implémentation RSA :
- temps de génération des clés
- taille des clés
- temps de hachage (SHA-512)
- temps de signature RSA
- temps de vérification RSA
- impact de la taille des clés (BITS)
- impact de la taille des messages

⚠️ Assure-toi que RSA.py est dans le même dossier que ce fichier.
"""

import time
import csv
import statistics
import RSA  # on importe ton fichier RSA.py comme module


# ============================================================
# PETITE FONCTION UTILE POUR MESURER UN TEMPS D'EXECUTION
# ============================================================

def measure_time(func, *args, **kwargs):
    """
    Mesure le temps d'exécution d'une fonction.
    
    Retourne:
        result : résultat retourné par la fonction
        elapsed : temps écoulé en secondes (float)
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    elapsed = end - start
    return result, elapsed


# ============================================================
# MESURE : GENERATION DES CLES
# ============================================================

def benchmark_key_generation(bits, repeat=3):
    """
    Mesure le temps de génération des clés RSA pour une taille donnée.
    
    Paramètres:
        bits   : taille des nombres premiers p et q (paramètre de creer_cles)
        repeat : nombre de répétitions pour faire une moyenne
        
    Retourne:
        dict avec :
          - bits
          - avg_time (moyenne)
          - min_time / max_time
          - key_size_n_bits (taille de n en bits)
          - key_size_d_bits (taille de d en bits)
          - cle_publique, cle_privee (pour réutiliser)
    """
    times = []
    last_pub = None
    last_priv = None

    print(f"\n=== Benchmark génération de clés pour {bits} bits (p et q) ===")

    for i in range(repeat):
        # On mesure le temps de RSA.creer_cles(bits)
        (cle_publique, cle_privee), t = measure_time(RSA.creer_cles, bits)
        times.append(t)
        last_pub = cle_publique
        last_priv = cle_privee
        print(f"  Essai {i+1}/{repeat} : {t:.4f} s")

    e, n = last_pub
    d, _ = last_priv

    key_size_n_bits = n.bit_length()  # taille du module n en bits
    key_size_d_bits = d.bit_length()  # taille de l'exposant privé d

    result = {
        "bits_param": bits,
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
        "key_size_n_bits": key_size_n_bits,
        "key_size_d_bits": key_size_d_bits,
        "cle_publique": last_pub,
        "cle_privee": last_priv,
    }

    print(f"  -> Temps moyen : {result['avg_time']:.4f} s")
    print(f"  -> Taille de n : {key_size_n_bits} bits")
    print(f"  -> Taille de d : {key_size_d_bits} bits")

    return result


# ============================================================
# MESURE : HACHAGE (SHA-512)
# ============================================================

def benchmark_hash(message, repeat=5):
    """
    Mesure le temps de hachage d'un message avec SHA-512 (RSA.hacher_message).
    
    Paramètres:
        message : string à hacher
        repeat  : nombre de répétitions pour la moyenne
        
    Retourne:
        dict avec :
          - message_length
          - avg_time / min_time / max_time
    """
    times = []
    print(f"\n=== Benchmark hachage pour message de longueur {len(message)} ===")

    for i in range(repeat):
        _, t = measure_time(RSA.hacher_message, message)
        times.append(t)
        print(f"  Essai {i+1}/{repeat} : {t:.6f} s")

    result = {
        "message_length": len(message),
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
    }

    print(f"  -> Temps moyen de hachage : {result['avg_time']:.6f} s")

    return result


# ============================================================
# MESURE : SIGNATURE RSA
# ============================================================

def benchmark_sign(message, cle_privee, repeat=5):
    """
    Mesure le temps de signature RSA, en séparant :
    - le temps de hachage du message
    - le temps de l'exponentiation modulaire (pow(hash, d, n))
    
    Paramètres:
        message    : string à signer
        cle_privee : tuple (d, n)
        repeat     : nombre de répétitions
        
    Retourne:
        dict avec :
          - message_length
          - avg_hash_time, avg_sign_time, avg_total_time
    """
    d, n = cle_privee

    hash_times = []
    sign_times = []
    total_times = []

    print(f"\n=== Benchmark signature pour message de longueur {len(message)} ===")

    for i in range(repeat):
        start_total = time.perf_counter()

        # 1. Hachage
        _, t_hash = measure_time(RSA.hacher_message, message)

        # On re-hache pour récupérer la valeur (on isole les temps pour être clair)
        hash_val = RSA.hacher_message(message)

        # 2. Signature RSA = pow(hash_val, d, n)
        _, t_sign = measure_time(pow, hash_val, d, n)

        end_total = time.perf_counter()
        t_total = end_total - start_total

        hash_times.append(t_hash)
        sign_times.append(t_sign)
        total_times.append(t_total)

        print(f"  Essai {i+1}/{repeat} : hash = {t_hash:.6f}s, RSA = {t_sign:.6f}s, total = {t_total:.6f}s")

    result = {
        "message_length": len(message),
        "avg_hash_time": statistics.mean(hash_times),
        "avg_sign_time": statistics.mean(sign_times),
        "avg_total_time": statistics.mean(total_times),
    }

    print(f"  -> Temps moyen hash   : {result['avg_hash_time']:.6f} s")
    print(f"  -> Temps moyen RSA    : {result['avg_sign_time']:.6f} s")
    print(f"  -> Temps moyen total  : {result['avg_total_time']:.6f} s")

    return result


# ============================================================
# MESURE : VERIFICATION RSA
# ============================================================

def benchmark_verify(message, signature, cle_publique, repeat=5):
    """
    Mesure le temps de vérification RSA, en séparant :
    - le temps de hachage du message
    - le temps de l'exponentiation modulaire (pow(signature, e, n))
    
    Paramètres:
        message     : string original
        signature   : signature du message
        cle_publique: tuple (e, n)
        repeat      : nombre de répétitions
        
    Retourne:
        dict avec :
          - message_length
          - avg_hash_time, avg_verify_time, avg_total_time
    """
    e, n = cle_publique

    hash_times = []
    verify_times = []
    total_times = []

    print(f"\n=== Benchmark vérification pour message de longueur {len(message)} ===")

    for i in range(repeat):
        start_total = time.perf_counter()

        # 1. Hachage
        _, t_hash = measure_time(RSA.hacher_message, message)
        hash_val = RSA.hacher_message(message)

        # 2. Vérification RSA = pow(signature, e, n)
        _, t_verify = measure_time(pow, signature, e, n)

        end_total = time.perf_counter()
        t_total = end_total - start_total

        hash_times.append(t_hash)
        verify_times.append(t_verify)
        total_times.append(t_total)

        print(f"  Essai {i+1}/{repeat} : hash = {t_hash:.6f}s, RSA = {t_verify:.6f}s, total = {t_total:.6f}s")

    result = {
        "message_length": len(message),
        "avg_hash_time": statistics.mean(hash_times),
        "avg_verify_time": statistics.mean(verify_times),
        "avg_total_time": statistics.mean(total_times),
    }

    print(f"  -> Temps moyen hash     : {result['avg_hash_time']:.6f} s")
    print(f"  -> Temps moyen RSA (ver): {result['avg_verify_time']:.6f} s")
    print(f"  -> Temps moyen total    : {result['avg_total_time']:.6f} s")

    return result


# ============================================================
# PETITE FONCTION POUR SAUVEGARDER EN CSV
# ============================================================

def write_csv(filename, header, rows):
    """
    Écrit une liste de dictionnaires dans un fichier CSV.
    
    Paramètres:
        filename : nom du fichier (string)
        header   : liste des noms de colonnes
        rows     : liste de dicts avec ces clés
    """
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"\n[OK] Résultats sauvegardés dans {filename}")


# ============================================================
# FONCTION PRINCIPALE DE BENCHMARK
# ============================================================

def main():
    # ---------- 1. Paramètres globaux de l'expérience ----------
    # Tailles de clés à tester (en bits pour p et q)
    KEY_SIZES = [512, 1024]  # tu peux ajouter 2048, 3072 si ta machine tient le coup

    # Tailles de messages à tester (nombre de caractères)
    MESSAGE_SIZES = [10, 100, 1000, 5000]

    # Message de base, on va juste le répéter
    BASE_MESSAGE = "Bonjour j'aime les falafels! "

    # Listes pour stocker tous les résultats
    keygen_results = []
    hash_results = []
    sign_results = []
    verify_results = []

    # ---------- 2. Benchmarks pour différentes tailles de clé ----------
    for bits in KEY_SIZES:
        # a) Génération des clés
        kg_res = benchmark_key_generation(bits, repeat=3)
        keygen_results.append({
            "bits_param": kg_res["bits_param"],
            "avg_time": kg_res["avg_time"],
            "min_time": kg_res["min_time"],
            "max_time": kg_res["max_time"],
            "key_size_n_bits": kg_res["key_size_n_bits"],
            "key_size_d_bits": kg_res["key_size_d_bits"],
        })

        cle_publique = kg_res["cle_publique"]
        cle_privee = kg_res["cle_privee"]

        # b) On teste plusieurs tailles de messages pour cette taille de clé
        for L in MESSAGE_SIZES:
            message = (BASE_MESSAGE * ((L // len(BASE_MESSAGE)) + 1))[:L]

            # --- Hachage ---
            h_res = benchmark_hash(message, repeat=5)
            hash_results.append({
                "bits_param": bits,
                "message_length": h_res["message_length"],
                "avg_time": h_res["avg_time"],
                "min_time": h_res["min_time"],
                "max_time": h_res["max_time"],
            })

            # --- Signature ---
            # On génère d'abord une signature une fois, pour la partie vérification après
            signature, _ = RSA.signer(message, cle_privee)

            s_res = benchmark_sign(message, cle_privee, repeat=5)
            sign_results.append({
                "bits_param": bits,
                "message_length": s_res["message_length"],
                "avg_hash_time": s_res["avg_hash_time"],
                "avg_sign_time": s_res["avg_sign_time"],
                "avg_total_time": s_res["avg_total_time"],
            })

            # --- Vérification ---
            v_res = benchmark_verify(message, signature, cle_publique, repeat=5)
            verify_results.append({
                "bits_param": bits,
                "message_length": v_res["message_length"],
                "avg_hash_time": v_res["avg_hash_time"],
                "avg_verify_time": v_res["avg_verify_time"],
                "avg_total_time": v_res["avg_total_time"],
            })

    # ---------- 3. Sauvegarde des résultats en CSV ----------
    write_csv(
        "rsa_keygen_results.csv",
        ["bits_param", "avg_time", "min_time", "max_time", "key_size_n_bits", "key_size_d_bits"],
        keygen_results,
    )

    write_csv(
        "rsa_hash_results.csv",
        ["bits_param", "message_length", "avg_time", "min_time", "max_time"],
        hash_results,
    )

    write_csv(
        "rsa_sign_results.csv",
        ["bits_param", "message_length", "avg_hash_time", "avg_sign_time", "avg_total_time"],
        sign_results,
    )

    write_csv(
        "rsa_verify_results.csv",
        ["bits_param", "message_length", "avg_hash_time", "avg_verify_time", "avg_total_time"],
        verify_results,
    )

    print("\n=== Benchmarks terminés 🎉 ===")


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    main()
