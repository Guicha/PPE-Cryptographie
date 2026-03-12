"""
CryptoEngine - Interface unifiée RSA / ECDSA pour BankLab
"""
import time
from dataclasses import dataclass, field
from typing import Any, Tuple, Optional
from enum import Enum

from core.rsa_engine import (
    creer_cles as rsa_keygen,
    signer as rsa_sign,
    verifier as rsa_verify,
)
from core.ecdsa_engine import (
    generate_keypair as ecc_keygen,
    sign_message as ecc_sign,
    verify_signature as ecc_verify,
)


class AlgoType(str, Enum):
    RSA = "RSA"
    ECDSA = "ECDSA"


@dataclass
class KeyPair:
    algo: AlgoType
    public_key: Any
    private_key: Any
    metadata: dict = field(default_factory=dict)


@dataclass
class SignatureResult:
    algo: AlgoType
    signature: Any
    sign_time_ms: float
    verify_time_ms: float = 0.0
    is_valid: bool = False
    key_size_bits: int = 0
    signature_size_bytes: int = 0
    message_hash: Optional[Any] = None


class CryptoEngine:
    """
    Façade unifiée pour RSA et ECDSA.
    Toutes les opérations retournent des métriques de performance.
    """

    def __init__(self, algo: AlgoType, rsa_bits: int = 2048):
        self.algo = algo
        self.rsa_bits = rsa_bits  # bits par premier (module = 2x)
        self._keypair: Optional[KeyPair] = None

    @property
    def keypair(self) -> Optional[KeyPair]:
        return self._keypair

    def generate_keys(self) -> KeyPair:
        """Génère une paire de clés et retourne les métriques."""
        if self.algo == AlgoType.RSA:
            pub, priv, meta = rsa_keygen(bits=self.rsa_bits)
            self._keypair = KeyPair(
                algo=AlgoType.RSA,
                public_key=pub,
                private_key=priv,
                metadata=meta,
            )
        else:
            priv, pub, meta = ecc_keygen()
            self._keypair = KeyPair(
                algo=AlgoType.ECDSA,
                public_key=pub,
                private_key=priv,
                metadata=meta,
            )
        return self._keypair

    def sign(self, message: str) -> SignatureResult:
        """Signe un message avec la clé privée courante."""
        if self._keypair is None:
            raise RuntimeError("Clés non générées. Appeler generate_keys() d'abord.")

        if self.algo == AlgoType.RSA:
            sig, msg_hash, sign_time = rsa_sign(message, self._keypair.private_key)
            # Taille approximative de la signature RSA en octets
            e, n = self._keypair.public_key
            sig_size = (n.bit_length() + 7) // 8
            key_bits = n.bit_length()
            return SignatureResult(
                algo=AlgoType.RSA,
                signature=sig,
                sign_time_ms=sign_time,
                key_size_bits=key_bits,
                signature_size_bytes=sig_size,
                message_hash=msg_hash,
            )
        else:
            (R, s), sign_time = ecc_sign(message, self._keypair.private_key)
            # Signature ECC: 2 coordonnées 256 bits = 64 octets
            sig_size = 64
            return SignatureResult(
                algo=AlgoType.ECDSA,
                signature=(R, s),
                sign_time_ms=sign_time,
                key_size_bits=256,
                signature_size_bytes=sig_size,
            )

    def verify(self, message: str, sig_result: SignatureResult) -> SignatureResult:
        """Vérifie une signature et met à jour les métriques."""
        if self._keypair is None:
            raise RuntimeError("Clés non générées.")

        if self.algo == AlgoType.RSA:
            is_valid, verify_time = rsa_verify(
                message, sig_result.signature, self._keypair.public_key
            )
        else:
            is_valid, verify_time = ecc_verify(
                message, sig_result.signature, self._keypair.public_key
            )

        sig_result.is_valid = is_valid
        sig_result.verify_time_ms = verify_time
        return sig_result

    def sign_and_verify(self, message: str) -> SignatureResult:
        """Signe puis vérifie un message en une seule opération."""
        result = self.sign(message)
        result = self.verify(message, result)
        return result

    def get_algorithm_info(self) -> dict:
        """Retourne les informations sur l'algorithme configuré."""
        if self.algo == AlgoType.RSA:
            return {
                "name": "RSA",
                "full_name": "Rivest-Shamir-Adleman",
                "type": "Asymétrique - Factorisation",
                "key_size_bits": self.rsa_bits * 2,
                "security_bits": _rsa_security_bits(self.rsa_bits * 2),
                "signature_size_bytes": (self.rsa_bits * 2) // 8,
                "nist_recommendation": "3072 bits minimum (2030+)",
                "hash_function": "SHA-512",
                "problem": "Factorisation d'entiers",
            }
        else:
            return {
                "name": "ECDSA",
                "full_name": "Elliptic Curve Digital Signature Algorithm (Ed25519)",
                "type": "Asymétrique - Courbe elliptique",
                "key_size_bits": 256,
                "security_bits": 128,
                "signature_size_bytes": 64,
                "nist_recommendation": "Ed25519 recommandé",
                "hash_function": "SHA-512",
                "problem": "Logarithme discret sur courbe elliptique",
                "curve": "Ed25519 (Twisted Edwards)",
                "prime": "2^255 - 19",
            }


def _rsa_security_bits(key_bits: int) -> int:
    """Estimation des bits de sécurité RSA selon NIST."""
    table = {
        1024: 80,
        2048: 112,
        3072: 128,
        4096: 140,
        7680: 192,
        15360: 256,
    }
    for k, v in sorted(table.items()):
        if key_bits <= k:
            return v
    return 256
