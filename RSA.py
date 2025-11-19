import random

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



def generer_nombre_premier(bits=16):
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
        pgcd, x1, y1 = euclide_etendu(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return pgcd, x, y
    
    _, x, _ = euclide_etendu(e, phi)
    return x % phi



def creer_cles(bits=16):
    
    p = generer_nombre_premier(bits)
    q = generer_nombre_premier(bits)
    
    while p == q:
        q = generer_nombre_premier(bits)
    
    print(f"p = {p}")
    print(f"q = {q}")
    
    n = p * q
    print(f"n = p × q = {n}")
    
    phi = (p - 1) * (q - 1)
    print(f"φ(n) = {phi}")
    
    e = 65537
    if e >= phi or pgcd(e, phi) != 1:
        e = random.randrange(2, phi)
        while pgcd(e, phi) != 1:
            e = random.randrange(2, phi)
    
    print(f"e = {e}")
    
    d = inverse_modulaire(e, phi)
    print(f"d = {d}")
    
    cle_publique = (e, n)
    cle_privee = (d, n)
    
    print(f"\nClé publique : {cle_publique}")
    print(f"Clé privée : {cle_privee}\n")
    
    return cle_publique, cle_privee



def texte_vers_nombres(message):
    return [ord(char) for char in message]



def nombres_vers_texte(nombres):
    return ''.join([chr(num) for num in nombres])



def encrypter(message, cle_publique):
    e, n = cle_publique
    nombres = texte_vers_nombres(message)
    
    print(f"Message original : '{message}'\n")
    print(f" Codes ASCII : {nombres}\n")
    
    message_chiffre = [pow(m, e, n) for m in nombres]
    
    print(f"Message chiffré : {message_chiffre}\n")
    
    return message_chiffre



def decrypter(message_chiffre, cle_privee):
    d, n = cle_privee
    
    nombres_dechiffres = [pow(c, d, n) for c in message_chiffre]
    
    print(f"Codes ASCII déchiffrés : {nombres_dechiffres}\n")
    
    message_dechiffre = nombres_vers_texte(nombres_dechiffres)
    
    print(f"Message déchiffré : '{message_dechiffre}'\n")





def main(message):

    print("=" * 60)
    print("        CREATIONS DES CLES PUBLIQUE ET PRIVEE")
    print("=" * 60 + "\n")

    # 1. Créer les clés
    cle_publique, cle_privee = creer_cles(bits=16)
    
    print("=" * 60)
    print("               CHIFFREMENT")
    print("=" * 60 + "\n")
    
    # 2. Chiffrer le message
    message_chiffre = encrypter(message, cle_publique)
    
    print("=" * 60)
    print("              DÉCHIFFREMENT")
    print("=" * 60 + "\n")
    
    # 3. Déchiffrer le message
    decrypter(message_chiffre, cle_privee)
    


if __name__ == "__main__":
    main(message="Bonjour j'aime les falafels!")