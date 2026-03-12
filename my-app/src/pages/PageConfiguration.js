import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

const RSA_SIZES = [
  { bits: 1024, label: '1024 bits', security: 80, warning: 'Obsolète' },
  { bits: 2048, label: '2048 bits', security: 112, warning: null },
  { bits: 3072, label: '3072 bits', security: 128, warning: 'Recommandé NIST' },
  { bits: 4096, label: '4096 bits', security: 140, warning: null },
];

export default function PageConfiguration({ bankStatus, refreshStatus }) {
  const [algo, setAlgo] = useState('ECDSA');
  const [rsaBits, setRsaBits] = useState(2048);
  const [nbComptes, setNbComptes] = useState(5);
  const [nomBanque, setNomBanque] = useState('BankLab Testbed');
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState([]);
  const [algoInfo, setAlgoInfo] = useState(null);
  const [algoParams, setAlgoParams] = useState(null);

  useEffect(() => {
    api.algoParams().then(setAlgoParams).catch(() => {});
  }, []);

  useEffect(() => {
    api.algoInfo(algo, rsaBits).then(setAlgoInfo).catch(() => {});
  }, [algo, rsaBits]);

  const addLog = (msg, type = 'info') => {
    setLog(prev => [...prev, { msg, type, t: new Date().toLocaleTimeString('fr-FR') }]);
  };

  const handleInit = async () => {
    setLoading(true);
    setLog([]);
    addLog(`Initialisation de la banque "${nomBanque}"...`, 'accent');
    addLog(`Algorithme sélectionné : ${algo}${algo === 'RSA' ? ` ${rsaBits} bits` : ' Ed25519 256 bits'}`, 'info');
    addLog(`Génération de ${nbComptes} paires de clés en cours...`, 'info');

    try {
      const res = await api.initBank({
        nom: nomBanque,
        algo,
        rsa_key_bits: rsaBits,
        nb_comptes: nbComptes,
        tps_cible: 1.0,
      });
      addLog(`Banque initialisée avec succès.`, 'success');
      addLog(`${res.nb_comptes} comptes créés avec clés ${res.algo}.`, 'success');
      refreshStatus();
    } catch (e) {
      addLog(`Erreur : ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const isRSA = algo === 'RSA';

  return (
    <div>
      <div className="page-header">
        <div className="page-title">CONFIGURATION</div>
        <div className="page-subtitle">
          Paramétrage de la banque virtuelle et sélection de l'algorithme cryptographique
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* LEFT — Setup */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Bank name */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Paramètres de la Banque</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="form-group">
                <label className="form-label">Nom de la banque</label>
                <input
                  className="form-control"
                  value={nomBanque}
                  onChange={e => setNomBanque(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Nombre de comptes virtuels</label>
                <input
                  type="range" min={2} max={10} value={nbComptes}
                  onChange={e => setNbComptes(+e.target.value)}
                  style={{ marginBottom: 4 }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--gray-500)' }}>
                  <span>2</span>
                  <span style={{ color: 'var(--black)', fontWeight: 600 }}>{nbComptes} comptes</span>
                  <span>10</span>
                </div>
              </div>
            </div>
          </div>

          {/* Algorithm selection */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Algorithme Cryptographique</span>
            </div>
            <div className="seg-control" style={{ width: '100%', marginBottom: 16 }}>
              <button
                className={`seg-btn ${algo === 'ECDSA' ? 'active' : ''}`}
                style={{ flex: 1 }}
                onClick={() => setAlgo('ECDSA')}
              >
                ECDSA / Ed25519
              </button>
              <button
                className={`seg-btn ${algo === 'RSA' ? 'active' : ''}`}
                style={{ flex: 1 }}
                onClick={() => setAlgo('RSA')}
              >
                RSA
              </button>
            </div>

            {isRSA && (
              <div className="form-group" style={{ marginBottom: 4 }}>
                <label className="form-label">Taille de la clé RSA</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {RSA_SIZES.map(s => (
                    <button
                      key={s.bits}
                      onClick={() => setRsaBits(s.bits)}
                      style={{
                        padding: '10px 12px',
                        border: rsaBits === s.bits ? '2px solid var(--black)' : '1px solid var(--gray-200)',
                        background: rsaBits === s.bits ? 'var(--black)' : 'var(--white)',
                        color: rsaBits === s.bits ? 'var(--white)' : 'var(--gray-700)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <div style={{ fontWeight: 600 }}>{s.label}</div>
                      <div style={{ fontSize: 9, opacity: 0.7, marginTop: 2 }}>
                        {s.security} bits sécurité
                        {s.warning && ` — ${s.warning}`}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {!isRSA && (
              <div style={{
                background: 'var(--gray-50)', border: 'var(--border)',
                padding: 14, fontFamily: 'var(--font-mono)', fontSize: 11
              }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Ed25519 — Courbe d'Edwards tordue</div>
                <div style={{ color: 'var(--gray-500)', lineHeight: 1.7, fontSize: 10 }}>
                  Clé privée : 256 bits<br />
                  Clé publique : 256 bits (point sur courbe)<br />
                  Signature : 64 octets (R, s)<br />
                  Sécurité : 128 bits (équivalent AES-128)
                </div>
              </div>
            )}
          </div>

          {/* Launch button */}
          <button
            className="btn btn-primary"
            onClick={handleInit}
            disabled={loading}
            style={{ padding: '14px 20px', fontSize: 12, letterSpacing: '0.15em' }}
          >
            {loading ? (
              <><span className="spinner" style={{ borderTopColor: 'var(--white)', borderColor: 'rgba(255,255,255,0.3)' }} /> Génération des clés...</>
            ) : (
              <>▶ INITIALISER LA BANQUE</>
            )}
          </button>

          {/* Current status */}
          {bankStatus?.initialise && (
            <div className="card" style={{ borderTop: '2px solid var(--black)' }}>
              <div className="card-header">
                <span className="card-title">État Actuel</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--gray-400)' }}>
                  <span className="status-dot green" />Opérationnel
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  ['Algorithme', bankStatus.algo],
                  ['Comptes', bankStatus.nb_comptes],
                  ['Transactions', bankStatus.nb_transactions],
                  ['Banque', bankStatus.config?.nom || 'BankLab'],
                ].map(([k, v]) => (
                  <div key={k} style={{ padding: '8px 0', borderBottom: 'var(--border)' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 3 }}>{k}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600 }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT — Algo info + log */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Algo technical sheet */}
          {algoInfo && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Fiche Technique — {algoInfo.name}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                {[
                  ['Algorithme complet', algoInfo.full_name],
                  ['Type', algoInfo.type],
                  ['Taille de clé', `${algoInfo.key_size_bits} bits`],
                  ['Bits de sécurité', `${algoInfo.security_bits} bits`],
                  ['Taille signature', `${algoInfo.signature_size_bytes} octets`],
                  ['Fonction de hash', algoInfo.hash_function],
                  ['Problème mathématique', algoInfo.problem],
                  ['Recommandation NIST', algoInfo.nist_recommendation],
                  ...(algoInfo.curve ? [['Courbe', algoInfo.curve]] : []),
                  ...(algoInfo.prime ? [['Module premier', algoInfo.prime]] : []),
                ].map(([k, v]) => (
                  <div key={k} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '9px 0', borderBottom: 'var(--border)',
                    alignItems: 'baseline', gap: 8,
                  }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--gray-500)', flexShrink: 0 }}>{k}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500, textAlign: 'right' }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Comparison quick */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Comparaison Rapide RSA vs ECDSA</span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '6px 0', borderBottom: 'var(--border)', color: 'var(--gray-500)', fontWeight: 400 }}>Critère</th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', borderBottom: 'var(--border)', color: 'var(--gray-500)', fontWeight: 400 }}>RSA-3072</th>
                  <th style={{ textAlign: 'right', padding: '6px 0', borderBottom: 'var(--border)', color: 'var(--gray-500)', fontWeight: 400 }}>Ed25519</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Clé privée', '384 octets', '32 octets'],
                  ['Clé publique', '384 octets', '32 octets'],
                  ['Signature', '384 octets', '64 octets'],
                  ['Sécurité', '128 bits', '128 bits'],
                  ['Keygen (ref)', 'Lente', 'Rapide'],
                  ['Signature (ref)', 'Lente', 'Rapide'],
                  ['Vérification (ref)', 'Très rapide', 'Rapide'],
                  ['Résistance quantique', 'Non', 'Non'],
                ].map(([k, rsa, ecc]) => (
                  <tr key={k}>
                    <td style={{ padding: '7px 0', borderBottom: 'var(--border)', color: 'var(--gray-600)' }}>{k}</td>
                    <td style={{ padding: '7px 8px', borderBottom: 'var(--border)', textAlign: 'right', color: algo === 'RSA' ? 'var(--black)' : 'var(--gray-400)', fontWeight: algo === 'RSA' ? 600 : 400 }}>{rsa}</td>
                    <td style={{ padding: '7px 0', borderBottom: 'var(--border)', textAlign: 'right', color: algo === 'ECDSA' ? 'var(--black)' : 'var(--gray-400)', fontWeight: algo === 'ECDSA' ? 600 : 400 }}>{ecc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Log */}
          {log.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Journal d'Initialisation</span>
              </div>
              <div className="terminal">
                {log.map((l, i) => (
                  <span key={i} className={`terminal-line ${l.type}`}>
                    <span className="terminal-prompt">[{l.t}]</span>
                    {l.msg}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
