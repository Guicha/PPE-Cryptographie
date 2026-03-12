"""
BankingService - Gestion des comptes et transactions BankLab
"""
import random
import uuid
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from core.crypto_engine import CryptoEngine, AlgoType as CoreAlgo
from models import (
    AlgoType, TransactionType, TransactionStatus,
    ComptesBancaire, BanqueConfig, Transaction, TransactionMetrics,
    BenchmarkRequest, BenchmarkResult, AlgoComparisonResult,
)


# ============================================================
# DONNEES DE SIMULATION REALISTES
# ============================================================

NOMS_CLIENTS = [
    "Dupont Marie", "Martin Jean", "Bernard Sophie", "Petit Lucas",
    "Moreau Emma", "Simon Pierre", "Laurent Alice", "Michel Thomas",
    "Garcia Camille", "David Hugo", "Leroy Lea", "Robert Nathan",
    "Roux Chloe", "Vincent Maxime", "Fournier Julie", "Morel Antoine",
    "Girard Pauline", "Andre Mathis", "Lefebvre Inès", "Mercier Romain",
]

MARCHANDS = [
    ("Carrefour Market", "5411"),
    ("SNCF Voyages", "4112"),
    ("Amazon FR", "5999"),
    ("Total Energie", "5541"),
    ("EDF Electricite", "4911"),
    ("Fnac Darty", "5734"),
    ("Decathlon", "5941"),
    ("Boulangerie Du Coin", "5462"),
    ("Pharmacie Centrale", "5912"),
    ("Netflix France", "7841"),
    ("Orange SA", "4813"),
    ("Uber Eats FR", "5812"),
    ("MAIF Assurances", "6411"),
    ("BNP Paribas ATM", "6011"),
    ("RATP Paris", "4111"),
]

LOCALISATIONS = [
    "Paris 1er", "Paris 8e", "Lyon Part-Dieu", "Marseille Centre",
    "Bordeaux Mériadeck", "Toulouse Capitole", "Nice Promenade",
    "Lille Grand Place", "Nantes Centre", "Strasbourg Cathédrale",
    "En ligne - France", "En ligne - International",
]


def generer_iban():
    """Génère un IBAN français factice."""
    bban = ''.join([str(random.randint(0, 9)) for _ in range(23)])
    return f"FR76{bban}"


def generer_pan():
    """Génère un PAN de carte bancaire masqué (format réel)."""
    prefix = random.choice(["4", "5", "3"])  # Visa, MC, Amex
    digits = ''.join([str(random.randint(0, 9)) for _ in range(11)])
    return f"{prefix}{'*' * 4}{digits[-4:]}"


# ============================================================
# BANK SERVICE
# ============================================================

@dataclass
class AccountInternal:
    """Compte avec clés cryptographiques internes."""
    id: str
    titulaire: str
    iban: str
    pan: str
    solde: float
    devise: str
    algo: CoreAlgo
    engine: CryptoEngine
    numero_compte: str


class BankingService:
    """
    Service bancaire principal.
    Gère les comptes virtuels et les transactions signées.
    """

    def __init__(self):
        self._accounts: Dict[str, AccountInternal] = {}
        self._transactions: List[Transaction] = []
        self._config: Optional[BanqueConfig] = None
        self._initialise = False
        self._init_progress: List[str] = []

    @property
    def is_initialised(self) -> bool:
        return self._initialise

    @property
    def config(self) -> Optional[BanqueConfig]:
        return self._config

    @property
    def transactions(self) -> List[Transaction]:
        return self._transactions

    def get_init_progress(self) -> List[str]:
        return self._init_progress

    def initialiser_banque(self, config: BanqueConfig, progress_callback=None) -> List[ComptesBancaire]:
        """
        Initialise la banque virtuelle avec les comptes et clés cryptographiques.
        """
        self._config = config
        self._accounts.clear()
        self._transactions.clear()
        self._init_progress = []
        self._initialise = False

        algo_core = CoreAlgo(config.algo.value)
        clients = random.sample(NOMS_CLIENTS, min(config.nb_comptes, len(NOMS_CLIENTS)))
        comptes_publics = []

        for i, nom in enumerate(clients):
            msg = f"Génération des clés {config.algo.value} pour {nom}..."
            self._init_progress.append(msg)
            if progress_callback:
                progress_callback(msg, i + 1, len(clients))

            rsa_bits = config.rsa_key_bits // 2  # bits par premier
            engine = CryptoEngine(algo_core, rsa_bits=rsa_bits)
            keypair = engine.generate_keys()

            account_id = str(uuid.uuid4())
            iban = generer_iban()
            pan = generer_pan()
            numero = f"00{random.randint(10000000, 99999999)}0"
            solde = round(random.uniform(500, 15000), 2)

            # Représentation lisible de la clé publique
            if config.algo == AlgoType.RSA:
                e, n = keypair.public_key
                pub_hex = hex(n)[-32:]  # les 32 derniers hex du modulus
            else:
                x, y = keypair.public_key
                pub_hex = hex(x)[-32:]

            acc = AccountInternal(
                id=account_id,
                titulaire=nom,
                iban=iban,
                pan=pan,
                solde=solde,
                devise="EUR",
                algo=algo_core,
                engine=engine,
                numero_compte=numero,
            )
            self._accounts[account_id] = acc

            comptes_publics.append(ComptesBancaire(
                id=account_id,
                titulaire=nom,
                numero_compte=numero,
                iban=iban,
                solde=solde,
                devise="EUR",
                algo=config.algo,
                cle_publique_hex=pub_hex,
            ))

        self._initialise = True
        msg = f"Banque initialisée avec {len(clients)} comptes ({config.algo.value})"
        self._init_progress.append(msg)
        if progress_callback:
            progress_callback(msg, len(clients), len(clients))

        return comptes_publics

    def effectuer_transaction(
        self,
        compte_source_id: str,
        montant: float,
        type_tx: TransactionType,
        compte_dest_id: Optional[str] = None,
        marchand: Optional[str] = None,
        mcc: str = "5999",
        localisation: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Transaction:
        """
        Effectue une transaction bancaire avec signature cryptographique.
        """
        if not self._initialise:
            raise RuntimeError("La banque n'est pas initialisée.")

        source = self._accounts.get(compte_source_id)
        if not source:
            raise ValueError(f"Compte source introuvable: {compte_source_id}")

        dest = None
        if compte_dest_id:
            dest = self._accounts.get(compte_dest_id)

        # Construction du message de transaction (format réaliste)
        timestamp_now = datetime.now()
        marchand_nom = marchand or random.choice(MARCHANDS)[0]
        loc = localisation or random.choice(LOCALISATIONS)
        tx_ref = f"TXN{random.randint(100000,999999)}"

        message_tx = json.dumps({
            "reference": tx_ref,
            "type": type_tx.value,
            "montant": montant,
            "devise": "EUR",
            "pan_source": source.pan,
            "iban_source": source.iban,
            "iban_destination": dest.iban if dest else None,
            "marchand": marchand_nom,
            "mcc": mcc,
            "terminal": f"TRM{random.randint(1000,9999)}",
            "timestamp": timestamp_now.isoformat(),
            "localisation": loc,
        }, ensure_ascii=False)

        # Signature cryptographique
        sig_result = source.engine.sign(message_tx)
        sig_result = source.engine.verify(message_tx, sig_result)

        # Représentation hex de la signature
        if source.algo == CoreAlgo.RSA:
            sig_hex = hex(sig_result.signature)[:64] + "..."
        else:
            R, s = sig_result.signature
            sig_hex = hex(R[0])[:32] + "..." + hex(s)[:16] + "..."

        # Mise à jour du solde
        status = TransactionStatus.APPROUVE
        if source.solde < montant:
            status = TransactionStatus.REFUSE
        elif sig_result.is_valid:
            source.solde -= montant
            if dest:
                dest.solde += montant
        else:
            status = TransactionStatus.ERREUR

        # Construction de la transaction finale
        keygen_meta = source.engine.keypair.metadata if source.engine.keypair else {}

        metrics = TransactionMetrics(
            algo=AlgoType(source.algo.value),
            keygen_time_ms=keygen_meta.get("keygen_time_ms", 0),
            sign_time_ms=sig_result.sign_time_ms,
            verify_time_ms=sig_result.verify_time_ms,
            total_crypto_time_ms=(
                sig_result.sign_time_ms + sig_result.verify_time_ms
            ),
            key_size_bits=sig_result.key_size_bits,
            signature_size_bytes=sig_result.signature_size_bytes,
            security_bits=keygen_meta.get("security_bits", 0) or (
                128 if source.algo == CoreAlgo.ECDSA else 112
            ),
            is_valid=sig_result.is_valid,
        )

        transaction = Transaction(
            reference=tx_ref,
            type_transaction=type_tx,
            montant=montant,
            devise="EUR",
            mcc=mcc,
            marchand=marchand_nom,
            compte_source=source.iban,
            compte_destination=dest.iban if dest else None,
            titulaire_source=source.titulaire,
            titulaire_destination=dest.titulaire if dest else "",
            status=status,
            timestamp=timestamp_now,
            timestamp_validation=datetime.now(),
            message_signe=message_tx[:200] + "...",
            signature_hex=sig_hex,
            metrics=metrics,
            localisation=loc,
        )

        self._transactions.append(transaction)
        return transaction

    def transaction_aleatoire(self) -> Optional[Transaction]:
        """Génère et exécute une transaction aléatoire entre comptes."""
        if not self._initialise or len(self._accounts) < 1:
            return None

        account_ids = list(self._accounts.keys())
        source_id = random.choice(account_ids)

        # Sélection du type et paramètres
        type_tx = random.choice(list(TransactionType))
        montant = round(random.uniform(1.5, 2500), 2)

        dest_id = None
        if type_tx in (TransactionType.VIREMENT,) and len(account_ids) > 1:
            candidates = [a for a in account_ids if a != source_id]
            dest_id = random.choice(candidates)

        marchand_data = random.choice(MARCHANDS)

        try:
            return self.effectuer_transaction(
                compte_source_id=source_id,
                montant=montant,
                type_tx=type_tx,
                compte_dest_id=dest_id,
                marchand=marchand_data[0],
                mcc=marchand_data[1],
            )
        except Exception:
            return None

    def get_accounts(self) -> List[ComptesBancaire]:
        """Retourne la liste des comptes publics."""
        result = []
        for acc in self._accounts.values():
            keypair = acc.engine.keypair
            if keypair:
                if acc.algo == CoreAlgo.RSA:
                    e, n = keypair.public_key
                    pub_hex = hex(n)[-32:]
                else:
                    x, y = keypair.public_key
                    pub_hex = hex(x)[-32:]
            else:
                pub_hex = ""

            result.append(ComptesBancaire(
                id=acc.id,
                titulaire=acc.titulaire,
                numero_compte=acc.numero_compte,
                iban=acc.iban,
                solde=round(acc.solde, 2),
                devise=acc.devise,
                algo=AlgoType(acc.algo.value),
                cle_publique_hex=pub_hex,
            ))
        return result

    def get_transactions(self, limit: int = 100) -> List[Transaction]:
        return list(reversed(self._transactions[-limit:]))

    def get_stats(self) -> dict:
        """Statistiques globales de la banque."""
        if not self._transactions:
            return {
                "total_transactions": 0,
                "approuvees": 0,
                "refusees": 0,
                "erreurs": 0,
                "montant_total": 0,
                "sign_time_avg_ms": 0,
                "verify_time_avg_ms": 0,
                "algo": self._config.algo.value if self._config else "N/A",
            }

        tx = self._transactions
        approuvees = [t for t in tx if t.status == TransactionStatus.APPROUVE]
        refusees = [t for t in tx if t.status == TransactionStatus.REFUSE]
        erreurs = [t for t in tx if t.status == TransactionStatus.ERREUR]

        sign_times = [t.metrics.sign_time_ms for t in tx if t.metrics]
        verify_times = [t.metrics.verify_time_ms for t in tx if t.metrics]

        return {
            "total_transactions": len(tx),
            "approuvees": len(approuvees),
            "refusees": len(refusees),
            "erreurs": len(erreurs),
            "montant_total": round(sum(t.montant for t in approuvees), 2),
            "sign_time_avg_ms": round(sum(sign_times) / len(sign_times), 3) if sign_times else 0,
            "verify_time_avg_ms": round(sum(verify_times) / len(verify_times), 3) if verify_times else 0,
            "algo": self._config.algo.value if self._config else "N/A",
        }


# ============================================================
# BENCHMARK SERVICE
# ============================================================

class BenchmarkService:
    """Service de benchmark cryptographique isolé."""

    def run_benchmark(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Exécute un benchmark complet sur N itérations."""
        algo = CoreAlgo(request.algo.value)
        rsa_bits = (request.rsa_bits or 2048) // 2

        keygen_times = []
        sign_times = []
        verify_times = []
        key_size_bits = 0
        sig_size_bytes = 0

        for _ in range(request.nb_iterations):
            engine = CryptoEngine(algo, rsa_bits=rsa_bits)

            # Keygen
            t0 = time.perf_counter()
            keypair = engine.generate_keys()
            keygen_times.append((time.perf_counter() - t0) * 1000)

            # Sign
            sig_result = engine.sign(request.message_test)
            sign_times.append(sig_result.sign_time_ms)

            # Verify
            sig_result = engine.verify(request.message_test, sig_result)
            verify_times.append(sig_result.verify_time_ms)

            key_size_bits = sig_result.key_size_bits
            sig_size_bytes = sig_result.signature_size_bytes

        from core.crypto_engine import _rsa_security_bits
        if algo == CoreAlgo.RSA:
            security_bits = _rsa_security_bits(key_size_bits)
        else:
            security_bits = 128

        total_time = sum(keygen_times) + sum(sign_times) + sum(verify_times)
        # TPS basé sur sign+verify uniquement
        avg_tx_time = (sum(sign_times) + sum(verify_times)) / request.nb_iterations / 1000
        throughput = 1.0 / avg_tx_time if avg_tx_time > 0 else 0

        return BenchmarkResult(
            algo=request.algo,
            rsa_bits=request.rsa_bits if algo == CoreAlgo.RSA else None,
            nb_iterations=request.nb_iterations,
            keygen_time_avg_ms=round(sum(keygen_times) / len(keygen_times), 3),
            keygen_time_min_ms=round(min(keygen_times), 3),
            keygen_time_max_ms=round(max(keygen_times), 3),
            sign_time_avg_ms=round(sum(sign_times) / len(sign_times), 3),
            sign_time_min_ms=round(min(sign_times), 3),
            sign_time_max_ms=round(max(sign_times), 3),
            verify_time_avg_ms=round(sum(verify_times) / len(verify_times), 3),
            verify_time_min_ms=round(min(verify_times), 3),
            verify_time_max_ms=round(max(verify_times), 3),
            total_time_ms=round(total_time, 3),
            key_size_bits=key_size_bits,
            signature_size_bytes=sig_size_bytes,
            security_bits=security_bits,
            throughput_tps=round(throughput, 2),
        )
