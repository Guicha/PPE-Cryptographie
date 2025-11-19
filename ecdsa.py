import random
import hashlib

# ============================================================
# PARAMÈTRES DE LA COURBE Ed25519 (Type de courbe elliptique choisi pour cette implémentation)
# ============================================================

# Module premier (valeur standard pour Ed25519)
PRIME = pow(2, 255) - 19

# Point de base G (générateur)
# (Point standardisé sur la courbe Ed25519)
BASE_POINT_X = 15112221349535400772501151409588531511454012693041857206046113283949847762202
BASE_POINT_Y = 46316835694926478169428394003475163141307993866256225615783033603165251855960
BASE_POINT = (BASE_POINT_X, BASE_POINT_Y)

# Paramètres de l'équation de la courbe : ax² + y² = 1 + dx²y²
# IMMUABLE : Spécifiques à Ed25519
A = -1  # Coefficient a (simplifie les calculs)

# Calcul de d = -121665/121666 mod p
# IMMUABLE : Valeur choisie pour la sécurité de Ed25519
D_NUMERATOR = -121665
D_DENOMINATOR = 121666
# On calcule l'inverse modulaire du dénominateur puis on multiplie
D = (D_NUMERATOR * pow(D_DENOMINATOR, -1, PRIME)) % PRIME

print("=== CONFIGURATION DE LA COURBE Ed25519 ===")
print(f"Module p (255 bits) : {PRIME}")
print(f"Paramètre a : {A}")
print(f"Paramètre d : {D}")
print(f"Point de base G : ({BASE_POINT_X}, {BASE_POINT_Y})")
print("=" * 50)

# ============================================================
# FONCTION MATHEMATIQUES
# ============================================================

def mod_inverse(a, m):
    """
    Calcule l'inverse modulaire de a modulo m
    FONCTION IMMUABLE : Algorithme mathématique standard
    
    Paramètres:
        a : VARIABLE - nombre dont on veut l'inverse
        m : VARIABLE - module (généralement P pour nous)
    
    Retourne: a^(-1) mod m tel que a * a^(-1) ≡ 1 (mod m)
    """
    # Gestion des nombres négatifs
    if a < 0:
        a = (a % m + m) % m
    
    # Vérification que a et m sont copremiers
    if gcd(a, m) != 1:
        raise ValueError(f"Pas d'inverse modulaire : gcd({a}, {m}) != 1")
    
    # Algorithme d'Euclide étendu
    # IMMUABLE : Cet algorithme est mathématiquement prouvé
    u1, u2, u3 = 1, 0, a
    v1, v2, v3 = 0, 1, m
    
    while v3 != 0:
        q = u3 // v3
        v1, v2, v3, u1, u2, u3 = (u1 - q * v1), (u2 - q * v2), (u3 - q * v3), v1, v2, v3
    
    return u1 % m


def gcd(a, b):
    """
    Calcule le plus grand commun diviseur (PGCD)
    FONCTION IMMUABLE : Algorithme d'Euclide classique
    
    Paramètres:
        a, b : VARIABLES - les deux nombres
    """
    while a != 0:
        a, b = b % a, a
    return b


def message_to_int(message):
    """
    Convertit un message texte en entier
    FONCTION MODIFIABLE : Vous pouvez changer l'encodage
    
    Paramètres:
        message : VARIABLE - texte à convertir (ex: "Hello")
    """
    # MODIFIABLE : On peut utiliser d'autres encodages (latin-1, ascii...)
    if isinstance(message, str):
        message_bytes = message.encode('utf-8')
    else:
        message_bytes = message
    
    # Conversion bytes → hexadécimal → entier
    hex_string = message_bytes.hex()
    return int(hex_string, 16)


def hash_elements(*elements):
    """
    Hache une série d'éléments avec SHA-512
    SEMI-MODIFIABLE : SHA-512 est recommandé mais on pourrait utiliser SHA3-512
    
    Paramètres:
        *elements : VARIABLES - éléments à hacher ensemble
    """
    # IMMUABLE pour Ed25519 : Doit utiliser SHA-512
    hasher = hashlib.sha512()
    
    # Concaténer tous les éléments
    for element in elements:
        hasher.update(str(element).encode('utf-8'))
    
    # Retourner l'entier du hash
    return int(hasher.hexdigest(), 16)


# ============================================================
# OPERATIONS SUR LA COURBE ELLIPTIQUE
# ============================================================

def point_addition(point1, point2):
    """
    Addition de deux points sur la courbe Ed25519
    FONCTION IMMUABLE : Formules mathématiques de la courbe d'Edwards
    
    Formules (IMMUABLES pour courbe d'Edwards):
    x3 = (x1*y2 + y1*x2) / (1 + d*x1*x2*y1*y2)
    y3 = (y1*y2 - a*x1*x2) / (1 - d*x1*x2*y1*y2)
    """
    x1, y1 = point1
    x2, y2 = point2
    
    # Calcul du numérateur et dénominateur pour x3
    # IMMUABLE : Ces formules sont spécifiques aux courbes d'Edwards
    x3_numerator = (x1 * y2 + y1 * x2) % PRIME
    x3_denominator = (1 + D * x1 * x2 * y1 * y2) % PRIME
    
    # Calcul du numérateur et dénominateur pour y3
    y3_numerator = (y1 * y2 - A * x1 * x2) % PRIME  # Note: A = -1 donc ça devient +
    y3_denominator = (1 - D * x1 * x2 * y1 * y2) % PRIME
    
    # Division = multiplication par l'inverse modulaire
    x3 = (x3_numerator * mod_inverse(x3_denominator, PRIME)) % PRIME
    y3 = (y3_numerator * mod_inverse(y3_denominator, PRIME)) % PRIME
    
    return (x3, y3)


def scalar_multiplication(point, scalar):
    """
    Multiplication scalaire : calcule scalar * point
    ALGORITHME IMMUABLE : Double-and-add (efficace et standard)
    
    Paramètres:
        point : VARIABLE - Point sur la courbe (x, y)
        scalar : VARIABLE - Entier multiplicateur
    
    Retourne: scalar * point
    
    Exemple: 5 * P = P + P + P + P + P (mais optimisé)
    """
    # Cas spécial : scalar = 0
    if scalar == 0:
        # IMMUABLE : Point à l'infini sur Ed25519
        return (0, 1)  # Point neutre sur courbe d'Edwards
    
    # Cas spécial : scalar = 1
    if scalar == 1:
        return point
    
    # Conversion du scalaire en binaire
    # IMMUABLE : Méthode double-and-add
    binary = bin(scalar)[2:]  # Enlève '0b'
    
    # Initialisation avec le premier bit (toujours 1)
    result = point
    
    # Parcours des bits suivants
    for bit in binary[1:]:
        # TOUJOURS doubler (IMMUABLE dans l'algorithme)
        result = point_addition(result, result)
        
        # Si le bit est 1, ajouter le point de base
        if bit == '1':
            result = point_addition(result, point)
    
    return result


def is_point_on_curve(point):
    """
    Vérifie qu'un point est sur la courbe
    FONCTION IMMUABLE : Équation de la courbe Ed25519
    
    Paramètres:
        point : VARIABLE - Point à vérifier (x, y)
    
    Vérifie : ax² + y² = 1 + dx²y²
    """
    x, y = point
    
    # Calcul des deux côtés de l'équation
    # IMMUABLE : Équation de la courbe d'Edwards
    left_side = (A * x * x + y * y) % PRIME
    right_side = (1 + D * x * x * y * y) % PRIME
    
    return left_side == right_side


# ============================================================
# GENERATIONS DES CLES
# ============================================================

def generate_keypair():
    """
    Génère une paire de clés (privée, publique)
    
    Retourne:
        private_key : VARIABLE SECRÈTE - Entier aléatoire 256 bits
        public_key : VARIABLE PUBLIQUE - Point sur la courbe
    """
    # Génération de la clé privée
    # MODIFIABLE : La taille (256 bits) est recommandée mais flexible
    # IMPORTANT : Doit être aléatoire et secret !
    private_key = random.getrandbits(256)
    
    # La clé privée doit être dans [1, p-1]
    # IMMUABLE : Contrainte mathématique
    private_key = private_key % (PRIME - 1) + 1
    
    # Calcul de la clé publique
    # IMMUABLE : public_key = private_key × G
    public_key = scalar_multiplication(BASE_POINT, private_key)
    
    print(f"\nClé privée générée :")
    print(f"   {private_key}")
    print(f"Clé publique correspondante :")
    print(f"   x: {public_key[0]}")
    print(f"   y: {public_key[1]}")
    
    return private_key, public_key

# Génération d'exemple
print("\n=== GÉNÉRATION D'UNE PAIRE DE CLÉS ===")
khaled_private, khaled_public = generate_keypair()

# ============================================================
# SIGNATURE
# ============================================================

def sign_message(message, private_key):
    """
    Signe un message avec ECDSA/Ed25519
    
    Paramètres:
        message : VARIABLE - Le message à signer (string ou bytes)
        private_key : VARIABLE SECRÈTE - La clé privée du signataire
    
    Retourne:
        (R, s) : La signature
            R : VARIABLE PUBLIQUE - Point éphémère (engagement)
            s : VARIABLE PUBLIQUE - Scalaire de preuve
    """
    # Étape 1: Convertir le message en entier
    if isinstance(message, str):
        message_int = message_to_int(message)
    else:
        message_int = int.from_bytes(message, 'big')
    
    # Étape 2: Générer le nonce r
    r_seed = hash_elements(message_int, private_key, "nonce")
    r = r_seed % (PRIME - 1) + 1
    
    # Étape 3: Calculer R = r × G
    # IMMUABLE : Partie publique du nonce
    R = scalar_multiplication(BASE_POINT, r)
    
    # Étape 4: Calculer la clé publique (pour le hash)
    # IMMUABLE : Nécessaire pour lier la signature à l'identité
    public_key = scalar_multiplication(BASE_POINT, private_key)
    
    # Étape 5: Calculer le challenge h
    # IMMUABLE pour Ed25519 : h = H(R || public_key || message)
    h = hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME
    
    # Étape 6: Calculer s
    # IMMUABLE : Formule ECDSA s = r + h × private_key
    s = r + h * private_key
    
    print(f"\nSignature générée pour le message :")
    print(f"   R: ({str(R[0])[:30]}..., {str(R[1])[:30]}...)")
    print(f"   s: {s}")
    
    return (R, s)

# Test de signature
print("\n=== SIGNATURE D'UN MESSAGE ===")
message_test = "Bonjour Nahla, c'est Khaled !"  
print(f"Message de test: {message_test}")
signature = sign_message(message_test, khaled_private)

# ============================================================
# VERIFICATION DE LA SIGNATURE
# ============================================================

def verify_signature(message, signature, public_key):
    """
    Vérifie une signature ECDSA/Ed25519
    
    Paramètres:
        message : VARIABLE - Le message signé
        signature : VARIABLE - Tuple (R, s) de la signature
        public_key : VARIABLE PUBLIQUE - Clé publique du signataire
    
    Retourne:
        bool : True si valide, False sinon
    """
    R, s = signature
    
    # Étape 1: Convertir le message
    # DOIT être identique à la signature !
    if isinstance(message, str):
        message_int = message_to_int(message)
    else:
        message_int = int.from_bytes(message, 'big')
    
    # Étape 2: Recalculer le challenge h
    # IMMUABLE : Même formule que pour la signature
    h = hash_elements(R[0], R[1], public_key[0], public_key[1], message_int) % PRIME
    
    # Étape 3: Calculer P1 = s × G
    # IMMUABLE : Première équation de vérification
    P1 = scalar_multiplication(BASE_POINT, s)
    
    # Étape 4: Calculer P2 = R + h × public_key
    # IMMUABLE : Deuxième équation de vérification
    h_times_pub = scalar_multiplication(public_key, h)
    P2 = point_addition(R, h_times_pub)
    
    # Étape 5: Vérifier l'égalité
    # IMMUABLE : Condition de validité
    is_valid = (P1[0] == P2[0]) and (P1[1] == P2[1])
    
    print(f"\nVérification de la signature :")
    print(f"   P1 = s * G")
    print(f"   P2 = R + h * PublicKey")
    print(f"   P1 == P2 ? {is_valid}")
    
    if is_valid:
        print("   SIGNATURE VALIDE :)")
    else:
        print("   SIGNATURE INVALIDE :(")
    
    return is_valid

# Test de vérification
print("\n=== VÉRIFICATION DE LA SIGNATURE ===")
is_valid = verify_signature(message_test, signature, khaled_public)

# Test avec mauvais message
print("\n=== TEST AVEC MESSAGE MODIFIÉ ===")
message_modifie = "Bonjour Nahla, c'est Khaled ! (En réalité je suis un criminel qui me fait passer pour Khaled mwouhahahaha)"
print(f"Message altéré: {message_modifie}") 
is_valid_modifie = verify_signature(message_modifie, signature, khaled_public)