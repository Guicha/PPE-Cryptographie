"""
BankLab API - Backend FastAPI
Système de test cryptographique bancaire RSA vs ECDSA
"""
import asyncio
import json
import time
import sys
import os
import psutil
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ajout du répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    AlgoType, TransactionType, TransactionStatus,
    BanqueConfig, Transaction, ComptesBancaire,
    BenchmarkRequest, BenchmarkResult, AlgoComparisonResult,
    TransactionRequest, TransactionResponse, BankStatus, WSEvent,
)
from services import bank, benchmark_svc
from core.crypto_engine import CryptoEngine, AlgoType as CoreAlgo


# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(
    title="BankLab API",
    description="Système de test cryptographique bancaire — RSA vs ECDSA",
    version="1.0.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()

# Simulation state
sim_running = False
sim_task = None


# ============================================================
# SYSTEM METRICS (CPU / RAM)
# ============================================================

def get_system_metrics() -> dict:
    """Collecte les métriques système via psutil."""
    proc = psutil.Process(os.getpid())
    cpu_proc = proc.cpu_percent(interval=None)
    mem_proc = proc.memory_info()

    return {
        "cpu_global_pct": psutil.cpu_percent(interval=None),
        "cpu_proc_pct": cpu_proc,
        "ram_global_pct": psutil.virtual_memory().percent,
        "ram_global_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 1),
        "ram_global_total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 1),
        "ram_proc_mb": round(mem_proc.rss / 1024 / 1024, 2),
        "cpu_cores": psutil.cpu_count(logical=True),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/system/metrics")
async def system_metrics():
    """Retourne les métriques système actuelles."""
    return get_system_metrics()


# Background task : envoie les métriques système toutes les 2s aux clients WS connectés
system_monitor_task = None


async def _system_monitor_loop():
    """Boucle de monitoring système — émet toutes les 2 secondes."""
    # Initialisation de l'interval CPU (premier appel toujours 0.0)
    psutil.cpu_percent(interval=None)
    psutil.Process(os.getpid()).cpu_percent(interval=None)
    await asyncio.sleep(1)

    while True:
        if manager.active:
            metrics = get_system_metrics()
            await manager.broadcast({
                "type": "system_metrics",
                "data": metrics,
                "timestamp": metrics["timestamp"],
            })
        await asyncio.sleep(2)


@app.on_event("startup")
async def startup_event():
    global system_monitor_task
    system_monitor_task = asyncio.create_task(_system_monitor_loop())


# ============================================================
# ROUTES - BANQUE
# ============================================================

@app.get("/api/status", response_model=BankStatus)
async def get_status():
    """Retourne l'état courant de la banque virtuelle."""
    return BankStatus(
        initialise=bank.is_initialised,
        algo=bank.config.algo if bank.config else AlgoType.ECDSA,
        nb_comptes=len(bank.get_accounts()) if bank.is_initialised else 0,
        nb_transactions=len(bank.transactions),
        config=bank.config,
    )


@app.post("/api/banque/initialiser")
async def initialiser_banque(config: BanqueConfig, background_tasks: BackgroundTasks):
    """
    Initialise la banque virtuelle avec la configuration donnée.
    Génère les clés cryptographiques pour tous les comptes.
    """
    messages = []

    def progress_callback(msg: str, current: int, total: int):
        messages.append({"msg": msg, "current": current, "total": total})
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "init_progress",
                "data": {"msg": msg, "current": current, "total": total},
                "timestamp": datetime.now().isoformat(),
            }),
            asyncio.get_event_loop(),
        )

    try:
        comptes = bank.initialiser_banque(config)

        await manager.broadcast({
            "type": "bank_init",
            "data": {
                "success": True,
                "nb_comptes": len(comptes),
                "algo": config.algo.value,
                "message": f"Banque initialisée — {len(comptes)} comptes {config.algo.value}",
            },
            "timestamp": datetime.now().isoformat(),
        })

        return {
            "success": True,
            "message": f"Banque initialisée avec {len(comptes)} comptes",
            "algo": config.algo.value,
            "nb_comptes": len(comptes),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/banque/comptes", response_model=List[ComptesBancaire])
async def get_comptes():
    """Retourne la liste de tous les comptes bancaires."""
    if not bank.is_initialised:
        raise HTTPException(status_code=400, detail="Banque non initialisée")
    return bank.get_accounts()


@app.get("/api/banque/stats")
async def get_stats():
    """Retourne les statistiques globales de la banque."""
    return bank.get_stats()


# ============================================================
# ROUTES - TRANSACTIONS
# ============================================================

@app.post("/api/transaction", response_model=TransactionResponse)
async def creer_transaction(request: TransactionRequest):
    """
    Crée et signe une transaction bancaire.
    """
    if not bank.is_initialised:
        raise HTTPException(status_code=400, detail="Banque non initialisée")

    comptes = bank.get_accounts()
    if not comptes:
        raise HTTPException(status_code=400, detail="Aucun compte disponible")

    # Trouver le compte source par PAN ou prendre le premier
    source = None
    for c in comptes:
        if c.iban.endswith(request.pan_source[-4:]) or source is None:
            source = c
            break

    dest = None
    if request.pan_destination:
        for c in comptes:
            if c.iban != source.iban:
                dest = c
                break

    try:
        tx = bank.effectuer_transaction(
            compte_source_id=source.id,
            montant=request.montant,
            type_tx=request.type_transaction,
            compte_dest_id=dest.id if dest else None,
            marchand=request.marchand,
            mcc=request.mcc,
            localisation=request.localisation,
            description=request.description,
        )

        # Broadcast WebSocket
        await manager.broadcast({
            "type": "transaction",
            "data": tx.model_dump(mode="json"),
            "timestamp": datetime.now().isoformat(),
        })

        return TransactionResponse(
            success=True,
            transaction=tx,
            message=f"Transaction {tx.reference} — {tx.status.value}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transaction/aleatoire", response_model=TransactionResponse)
async def transaction_aleatoire():
    """Génère une transaction aléatoire réaliste."""
    if not bank.is_initialised:
        raise HTTPException(status_code=400, detail="Banque non initialisée")

    tx = bank.transaction_aleatoire()
    if not tx:
        raise HTTPException(status_code=500, detail="Impossible de générer une transaction")

    await manager.broadcast({
        "type": "transaction",
        "data": tx.model_dump(mode="json"),
        "timestamp": datetime.now().isoformat(),
    })

    return TransactionResponse(
        success=True,
        transaction=tx,
        message=f"Transaction {tx.reference} — {tx.status.value}",
    )


@app.get("/api/transactions", response_model=List[Transaction])
async def get_transactions(limit: int = 50):
    """Retourne les dernières transactions."""
    if not bank.is_initialised:
        return []
    return bank.get_transactions(limit=limit)


# ============================================================
# ROUTES - SIMULATION
# ============================================================

class SimConfig(BaseModel):
    tps: float = 1.0  # transactions par seconde
    duree_secondes: Optional[int] = None  # None = infini


@app.post("/api/simulation/demarrer")
async def demarrer_simulation(config: SimConfig, background_tasks: BackgroundTasks):
    """Démarre la simulation automatique de transactions."""
    global sim_running, sim_task

    if not bank.is_initialised:
        raise HTTPException(status_code=400, detail="Banque non initialisée")

    if sim_running:
        return {"message": "Simulation déjà en cours"}

    sim_running = True

    async def run_sim():
        global sim_running
        count = 0
        interval = 1.0 / max(config.tps, 0.1)
        max_tx = int(config.duree_secondes * config.tps) if config.duree_secondes else None

        while sim_running:
            if max_tx and count >= max_tx:
                break

            tx = bank.transaction_aleatoire()
            if tx:
                await manager.broadcast({
                    "type": "transaction",
                    "data": tx.model_dump(mode="json"),
                    "timestamp": datetime.now().isoformat(),
                })

                # Envoi des métriques
                if tx.metrics:
                    await manager.broadcast({
                        "type": "metric",
                        "data": {
                            "sign_ms": tx.metrics.sign_time_ms,
                            "verify_ms": tx.metrics.verify_time_ms,
                            "total_ms": tx.metrics.total_crypto_time_ms,
                            "algo": tx.metrics.algo.value,
                            "montant": tx.montant,
                            "type": tx.type_transaction.value,
                            "status": tx.status.value,
                            "timestamp": tx.timestamp.isoformat(),
                        },
                        "timestamp": datetime.now().isoformat(),
                    })

            count += 1
            await asyncio.sleep(interval)

        sim_running = False
        await manager.broadcast({
            "type": "simulation_stopped",
            "data": {"nb_transactions": count},
            "timestamp": datetime.now().isoformat(),
        })

    sim_task = asyncio.create_task(run_sim())
    return {"message": "Simulation démarrée", "tps": config.tps}


@app.post("/api/simulation/arreter")
async def arreter_simulation():
    """Arrête la simulation automatique."""
    global sim_running
    sim_running = False
    return {"message": "Simulation arrêtée"}


@app.get("/api/simulation/status")
async def simulation_status():
    return {"running": sim_running}


# ============================================================
# ROUTES - BENCHMARK
# ============================================================

@app.post("/api/benchmark", response_model=BenchmarkResult)
async def run_benchmark(request: BenchmarkRequest):
    """
    Lance un benchmark cryptographique.
    Mesure keygen, sign, verify sur N itérations.
    """
    try:
        result = benchmark_svc.run_benchmark(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/benchmark/comparaison", response_model=AlgoComparisonResult)
async def run_comparison(
    nb_iterations: int = 3,
    rsa_bits: int = 2048,
    message: str = "Transaction bancaire BankLab test",
):
    """
    Compare RSA et ECDSA côte à côte.
    """
    try:
        req_rsa = BenchmarkRequest(
            algo=AlgoType.RSA,
            rsa_bits=rsa_bits,
            nb_iterations=nb_iterations,
            message_test=message,
        )
        req_ecc = BenchmarkRequest(
            algo=AlgoType.ECDSA,
            nb_iterations=nb_iterations,
            message_test=message,
        )

        result_rsa = benchmark_svc.run_benchmark(req_rsa)
        result_ecc = benchmark_svc.run_benchmark(req_ecc)

        def safe_ratio(a, b):
            return round(a / b, 2) if b > 0 else None

        return AlgoComparisonResult(
            rsa=result_rsa,
            ecdsa=result_ecc,
            ratio_keygen=safe_ratio(result_rsa.keygen_time_avg_ms, result_ecc.keygen_time_avg_ms),
            ratio_sign=safe_ratio(result_rsa.sign_time_avg_ms, result_ecc.sign_time_avg_ms),
            ratio_verify=safe_ratio(result_rsa.verify_time_avg_ms, result_ecc.verify_time_avg_ms),
            ratio_key_size=safe_ratio(result_rsa.key_size_bits, result_ecc.key_size_bits),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ROUTES - DEMO ALICE & BOB (transaction détaillée)
# ============================================================

class AliceBobRequest(BaseModel):
    algo: str = "ECDSA"          # "RSA" | "ECDSA"
    message: str = "Virement de 250.00 EUR — Alice → Bob"
    # RSA params
    rsa_bits: int = 512          # taille de chaque premier (module = 2x)
    rsa_e: Optional[int] = None  # None → 65537
    # ECDSA params
    ecc_curve: str = "Ed25519"   # "Ed25519" | "P-256" | "secp256k1"
    ecc_seed: Optional[int] = None  # None → aléatoire


import hashlib as _hashlib
import random as _random

# ---- courbes ECDSA supportées ----
ECC_CURVES = {
    "Ed25519": {
        "prime": pow(2, 255) - 19,
        "a": -1,
        "d_num": -121665, "d_den": 121666,
        "Gx": 15112221349535400772501151409588531511454012693041857206046113283949847762202,
        "Gy": 46316835694926478169428394003475163141307993866256225615783033603165251855960,
        "bits": 255,
        "type": "Edwards",
        "equation": "ax² + y² = 1 + dx²y²",
        "security_bits": 128,
    },
    "P-256": {
        # NIST P-256 (secp256r1) — Weierstrass form: y² = x³ + ax + b (mod p)
        "prime": 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF,
        "a": -3,
        "b": 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
        "Gx": 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
        "Gy": 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
        "bits": 256,
        "type": "Weierstrass",
        "equation": "y² = x³ + ax + b (mod p)",
        "security_bits": 128,
    },
    "secp256k1": {
        # Bitcoin curve — y² = x³ + 7 (mod p)
        "prime": 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F,
        "a": 0,
        "b": 7,
        "Gx": 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
        "Gy": 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
        "bits": 256,
        "type": "Weierstrass",
        "equation": "y² = x³ + 7 (mod p)",
        "security_bits": 128,
    },
}


def _ecc_mod_inv(a, m):
    if a < 0:
        a = a % m
    u1, u2, u3 = 1, 0, a
    v1, v2, v3 = 0, 1, m
    while v3 != 0:
        q = u3 // v3
        v1, v2, v3, u1, u2, u3 = u1 - q*v1, u2 - q*v2, u3 - q*v3, v1, v2, v3
    return u1 % m


def _edwards_add(p1, p2, prime, a, d):
    x1, y1 = p1; x2, y2 = p2
    xn = (x1*y2 + y1*x2) % prime
    xd = (1 + d*x1*x2*y1*y2) % prime
    yn = (y1*y2 - a*x1*x2) % prime
    yd = (1 - d*x1*x2*y1*y2) % prime
    return (xn * _ecc_mod_inv(xd, prime)) % prime, (yn * _ecc_mod_inv(yd, prime)) % prime


def _weierstrass_add(p1, p2, prime):
    if p1 is None: return p2
    if p2 is None: return p1
    x1, y1 = p1; x2, y2 = p2
    if x1 == x2:
        if y1 != y2: return None
        lam = (3*x1*x1) * _ecc_mod_inv(2*y1, prime) % prime
    else:
        lam = (y2 - y1) * _ecc_mod_inv(x2 - x1, prime) % prime
    x3 = (lam*lam - x1 - x2) % prime
    y3 = (lam*(x1 - x3) - y1) % prime
    return x3, y3


def _scalar_mul_curve(curve_name, point, k, curve):
    prime = curve["prime"]
    if curve["type"] == "Edwards":
        a = curve["a"]
        d = (curve["d_num"] * _ecc_mod_inv(curve["d_den"], prime)) % prime
        add = lambda p, q: _edwards_add(p, q, prime, a, d)
        identity = (0, 1)
    else:
        add = lambda p, q: _weierstrass_add(p, q, prime)
        identity = None

    result = identity
    addend = point
    while k:
        if k & 1:
            result = add(result, addend) if result != identity else addend
        addend = add(addend, addend)
        k >>= 1
    return result


def _sha512_int(*parts):
    h = _hashlib.sha512()
    for p in parts:
        h.update(str(p).encode())
    return int(h.hexdigest(), 16)


def _sha512_hex(data: str) -> str:
    return _hashlib.sha512(data.encode()).hexdigest()


@app.post("/api/demo/alice-bob")
async def demo_alice_bob(req: AliceBobRequest):
    """
    Démo pédagogique complète Alice & Bob.
    Expose toutes les étapes cryptographiques avec paramètres détaillés.
    """
    import time as _time
    steps = []

    # ------------------------------------------------------------------ RSA
    if req.algo == "RSA":
        from core.rsa_engine import (
            generer_nombre_premier, pgcd, inverse_modulaire, hacher_message
        )
        bits = max(128, min(req.rsa_bits, 1024))  # limité pour la vitesse

        # 1. Génération des clés
        t0 = _time.perf_counter()
        p = generer_nombre_premier(bits)
        q = generer_nombre_premier(bits)
        while q == p:
            q = generer_nombre_premier(bits)
        n = p * q
        phi = (p - 1) * (q - 1)

        e = req.rsa_e if req.rsa_e and req.rsa_e > 1 and pgcd(req.rsa_e, phi) == 1 else 65537
        if pgcd(e, phi) != 1:
            e = 65537
        d = inverse_modulaire(e, phi)
        keygen_ms = (_time.perf_counter() - t0) * 1000

        pub_alice = (e, n)
        priv_alice = (d, n)

        # 2. Message → hash
        msg_hash = hacher_message(req.message)
        hash_hex = _hashlib.sha512(req.message.encode()).hexdigest()
        hash_reduit = msg_hash % n

        # 3. Signature (Alice signe avec sa clé privée)
        t1 = _time.perf_counter()
        signature = pow(hash_reduit, d, n)
        sign_ms = (_time.perf_counter() - t1) * 1000

        # 4. Vérification (Bob vérifie avec la clé publique d'Alice)
        t2 = _time.perf_counter()
        hash_decode = pow(signature, e, n)
        is_valid = (hash_decode == hash_reduit)
        verify_ms = (_time.perf_counter() - t2) * 1000

        return {
            "algo": "RSA",
            "params": {
                "bits_premier": bits,
                "bits_module": n.bit_length(),
                "e": e,
                "hash": "SHA-512",
            },
            "alice": {
                "role": "Expéditrice — signe le message",
                "cle_publique": {"e": e, "n_hex": hex(n), "n_bits": n.bit_length()},
                "cle_privee": {"d_hex": hex(d), "p_hex": hex(p), "q_hex": hex(q)},
                "keygen_ms": round(keygen_ms, 3),
            },
            "bob": {
                "role": "Destinataire — vérifie la signature",
                "cle_publique_alice": {"e": e, "n_hex": hex(n)},
            },
            "message": req.message,
            "message_bytes": req.message.encode().hex(),
            "hash_sha512": hash_hex,
            "hash_reduit_hex": hex(hash_reduit),
            "etapes_signature": [
                {"num": 1, "acteur": "Alice", "titre": "Hachage du message",
                 "detail": f"SHA-512(message) → {hash_hex[:32]}…", "valeur": hash_hex},
                {"num": 2, "acteur": "Alice", "titre": "Réduction mod n",
                 "detail": "hash_int mod n", "valeur": hex(hash_reduit)},
                {"num": 3, "acteur": "Alice", "titre": "Signature = hash^d mod n",
                 "detail": f"pow(hash_reduit, d, n)", "valeur": hex(signature)},
            ],
            "etapes_verification": [
                {"num": 1, "acteur": "Bob", "titre": "Réception signature + message",
                 "detail": "Bob reçoit le message en clair et la signature"},
                {"num": 2, "acteur": "Bob", "titre": "Hachage du message reçu",
                 "detail": f"SHA-512(message_reçu) → {hash_hex[:32]}…", "valeur": hash_hex},
                {"num": 3, "acteur": "Bob", "titre": "Déchiffrement = sig^e mod n",
                 "detail": "pow(signature, e, n)", "valeur": hex(hash_decode)},
                {"num": 4, "acteur": "Bob", "titre": "Comparaison des hashes",
                 "detail": f"hash_reçu == hash_déchiffré ? → {'✓ VALIDE' if is_valid else '✗ INVALIDE'}",
                 "valeur": str(is_valid)},
            ],
            "signature_hex": hex(signature),
            "signature_int": str(signature),
            "signature_bits": signature.bit_length(),
            "signature_bytes": (n.bit_length() + 7) // 8,
            "is_valid": is_valid,
            "sign_ms": round(sign_ms, 4),
            "verify_ms": round(verify_ms, 4),
            "keygen_ms": round(keygen_ms, 3),
            "security_bits": 80 if bits * 2 <= 1024 else 112 if bits * 2 <= 2048 else 128,
            "proprietes": {
                "probleme": "Factorisation de n = p × q",
                "sens_facile": "Multiplier deux grands premiers",
                "sens_difficile": "Factoriser n pour retrouver p et q",
            },
        }

    # ------------------------------------------------------------------ ECDSA
    else:
        curve_name = req.ecc_curve if req.ecc_curve in ECC_CURVES else "Ed25519"
        curve = ECC_CURVES[curve_name]
        prime = curve["prime"]
        G = (curve["Gx"], curve["Gy"])
        bits = curve["bits"]

        # Pré-calculer d pour Ed25519
        if curve["type"] == "Edwards":
            d_param = (curve["d_num"] * _ecc_mod_inv(curve["d_den"], prime)) % prime
        else:
            d_param = curve.get("b", 0)

        # 1. Keygen Alice
        t0 = _time.perf_counter()
        seed = req.ecc_seed if req.ecc_seed else _random.getrandbits(256)
        priv_alice = seed % (prime - 1) + 1
        pub_alice = _scalar_mul_curve(curve_name, G, priv_alice, curve)
        keygen_ms = (_time.perf_counter() - t0) * 1000

        # Keygen Bob (pour info)
        seed_bob = _random.getrandbits(256)
        priv_bob = seed_bob % (prime - 1) + 1
        pub_bob = _scalar_mul_curve(curve_name, G, priv_bob, curve)

        # 2. Hash message
        msg_int = int(req.message.encode().hex(), 16)
        hash_hex = _sha512_hex(req.message)
        h_int = int(hash_hex, 16) % prime

        # 3. Signature
        t1 = _time.perf_counter()
        r_seed = _sha512_int(msg_int, priv_alice, "nonce_banklab")
        r = r_seed % (prime - 1) + 1
        R = _scalar_mul_curve(curve_name, G, r, curve)
        h_sig = _sha512_int(R[0], R[1], pub_alice[0], pub_alice[1], msg_int) % prime
        s = r + h_sig * priv_alice
        sign_ms = (_time.perf_counter() - t1) * 1000

        # 4. Vérification
        t2 = _time.perf_counter()
        h_ver = _sha512_int(R[0], R[1], pub_alice[0], pub_alice[1], msg_int) % prime
        P1 = _scalar_mul_curve(curve_name, G, s, curve)
        h_pub = _scalar_mul_curve(curve_name, pub_alice, h_ver, curve)
        if curve["type"] == "Edwards":
            P2 = _edwards_add(R, h_pub, prime, curve["a"],
                              (curve["d_num"] * _ecc_mod_inv(curve["d_den"], prime)) % prime)
        else:
            P2 = _weierstrass_add(R, h_pub, prime)
        is_valid = P2 is not None and P1[0] == P2[0] and P1[1] == P2[1]
        verify_ms = (_time.perf_counter() - t2) * 1000

        return {
            "algo": "ECDSA",
            "courbe": curve_name,
            "params": {
                "courbe": curve_name,
                "type": curve["type"],
                "equation": curve["equation"],
                "prime_hex": hex(prime),
                "prime_bits": prime.bit_length(),
                "Gx_hex": hex(G[0]),
                "Gy_hex": hex(G[1]),
                "a": curve["a"],
                "b_ou_d": hex(d_param),
                "bits": bits,
                "hash": "SHA-512",
                "seed_utilise": seed,
            },
            "alice": {
                "role": "Expéditrice — signe le message",
                "cle_privee_hex": hex(priv_alice),
                "cle_privee_bits": priv_alice.bit_length(),
                "cle_publique": {
                    "Qx_hex": hex(pub_alice[0]),
                    "Qy_hex": hex(pub_alice[1]),
                    "formule": "Q = k × G (multiplication scalaire)"
                },
                "keygen_ms": round(keygen_ms, 3),
            },
            "bob": {
                "role": "Destinataire — vérifie la signature",
                "cle_privee_hex": hex(priv_bob),
                "cle_publique": {
                    "Qx_hex": hex(pub_bob[0]),
                    "Qy_hex": hex(pub_bob[1]),
                },
                "cle_publique_alice": {
                    "Qx_hex": hex(pub_alice[0]),
                    "Qy_hex": hex(pub_alice[1]),
                },
            },
            "message": req.message,
            "message_bytes": req.message.encode().hex(),
            "hash_sha512": hash_hex,
            "nonce_r": str(r),
            "point_R": {"x_hex": hex(R[0]), "y_hex": hex(R[1])},
            "challenge_h_hex": hex(h_sig),
            "s_hex": hex(s),
            "etapes_signature": [
                {"num": 1, "acteur": "Alice", "titre": "Hachage du message",
                 "detail": f"SHA-512(message)", "valeur": hash_hex},
                {"num": 2, "acteur": "Alice", "titre": "Génération nonce r (secret éphémère)",
                 "detail": "r = H(message, clé_privée, nonce) mod p", "valeur": str(r)},
                {"num": 3, "acteur": "Alice", "titre": "Calcul du point R = r × G",
                 "detail": "Multiplication scalaire sur la courbe", "valeur": f"({hex(R[0])[:18]}…, {hex(R[1])[:18]}…)"},
                {"num": 4, "acteur": "Alice", "titre": "Calcul du challenge h",
                 "detail": "h = H(R, Q_alice, message) mod p", "valeur": hex(h_sig)},
                {"num": 5, "acteur": "Alice", "titre": "Calcul de s",
                 "detail": "s = r + h × clé_privée", "valeur": hex(s)},
                {"num": 6, "acteur": "Alice", "titre": "Envoi de (R, s)",
                 "detail": "La signature est le couple (R, s)"},
            ],
            "etapes_verification": [
                {"num": 1, "acteur": "Bob", "titre": "Réception de (R, s) et du message"},
                {"num": 2, "acteur": "Bob", "titre": "Recalcul du challenge h",
                 "detail": "h = H(R, Q_alice, message) mod p", "valeur": hex(h_ver)},
                {"num": 3, "acteur": "Bob", "titre": "Calcul P1 = s × G",
                 "detail": "Multiplication scalaire", "valeur": f"({hex(P1[0])[:18]}…, {hex(P1[1])[:18]}…)"},
                {"num": 4, "acteur": "Bob", "titre": "Calcul P2 = R + h × Q_alice",
                 "detail": "Addition de points sur la courbe",
                 "valeur": f"({hex(P2[0])[:18]}…, {hex(P2[1])[:18]}…)" if P2 else "Point à l'infini"},
                {"num": 5, "acteur": "Bob", "titre": "Vérification P1 == P2",
                 "detail": f"P1 = P2 ? → {'✓ VALIDE' if is_valid else '✗ INVALIDE'}", "valeur": str(is_valid)},
            ],
            "signature": {"R_x_hex": hex(R[0]), "R_y_hex": hex(R[1]), "s_hex": hex(s)},
            "signature_bytes": 64,
            "is_valid": is_valid,
            "sign_ms": round(sign_ms, 4),
            "verify_ms": round(verify_ms, 4),
            "keygen_ms": round(keygen_ms, 3),
            "security_bits": curve["security_bits"],
            "proprietes": {
                "probleme": "Logarithme discret sur courbe elliptique (ECDLP)",
                "sens_facile": "k × G (multiplication scalaire, rapide)",
                "sens_difficile": "Retrouver k depuis Q = k × G (infaisable)",
            },
        }


# ============================================================
# ROUTES - ALGORITHME INFO
# ============================================================

@app.get("/api/algo/info/{algo}")
async def get_algo_info(algo: AlgoType, rsa_bits: int = 2048):
    """Retourne les informations détaillées sur un algorithme."""
    core_algo = CoreAlgo(algo.value)
    engine = CryptoEngine(core_algo, rsa_bits=rsa_bits // 2)
    return engine.get_algorithm_info()


@app.get("/api/algo/parametres")
async def get_parametres():
    """Retourne tous les paramètres disponibles pour les algorithmes."""
    return {
        "rsa": {
            "tailles_cles": [1024, 2048, 3072, 4096],
            "bits_securite": {1024: 80, 2048: 112, 3072: 128, 4096: 140},
            "e_public": 65537,
            "hash": "SHA-512",
            "nist_min_2030": 3072,
        },
        "ecdsa": {
            "courbe": "Ed25519",
            "taille_cle": 256,
            "bits_securite": 128,
            "hash": "SHA-512",
            "prime": "2^255 - 19",
            "equation": "ax² + y² = 1 + dx²y²",
            "a": -1,
        },
    }


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les événements en temps réel."""
    await manager.connect(websocket)
    try:
        # Envoi de l'état initial
        await websocket.send_json({
            "type": "connected",
            "data": {
                "bank_initialised": bank.is_initialised,
                "simulation_running": sim_running,
            },
            "timestamp": datetime.now().isoformat(),
        })

        while True:
            # Maintenir la connexion ouverte
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Ping/pong
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)





# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "BankLab API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": "/api/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}