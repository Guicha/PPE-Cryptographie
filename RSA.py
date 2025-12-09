import random
import hashlib
import time

# ============================================================
# PARAMÈTRES RSA
# ============================================================

# Taille des nombres premiers (en bits)
# MODIFIABLE : 16 bits minimum pour les tests, la taille de la clé privé doit être au moins 3072 bits, ce qui est la recommandation minimale actuelle pour la sécurité RSA (Donc 1536 bits pour p et q)
BITS = 1536

# ============================================================
# FONCTIONS MATHEMATIQUES
# ============================================================

def est_premier(n, k=5):
    """
    Test de primalité de Miller-Rabin
    FONCTION IMMUABLE : Algorithme probabiliste standard
    
    Paramètres:
        n : VARIABLE - Nombre à tester
        k : VARIABLE - Nombre d'itérations (plus k est grand, plus c'est précis)
    
    Retourne: True si n est probablement premier, False sinon
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False
    
    # Écrire n-1 comme 2^r * d
    # IMMUABLE : Décomposition nécessaire pour Miller-Rabin
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    
    # Test de Miller-Rabin
    # IMMUABLE : Algorithme mathématique prouvé
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



def generer_nombre_premier(bits=16):
    """
    Génère un nombre premier aléatoire de la taille spécifiée
    
    Paramètres:
        bits : VARIABLE - Nombre de bits du nombre premier (16 pour tests, 2048+ en production)
    
    Retourne: Un nombre premier de 'bits' bits
    """
    while True:
        # Générer un nombre aléatoire dans l'intervalle [2^(bits-1), 2^bits)
        # MODIFIABLE : Méthode de génération aléatoire
        n = random.randrange(2**(bits-1), 2**bits)
        if est_premier(n):
            return n



def pgcd(a, b):
    """
    Calcule le plus grand commun diviseur (PGCD)
    FONCTION IMMUABLE : Algorithme d'Euclide classique
    
    Paramètres:
        a, b : VARIABLES - Les deux nombres
    
    Retourne: pgcd(a, b)
    """
    while b:
        a, b = b, a % b
    return a



def inverse_modulaire(e, phi):
    """
    Calcule l'inverse modulaire de e modulo phi
    FONCTION IMMUABLE : Algorithme d'Euclide étendu
    
    Paramètres:
        e : VARIABLE - Nombre dont on cherche l'inverse
        phi : VARIABLE - Module
    
    Retourne: d tel que (e * d) mod phi = 1
    """
    def euclide_etendu(a, b):
        """
        Algorithme d'Euclide étendu
        IMMUABLE : Algorithme mathématique standard
        """
        if a == 0:
            return b, 0, 1
        pgcd, x1, y1 = euclide_etendu(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return pgcd, x, y
    
    _, x, _ = euclide_etendu(e, phi)
    return x % phi



# ============================================================
# GENERATION DES CLES
# ============================================================

def creer_cles(bits):
    """
    Génère une paire de clés RSA (publique, privée) et mesure le temps.
    
    Paramètres:
        bits : VARIABLE - Taille des nombres premiers en bits
    
    Retourne:
        cle_publique : VARIABLE PUBLIQUE - Tuple (e, n)
        cle_privee : VARIABLE SECRÈTE - Tuple (d, n)
        duration : Temps de génération en secondes
    """
    start_time = time.perf_counter()
    
    # Étape 1 : Générer deux nombres premiers distincts p et q
    # IMPORTANT : p et q doivent être gardés secrets
    p = generer_nombre_premier(bits)
    q = generer_nombre_premier(bits)
    
    # Assurer que p ≠ q
    # IMMUABLE : Contrainte de sécurité RSA
    while p == q:
        q = generer_nombre_premier(bits)
    
    print(f"p = {p}")
    print(f"q = {q}")
    
    # Étape 2 : Calculer n = p × q (module RSA)
    # IMMUABLE : Fondamental pour RSA
    n = p * q
    print(f"n = p × q = {n}")
    
    # Étape 3 : Calculer φ(n) = (p-1)(q-1) (indicatrice d'Euler)
    # IMMUABLE : Formule mathématique pour la fonction d'Euler
    phi = (p - 1) * (q - 1)
    print(f"φ(n) = {phi}")
    
    # Étape 4 : Choisir e (exposant public)
    # MODIFIABLE : 65537 est standard, mais tout nombre premier avec pgcd(e, φ(n)) = 1 fonctionne
    e = 65537
    if e >= phi or pgcd(e, phi) != 1:
        e = random.randrange(2, phi)
        while pgcd(e, phi) != 1:
            e = random.randrange(2, phi)
    
    print(f"e = {e}")
    
    # Étape 5 : Calculer d (exposant privé)
    # IMMUABLE : d est l'inverse modulaire de e modulo φ(n)
    # Propriété : (e × d) mod φ(n) = 1
    d = inverse_modulaire(e, phi)
    print(f"d = {d}")
    
    # Construction des clés
    cle_publique = (e, n)
    cle_privee = (d, n)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    print(f"\nClé publique : {cle_publique}")
    print(f"Clé privée : {cle_privee}")
    print(f"Taille de la clé (n) : {n.bit_length()} bits\n")
    
    return cle_publique, cle_privee, duration



# ============================================================
# SIGNATURE RSA
# ============================================================

def hacher_message(message):
    """
    Hache un message avec SHA-512
    SEMI-MODIFIABLE : SHA-512 est recommandé pour RSA
    
    Paramètres:
        message : VARIABLE - Le message à hacher (string)
    
    Retourne: Hash du message en tant qu'entier
    """
    # IMMUABLE pour signature RSA sécurisée : Utiliser une fonction de hash cryptographique
    # SHA-512 est recommandé pour RSA (peut aussi utiliser SHA-256 ou SHA-3)
    hasher = hashlib.sha512()
    
    # Encoder le message en bytes
    if isinstance(message, str):
        message_bytes = message.encode('utf-8')
    else:
        message_bytes = message
    
    hasher.update(message_bytes)
    
    # Convertir le hash hexadécimal en entier
    hash_hex = hasher.hexdigest()
    hash_val = int(hash_hex, 16)
    
    return hash_val



def signer(message, cle_privee):
    """
    Signe un message avec la clé privée RSA et mesure le temps.
    
    Paramètres:
        message : VARIABLE - Le message à signer (string)
        cle_privee : VARIABLE SECRÈTE - Tuple (d, n) où d est l'exposant privé
    
    Retourne:
        signature : VARIABLE PUBLIQUE - La signature du message
        hash_message : Le hash pour vérification
        duration : Temps de signature en secondes
    """
    start_time = time.perf_counter()
    
    d, n = cle_privee
    
    print(f"Message à signer : '{message}'\n")
    
    # Étape 1 : Hacher le message avec SHA-512
    # IMMUABLE : On ne signe jamais directement le message, toujours son hash
    hash_message = hacher_message(message)
    print(f"Hash du message : {hash_message}\n")
    
    # Si n est trop petit (pour les tests), réduire le hash
    if hash_message >= n:
        hash_message = hash_message % n
        print(f"Hash réduit mod n (test avec petites clés) : {hash_message}\n")
    
    # Étape 2 : Signer le hash avec la clé privée (d, n)
    # IMMUABLE : Formule signature = hash^d mod n
    # C'est l'inverse du chiffrement : on utilise la clé PRIVÉE pour "chiffrer"
    signature = pow(hash_message, d, n)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    print(f"Signature générée : {signature}")
    print(f"Taille de la signature : {signature.bit_length()} bits\n")
    
    return signature, hash_message, duration



def verifier(message, signature, cle_publique):
    """
    Vérifie la signature d'un message avec la clé publique RSA et mesure le temps.
    
    Paramètres:
        message : VARIABLE - Le message signé (string)
        signature : VARIABLE PUBLIQUE - La signature à vérifier
        cle_publique : VARIABLE PUBLIQUE - Tuple (e, n) où e est l'exposant public
    
    Retourne:
        is_valid : bool - True si la signature est valide, False sinon
        duration : Temps de vérification en secondes
    """
    start_time = time.perf_counter()
    
    e, n = cle_publique
    
    print(f"Message reçu : '{message}'")
    print(f"Signature reçue : {signature}\n")
    
    # Étape 1 : Hacher le message reçu avec SHA-512
    # IMMUABLE : Doit utiliser la même fonction de hash que pour signer
    hash_message = hacher_message(message)
    print(f"Hash SHA-512 du message reçu : {hash_message}\n")
    
    # Si n est trop petit (pour les tests), réduire le hash
    if hash_message >= n:
        hash_message = hash_message % n
        print(f"Hash réduit mod n (test avec petites clés) : {hash_message}\n")
    
    # Étape 2 : "Déchiffrer" la signature avec la clé publique (e, n)
    # IMMUABLE : Formule hash_déchiffré = signature^e mod n
    # On utilise la clé PUBLIQUE pour "déchiffrer" ce qui a été signé avec la clé privée
    hash_dechiffre = pow(signature, e, n)
    print(f"Hash déchiffré de la signature : {hash_dechiffre}\n")
    
    # Étape 3 : Comparer les deux hash
    # IMMUABLE : Si les hash correspondent, la signature est valide
    # Cela prouve que :
    #   1. Le message n'a pas été modifié (intégrité)
    #   2. La signature provient bien du détenteur de la clé privée (authenticité)
    is_valid = (hash_message == hash_dechiffre)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    if is_valid:
        print("SIGNATURE VALIDE :)\n")
    else:
        print("SIGNATURE INVALIDE :(\n")
    
    return is_valid, duration





# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def main(message):
    """
    Démontre le processus complet de signature RSA avec mesures de performance.
    
    Paramètres:
        message : VARIABLE - Le message à signer
    """

    print("=" * 60)
    print("        CREATION DES CLES PUBLIQUE ET PRIVEE")
    print("=" * 60 + "\n")

    # Étape 1 : Créer les clés RSA
    # La clé publique sera partagée avec tout le monde
    # La clé privée doit rester SECRÈTE
    cle_publique, cle_privee, gen_time = creer_cles(bits=BITS)
    
    print("=" * 60)
    print("               SIGNATURE DU MESSAGE")
    print("=" * 60 + "\n")
    
    # Étape 2 : Signer le message avec la clé privée
    # Seul le propriétaire de la clé privée peut créer cette signature
    signature, hash_original, sign_time = signer(message, cle_privee)
    
    print("=" * 60)
    print("            VERIFICATION DE LA SIGNATURE")
    print("=" * 60 + "\n")
    
    # Étape 3 : Vérifier la signature avec la clé publique
    # N'importe qui peut vérifier l'authenticité du message
    is_valid, verify_time = verifier(message, signature, cle_publique)
    
    # Étape 4 : Test avec un message modifié
    # Démontre que la signature échoue si le message est altéré
    print("=" * 60)
    print("      TEST AVEC UN MESSAGE MODIFIE")
    print("=" * 60 + "\n")
    
    message_modifie = "Envoie 5000 euros à ce compte : FR76 9876 5432 1098 7654 3210 987, c'est le compte de Parfait Junior."
    verifier(message_modifie, signature, cle_publique)
    
    # ============================================================
    # RÉSUMÉ DES PERFORMANCES
    # ============================================================
    print("=" * 60)
    print("         RÉSULTATS DES MESURES DE PERFORMANCE")
    print("=" * 60 + "\n")
    
    e, n = cle_publique
    d, _ = cle_privee
    
    print(f"Algorithme              : RSA")
    print(f"Taille des premiers (p,q): {BITS} bits chacun")
    print(f"Taille de la clé (n)    : {n.bit_length()} bits")
    print(f"Taille clé privée (d)   : {d.bit_length()} bits")
    print(f"Temps de génération     : {gen_time:.6f} secondes")
    print(f"Temps de signature      : {sign_time:.6f} secondes")
    print(f"Temps de vérification   : {verify_time:.6f} secondes")
    print(f"Validité de la signature: {'VALIDE' if is_valid else 'INVALIDE'}")
    print("=" * 60)
    


if __name__ == "__main__":
    main(message="Envoie 500 euros à ce compte : FR76 1234 5678 9012 3456 7890 123, c'est le compte de Guy-Charbel.")