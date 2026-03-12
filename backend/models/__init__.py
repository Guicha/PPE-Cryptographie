"""
Modèles de données BankLab - Format proche de la réalité bancaire (ISO 8583 inspiré)
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from enum import Enum
from datetime import datetime
import uuid
import random


# ============================================================
# ENUMERATIONS
# ============================================================

class AlgoType(str, Enum):
    RSA = "RSA"
    ECDSA = "ECDSA"


class TransactionType(str, Enum):
    PAIEMENT_CB = "PAIEMENT_CB"          # Paiement par carte bancaire
    RETRAIT_DAB = "RETRAIT_DAB"          # Retrait distributeur
    VIREMENT = "VIREMENT"                # Virement bancaire
    PAIEMENT_MOBILE = "PAIEMENT_MOBILE"  # Paiement mobile (NFC)
    AUTORISATION = "AUTORISATION"        # Demande d'autorisation pré-paiement
    REMBOURSEMENT = "REMBOURSEMENT"      # Remboursement


class TransactionStatus(str, Enum):
    EN_ATTENTE = "EN_ATTENTE"
    SIGNE = "SIGNE"
    VERIFIE = "VERIFIE"
    APPROUVE = "APPROUVE"
    REFUSE = "REFUSE"
    ERREUR = "ERREUR"


class RSAKeySize(int, Enum):
    RSA_1024 = 512    # bits par premier (module = 1024)
    RSA_2048 = 1024   # bits par premier (module = 2048)
    RSA_3072 = 1536   # bits par premier (module = 3072)
    RSA_4096 = 2048   # bits par premier (module = 4096)


# ============================================================
# MODELES BANCAIRES
# ============================================================

class AdresseBancaire(BaseModel):
    iban: str
    bic: str
    banque: str
    pays: str = "FR"


class ComptesBancaire(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    titulaire: str
    numero_compte: str
    iban: str
    solde: float
    devise: str = "EUR"
    algo: AlgoType
    cle_publique_hex: str = ""  # représentation lisible
    actif: bool = True
    date_creation: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BanqueConfig(BaseModel):
    nom: str = "BankLab Testbed"
    code_banque: str = "BKLA"
    pays: str = "FR"
    algo: AlgoType = AlgoType.ECDSA
    rsa_key_bits: int = 2048  # taille module RSA (1024, 2048, 3072, 4096)
    nb_comptes: int = 5
    tps_cible: float = 1.0   # transactions par seconde cible


# ============================================================
# TRANSACTION ISO 8583-like
# ============================================================

class TransactionRequest(BaseModel):
    """Requête de transaction - similaire à un message ISO 8583"""
    # Champ 2 : PAN (Primary Account Number)
    pan_source: str
    pan_destination: Optional[str] = None

    # Champ 4 : Montant
    montant: float
    devise: str = "EUR"

    # Champ 18 : Code MCC (Merchant Category Code)
    mcc: str = "5999"
    marchand: str = "Inconnu"

    # Type de transaction
    type_transaction: TransactionType = TransactionType.PAIEMENT_CB

    # Données supplémentaires
    description: Optional[str] = None
    localisation: Optional[str] = None

    # Configuration crypto
    algo: AlgoType = AlgoType.ECDSA
    rsa_bits: Optional[int] = None  # uniquement pour RSA


class TransactionMetrics(BaseModel):
    """Métriques cryptographiques d'une transaction"""
    algo: AlgoType
    keygen_time_ms: float = 0.0
    sign_time_ms: float
    verify_time_ms: float
    total_crypto_time_ms: float
    key_size_bits: int
    signature_size_bytes: int
    security_bits: int
    is_valid: bool


class Transaction(BaseModel):
    """Transaction complète avec toutes les données"""
    # Identifiant unique
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reference: str = Field(default_factory=lambda: f"TXN{random.randint(100000,999999)}")

    # Données de la transaction
    type_transaction: TransactionType
    montant: float
    devise: str = "EUR"
    mcc: str = "5999"
    marchand: str

    # Comptes
    compte_source: str
    compte_destination: Optional[str] = None
    titulaire_source: str = ""
    titulaire_destination: str = ""

    # Statut et timing
    status: TransactionStatus = TransactionStatus.EN_ATTENTE
    timestamp: datetime = Field(default_factory=datetime.now)
    timestamp_validation: Optional[datetime] = None

    # Données cryptographiques
    message_signe: str = ""
    signature_hex: str = ""
    metrics: Optional[TransactionMetrics] = None

    # Localisation et contexte
    localisation: Optional[str] = None
    terminal_id: str = Field(default_factory=lambda: f"TRM{random.randint(1000,9999)}")
    ip_terminal: str = Field(default_factory=lambda: f"192.168.{random.randint(1,254)}.{random.randint(1,254)}")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================
# REPONSES API
# ============================================================

class TransactionResponse(BaseModel):
    success: bool
    transaction: Transaction
    message: str = ""


class BenchmarkRequest(BaseModel):
    algo: AlgoType
    rsa_bits: Optional[int] = 2048
    nb_iterations: int = Field(default=5, ge=1, le=50)
    message_test: str = "Transaction bancaire BankLab test benchmark"


class BenchmarkResult(BaseModel):
    algo: AlgoType
    rsa_bits: Optional[int] = None
    nb_iterations: int
    keygen_time_avg_ms: float
    keygen_time_min_ms: float
    keygen_time_max_ms: float
    sign_time_avg_ms: float
    sign_time_min_ms: float
    sign_time_max_ms: float
    verify_time_avg_ms: float
    verify_time_min_ms: float
    verify_time_max_ms: float
    total_time_ms: float
    key_size_bits: int
    signature_size_bytes: int
    security_bits: int
    throughput_tps: float  # transactions/seconde possibles


class BankStatus(BaseModel):
    initialise: bool
    algo: AlgoType
    nb_comptes: int
    nb_transactions: int
    config: Optional[BanqueConfig] = None


class AlgoComparisonResult(BaseModel):
    rsa: Optional[BenchmarkResult] = None
    ecdsa: Optional[BenchmarkResult] = None
    ratio_keygen: Optional[float] = None     # RSA / ECDSA
    ratio_sign: Optional[float] = None
    ratio_verify: Optional[float] = None
    ratio_key_size: Optional[float] = None


# ============================================================
# WEBSOCKET EVENTS
# ============================================================

class WSEvent(BaseModel):
    type: str  # "transaction", "metric", "bank_init", "error"
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}