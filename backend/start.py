#!/usr/bin/env python3
"""
BankLab - Script de démarrage du serveur backend
"""
import sys
import os

# Ajouter le répertoire courant au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  BankLab API — Démarrage du serveur")
    print("=" * 60)
    print("  Algorithmes : RSA (1024–4096 bits) | ECDSA Ed25519")
    print("  Documentation : http://localhost:8000/api/docs")
    print("  WebSocket    : ws://localhost:8000/ws")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
