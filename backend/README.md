# BankLab — Backend API

Système de test cryptographique bancaire comparant **RSA** et **ECDSA (Ed25519)**.


## Démarrage

```bash
pip install -r requirements.txt
python start.py
```

## Structure

```
banklab/
├── main.py              # Application FastAPI principale
├── start.py             # Script de démarrage
├── requirements.txt
├── core/
│   ├── RSA.py           # Module RSA original (conservé intact)
│   ├── ecdsa.py         # Module ECDSA original (conservé intact)
│   ├── rsa_engine.py    # Wrapper RSA sans prints, avec métriques
│   ├── ecdsa_engine.py  # Wrapper ECDSA sans prints, avec métriques
│   └── crypto_engine.py # Interface unifiée CryptoEngine
├── models/
│   └── __init__.py      # Modèles Pydantic (transactions, comptes, benchmarks)
└── services/
    ├── __init__.py
    └── banking.py       # BankingService + BenchmarkService
```


## Endpoints principaux

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/status` | État de la banque |
| POST | `/api/banque/initialiser` | Initialiser la banque |
| GET | `/api/banque/comptes` | Liste des comptes |
| POST | `/api/transaction` | Créer une transaction |
| POST | `/api/transaction/aleatoire` | Transaction aléatoire |
| GET | `/api/transactions` | Historique |
| POST | `/api/simulation/demarrer` | Démarrer simulation |
| POST | `/api/benchmark` | Benchmark cryptographique |
| POST | `/api/benchmark/comparaison` | Comparaison RSA vs ECDSA |
| WS | `/ws` | WebSocket temps réel |

## Configuration BanqueConfig

```json
{
  "nom": "BankLab",
  "algo": "ECDSA",
  "rsa_key_bits": 2048,
  "nb_comptes": 5,
  "tps_cible": 1.0
}
```

## Format Transaction (ISO 8583-inspiré)

```json
{
  "reference": "TXN123456",
  "type_transaction": "PAIEMENT_CB",
  "montant": 42.50,
  "devise": "EUR",
  "mcc": "5411",
  "marchand": "Carrefour Market",
  "compte_source": "FR76...",
  "status": "APPROUVE",
  "metrics": {
    "algo": "ECDSA",
    "sign_time_ms": 98.5,
    "verify_time_ms": 134.2,
    "key_size_bits": 256,
    "signature_size_bytes": 64,
    "security_bits": 128
  }
}
```

## Notes de sécurité

- Les modules RSA.py et ecdsa.py originaux sont préservés dans `core/`
- Les wrappers (`rsa_engine.py`, `ecdsa_engine.py`) suppriment les `print()` 
  et ajoutent la mesure de performance précise
- L'interface `CryptoEngine` unifie les deux algorithmes
- Les clés privées ne sont jamais exposées dans l'API
