import random
import hashlib
import time

# ============================================================
# PARAMÈTRES DE LA COURBE Ed25519
# ============================================================

PRIME = pow(2, 255) - 19
A = -1
D_NUMERATOR = -121665
D_DENOMINATOR = 121666
D = (D_NUMERATOR * pow(D_DENOMINATOR, -1, PRIME)) % PRIME

BASE_POINT_X = 15112221349535400772501151409588531511454012693041857206046113283949847762202
BASE_POINT_Y = 46316835694926478169428394003475163141307993866256225615783033603165251855960

# Point de base en coordonnées projectives étendues (X, Y, Z, T)
# x = X/Z, y = Y/Z, xy = T/Z
# Pour le point de base, Z=1, donc X=x, Y=y, T=x*y
BASE_POINT_PROJ = (
    BASE_POINT_X,
    BASE_POINT_Y,
    1,
    (BASE_POINT_X * BASE_POINT_Y) % PRIME
)

print("=== CONFIGURATION DE LA COURBE Ed25519 (OPTIMISÉE) ===")
print(f"Module p (255 bits) : {PRIME}")
print("Utilisation des coordonnées projectives étendues pour la performance.")
print("=" * 50)

# ============================================================
# FONCTIONS MATHEMATIQUES & UTILITAIRES
# ============================================================

def message_to_int(message):
    """Convertit un message en entier."""
    if isinstance(message, str):
        message_bytes = message.encode('utf-8')
    else:
        message_bytes = message
    return int.from_bytes(message_bytes, 'big')

def hash_elements(*elements):
    """Hache une série d'éléments avec SHA-512."""
    hasher = hashlib.sha512()
    for element in elements:
        hasher.update(str(element).encode('utf-8'))
    return int(hasher.hexdigest(), 16)

# ============================================================
# ARITHMETIQUE PROJECTIVE (OPTIMISATION)
# ============================================================

def point_add_projective(P1, P2):
    """
    Addition de points en coordonnées projectives étendues (X:Y:Z:T).
    Cette implémentation évite les inversions modulaires coûteuses.
    """
    X1, Y1, Z1, T1 = P1
    X2, Y2, Z2, T2 = P2
    
    A = ((Y1 - X1) * (Y2 - X2)) % PRIME
    B = ((Y1 + X1) * (Y2 + X2)) % PRIME
    C = (T1 * 2 * D * T2) % PRIME
    D_val = (2 * Z1 * Z2) % PRIME
    
    E = (B - A) % PRIME
    F = (D_val - C) % PRIME
    G = (D_val + C) % PRIME
    H = (B + A) % PRIME
    
    X3 = (E * F) % PRIME
    Y3 = (G * H) % PRIME
    T3 = (E * H) % PRIME
    Z3 = (F * G) % PRIME
    
    return (X3, Y3, Z3, T3)

def point_double_projective(P):
    """
    Doublement de point en coordonnées projectives étendues.
    Plus rapide que l'addition générique.
    """
    X1, Y1, Z1, T1 = P
    
    A = (X1 * X1) % PRIME
    B = (Y1 * Y1) % PRIME
    C = (2 * Z1 * Z1) % PRIME
    # a = -1, donc a*A = -A
    D_val = (-A) % PRIME 
    
    E = ((X1 + Y1) * (X1 + Y1) - A - B) % PRIME
    G = (D_val + B) % PRIME
    F = (G - C) % PRIME
    H = (D_val - B) % PRIME
    
    X3 = (E * F) % PRIME
    Y3 = (G * H) % PRIME
    T3 = (E * H) % PRIME
    Z3 = (F * G) % PRIME
    
    return (X3, Y3, Z3, T3)

def to_affine(P):
    """
    Convertit un point projectif (X,Y,Z,T) en affine (x,y).
    C'est la SEULE opération qui nécessite une inversion modulaire.
    """
    X, Y, Z, T = P
    inv_Z = pow(Z, -1, PRIME)
    x = (X * inv_Z) % PRIME
    y = (Y * inv_Z) % PRIME
    return (x, y)

def scalar_multiplication(point_proj, scalar):
    """
    Multiplication scalaire optimisée (Double-and-Add).
    Travaille entièrement en coordonnées projectives.
    """
    if scalar == 0:
        return (0, 1, 1, 0) # Point neutre
    
    # Point résultant (Neutre au départ)
    result = (0, 1, 1, 0)
    
    # Conversion binaire (suppression du préfixe '0b')
    bits = bin(scalar)[2:]
    
    for bit in bits:
        result = point_double_projective(result)
        if bit == '1':
            result = point_add_projective(result, point_proj)
            
    return result

# ============================================================
# FONCTIONS PRINCIPALES (AVEC MESURES)
# ============================================================

def generate_keypair():
    """Génère une paire de clés et mesure le temps."""
    start_time = time.perf_counter()
    
    # Clé privée (256 bits)
    private_key = random.getrandbits(256)
    private_key = private_key % (PRIME - 1) + 1
    
    # Clé publique (Calcul optimisé)
    public_key_proj = scalar_multiplication(BASE_POINT_PROJ, private_key)
    public_key = to_affine(public_key_proj)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    return private_key, public_key, duration

def sign_message(message, private_key):
    """Signe un message et mesure le temps."""
    start_time = time.perf_counter()
    
    message_int = message_to_int(message)
    
    # Génération déterministe du nonce r
    r_seed = hash_elements(message_int, private_key, "nonce")
    r = r_seed % (PRIME - 1) + 1
    
    # Calcul de R = r * G (Optimisé)
    R_proj = scalar_multiplication(BASE_POINT_PROJ, r)
    R = to_affine(R_proj)
    
    # Recalcul de la clé publique (nécessaire pour le hash)
    pk_proj = scalar_multiplication(BASE_POINT_PROJ, private_key)
    public_key = to_affine(pk_proj)
    
    # Calcul du challenge h
    h = hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME
    
    # Calcul de s
    s = r + h * private_key
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    return (R, s), duration

def verify_signature(message, signature, public_key):
    """Vérifie une signature et mesure le temps."""
    start_time = time.perf_counter()
    
    R, s = signature
    message_int = message_to_int(message)
    
    h = hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME
    
    # P1 = s * G
    P1_proj = scalar_multiplication(BASE_POINT_PROJ, s)
    P1 = to_affine(P1_proj)
    
    # P2 = R + h * PubKey
    # Conversion de PubKey et R en projectif pour l'addition
    pk_proj = (public_key[0], public_key[1], 1, (public_key[0]*public_key[1])%PRIME)
    R_proj = (R[0], R[1], 1, (R[0]*R[1])%PRIME)
    
    h_times_pk_proj = scalar_multiplication(pk_proj, h)
    P2_proj = point_add_projective(R_proj, h_times_pk_proj)
    P2 = to_affine(P2_proj)
    
    is_valid = (P1[0] == P2[0]) and (P1[1] == P2[1])
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    return is_valid, duration

# ============================================================
# EXECUTION ET AFFICHAGE DES RESULTATS
# ============================================================

if __name__ == "__main__":
    print("\n=== RÉSULTATS DES MESURES DE PERFORMANCE ===")
    
    # 1. Génération de clés
    private_key, public_key, gen_time = generate_keypair()
    print(f"Taille de la clé privée : {private_key.bit_length()} bits")
    print(f"Temps de génération     : {gen_time:.6f} secondes")
    
    # 2. Signature
    message = "Test de performance cryptographique"
    signature, sign_time = sign_message(message, private_key)
    print(f"Temps de signature      : {sign_time:.6f} secondes")
    
    # 3. Vérification
    is_valid, verify_time = verify_signature(message, signature, public_key)
    print(f"Temps de vérification   : {verify_time:.6f} secondes")
    print(f"Validité de la signature: {'VALIDE' if is_valid else 'INVALIDE'}")
    
    print("=" * 50)
