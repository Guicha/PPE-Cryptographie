import React, { useState, useCallback } from 'react';
import { formatMs } from '../utils/api';

// ─── Constantes ──────────────────────────────────────────────────────────────

const BASE = 'http://localhost:8000';

const ECC_CURVES = [
  { id: 'Ed25519',    label: 'Ed25519',    type: 'Edwards',     bits: 255, info: 'Courbe recommandée par NIST, utilisée dans SSH/TLS modernes' },
  { id: 'P-256',      label: 'P-256',      type: 'Weierstrass', bits: 256, info: 'NIST P-256, standard TLS/HTTPS, utilisée dans les cartes bancaires EMV' },
  { id: 'secp256k1',  label: 'secp256k1',  type: 'Weierstrass', bits: 256, info: 'Courbe de Bitcoin et Ethereum, coefficiant a=0' },
];

const RSA_BITS_PRESETS = [
  { bits: 128,  label: '256 bits',   note: '⚠ Démo seulement',   color: '#dc2626' },
  { bits: 256,  label: '512 bits',   note: '⚠ Cassable',          color: '#ea580c' },
  { bits: 512,  label: '1024 bits',  note: '⚠ Faible',            color: '#d97706' },
  { bits: 1024, label: '2048 bits',  note: '✓ Acceptable',        color: '#65a30d' },
];

const E_PRESETS = [
  { v: 3,     label: 'e = 3',      note: 'Historique, risqué' },
  { v: 17,    label: 'e = 17',     note: 'Fermat F₂' },
  { v: 257,   label: 'e = 257',    note: 'Fermat F₃' },
  { v: 65537, label: 'e = 65537', note: 'F₄ — Standard PKCS#1' },
];

// ─── Helpers UI ──────────────────────────────────────────────────────────────

const mono = { fontFamily: 'var(--font-mono)' };

function Tag({ children, style }) {
  return (
    <span style={{
      display: 'inline-block', padding: '1px 7px',
      fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em',
      border: '1px solid var(--gray-300)', color: 'var(--gray-500)',
      ...style,
    }}>{children}</span>
  );
}

function SectionTitle({ children }) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.2em',
      textTransform: 'uppercase', color: 'var(--gray-400)',
      borderBottom: '1px solid var(--gray-100)', paddingBottom: 8, marginBottom: 14,
    }}>{children}</div>
  );
}

function KV({ k, v, mono: isMono = true, trunc = false, copyable = false }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(v).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1200); });
  };
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '5px 0', borderBottom: '1px solid var(--gray-50)', gap: 12 }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)', whiteSpace: 'nowrap', flexShrink: 0 }}>{k}</span>
      <span style={{
        fontFamily: isMono ? 'var(--font-mono)' : 'var(--font-sans)', fontSize: 10, fontWeight: 500,
        textAlign: 'right', wordBreak: 'break-all',
        maxWidth: trunc ? 260 : 'none',
        overflow: trunc ? 'hidden' : 'visible',
        textOverflow: trunc ? 'ellipsis' : 'clip',
        whiteSpace: trunc ? 'nowrap' : 'normal',
        cursor: copyable ? 'pointer' : 'default',
        color: copyable ? (copied ? '#16a34a' : 'var(--black)') : 'var(--black)',
      }} onClick={copyable ? handleCopy : undefined} title={copyable ? 'Cliquer pour copier' : v}>
        {copied ? '✓ copié' : v}
      </span>
    </div>
  );
}

function HexBox({ label, value, rows = 3 }) {
  const [open, setOpen] = useState(false);
  const preview = value ? value.slice(0, 64) + (value.length > 64 ? '…' : '') : '—';
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>{label}</span>
        {value && value.length > 64 && (
          <button onClick={() => setOpen(o => !o)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>
            {open ? '▲ réduire' : '▼ tout voir'}
          </button>
        )}
      </div>
      <div style={{
        background: 'var(--gray-50)', border: 'var(--border)',
        padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: 10,
        wordBreak: 'break-all', lineHeight: 1.6, color: 'var(--gray-700)',
        maxHeight: open ? 'none' : '3.5em', overflow: 'hidden',
      }}>
        {open ? value : preview}
      </div>
    </div>
  );
}

// Étape signée dans le flux de l'échange
function StepBubble({ step, actor }) {
  const isAlice = actor === 'Alice';
  return (
    <div style={{
      display: 'flex', flexDirection: isAlice ? 'row' : 'row-reverse',
      alignItems: 'flex-start', gap: 10, marginBottom: 12,
    }}>
      {/* Avatar */}
      <div style={{
        width: 28, height: 28, flexShrink: 0,
        background: isAlice ? 'var(--black)' : 'var(--gray-200)',
        color: isAlice ? 'var(--white)' : 'var(--black)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
      }}>{isAlice ? 'A' : 'B'}</div>
      {/* Bulle */}
      <div style={{
        flex: 1, background: isAlice ? 'var(--black)' : 'var(--gray-50)',
        border: isAlice ? 'none' : 'var(--border)',
        padding: '10px 14px',
        color: isAlice ? 'var(--white)' : 'var(--black)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, opacity: 0.7 }}>ÉTAPE {step.num}</span>
          <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 600 }}>{step.titre}</span>
        </div>
        {step.detail && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, opacity: 0.8, marginBottom: step.valeur ? 4 : 0 }}>
            {step.detail}
          </div>
        )}
        {step.valeur && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            background: isAlice ? 'rgba(255,255,255,0.1)' : 'var(--white)',
            border: isAlice ? '1px solid rgba(255,255,255,0.2)' : 'var(--border)',
            padding: '4px 8px', marginTop: 4, wordBreak: 'break-all',
            maxHeight: 40, overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {step.valeur.length > 80 ? step.valeur.slice(0, 80) + '…' : step.valeur}
          </div>
        )}
      </div>
    </div>
  );
}

// Chrono comparison bar
function TimingBar({ sign, verify, keygen }) {
  const max = Math.max(sign, verify, keygen, 0.01);
  const bar = (val, label, pct) => (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700 }}>{formatMs(val)}</span>
      </div>
      <div style={{ height: 6, background: 'var(--gray-100)' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: 'var(--black)', transition: 'width 0.6s ease' }} />
      </div>
    </div>
  );
  return (
    <div>
      {bar(keygen, 'Génération de clés', (keygen / max) * 100)}
      {bar(sign,   'Signature',          (sign / max) * 100)}
      {bar(verify, 'Vérification',       (verify / max) * 100)}
    </div>
  );
}

// ─── Composant principal ──────────────────────────────────────────────────────

export default function PageTransaction() {
  // Paramètres communs
  const [algo, setAlgo] = useState('ECDSA');
  const [message, setMessage] = useState('Virement de 250.00 EUR — Alice → Bob [ref:TX-2024]');

  // Params RSA
  const [rsaBits, setRsaBits] = useState(256);
  const [rsaE, setRsaE] = useState(65537);
  const [rsaECustom, setRsaECustom] = useState('');

  // Params ECDSA
  const [eccCurve, setEccCurve] = useState('Ed25519');
  const [eccSeed, setEccSeed] = useState('');
  const [randomSeed, setRandomSeed] = useState(true);

  // État résultat
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('flux'); // 'flux' | 'alice' | 'bob' | 'params' | 'signature'

  const effectiveE = rsaECustom ? parseInt(rsaECustom) : rsaE;

  const handleRun = useCallback(async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const body = {
        algo,
        message,
        rsa_bits: rsaBits,
        rsa_e: algo === 'RSA' ? effectiveE : null,
        ecc_curve: eccCurve,
        ecc_seed: algo === 'ECDSA' && !randomSeed && eccSeed ? parseInt(eccSeed) : null,
      };
      const resp = await fetch(`${BASE}/api/demo/alice-bob`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || resp.statusText);
      }
      const data = await resp.json();
      setResult(data);
      setActiveTab('flux');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [algo, message, rsaBits, effectiveE, eccCurve, eccSeed, randomSeed]);

  const curveInfo = ECC_CURVES.find(c => c.id === eccCurve);

  // ── Rendu ─────────────────────────────────────────────────────────────────
  return (
    <div>
      <div className="page-header">
        <div className="page-title">ÉCHANGE ALICE & BOB</div>
        <div className="page-subtitle">
          Simulation d'une transaction signée cryptographiquement — exposition complète des étapes, paramètres et données internes
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 20, alignItems: 'start' }}>

        {/* ── PANNEAU GAUCHE : configuration ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* Sélection algorithme */}
          <div className="card">
            <SectionTitle>Algorithme</SectionTitle>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {['RSA', 'ECDSA'].map(a => (
                <button key={a} onClick={() => setAlgo(a)} style={{
                  padding: '10px 0', fontFamily: 'var(--font-display)', fontSize: 16,
                  letterSpacing: '0.1em', cursor: 'pointer',
                  background: algo === a ? 'var(--black)' : 'var(--white)',
                  color: algo === a ? 'var(--white)' : 'var(--black)',
                  border: '1px solid var(--black)',
                  transition: 'all 0.15s',
                }}>
                  {a}
                </button>
              ))}
            </div>
          </div>

          {/* Message */}
          <div className="card">
            <SectionTitle>Message (Alice → Bob)</SectionTitle>
            <textarea
              value={message} onChange={e => setMessage(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box',
                fontFamily: 'var(--font-mono)', fontSize: 11,
                border: 'var(--border)', padding: '8px 10px',
                resize: 'vertical', minHeight: 70, lineHeight: 1.5,
              }}
            />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)', marginTop: 4 }}>
              {message.length} octets · SHA-512 → 512 bits
            </div>
          </div>

          {/* Params RSA */}
          {algo === 'RSA' && (
            <div className="card">
              <SectionTitle>Paramètres RSA</SectionTitle>

              <div style={{ marginBottom: 14 }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 8 }}>TAILLE DES PREMIERS p, q</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                  {RSA_BITS_PRESETS.map(p => (
                    <button key={p.bits} onClick={() => setRsaBits(p.bits)} style={{
                      padding: '8px 6px', cursor: 'pointer', textAlign: 'left',
                      border: rsaBits === p.bits ? '1px solid var(--black)' : 'var(--border)',
                      background: rsaBits === p.bits ? 'var(--black)' : 'transparent',
                      color: rsaBits === p.bits ? 'var(--white)' : 'var(--black)',
                      transition: 'all 0.1s',
                    }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700 }}>{p.label}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, opacity: 0.7, color: rsaBits === p.bits ? 'rgba(255,255,255,0.7)' : p.color }}>{p.note}</div>
                    </button>
                  ))}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)', marginTop: 6 }}>
                  Module n = p × q = {rsaBits * 2} bits
                </div>
              </div>

              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 8 }}>EXPOSANT PUBLIC e</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
                  {E_PRESETS.map(ep => (
                    <button key={ep.v} onClick={() => { setRsaE(ep.v); setRsaECustom(''); }} style={{
                      padding: '6px 8px', cursor: 'pointer', textAlign: 'left',
                      border: rsaE === ep.v && !rsaECustom ? '1px solid var(--black)' : 'var(--border)',
                      background: rsaE === ep.v && !rsaECustom ? 'var(--black)' : 'transparent',
                      color: rsaE === ep.v && !rsaECustom ? 'var(--white)' : 'var(--black)',
                    }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600 }}>{ep.label}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, opacity: 0.65 }}>{ep.note}</div>
                    </button>
                  ))}
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">e personnalisé (impair, pgcd(e,φ)=1)</label>
                  <input className="form-control" type="number" placeholder="ex: 65537"
                    value={rsaECustom} onChange={e => setRsaECustom(e.target.value)} />
                </div>
              </div>

              {/* Info maths */}
              <div style={{ marginTop: 12, padding: '10px', background: 'var(--gray-50)', border: 'var(--border)' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 4 }}>RAPPEL MATHÉMATIQUE</div>
                {[
                  'n = p × q (module public)',
                  'φ(n) = (p−1)(q−1) (secret)',
                  'd = e⁻¹ mod φ(n) (clé privée)',
                  'sign = hash^d mod n',
                  'verify : hash^e mod n == sign^e mod n',
                ].map(l => <div key={l} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-600)', lineHeight: 1.8 }}>› {l}</div>)}
              </div>
            </div>
          )}

          {/* Params ECDSA */}
          {algo === 'ECDSA' && (
            <div className="card">
              <SectionTitle>Paramètres ECDSA</SectionTitle>

              <div style={{ marginBottom: 14 }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 8 }}>COURBE ELLIPTIQUE</div>
                {ECC_CURVES.map(c => (
                  <button key={c.id} onClick={() => setEccCurve(c.id)} style={{
                    width: '100%', padding: '10px 12px', cursor: 'pointer', textAlign: 'left',
                    border: eccCurve === c.id ? '1px solid var(--black)' : 'var(--border)',
                    background: eccCurve === c.id ? 'var(--black)' : 'transparent',
                    color: eccCurve === c.id ? 'var(--white)' : 'var(--black)',
                    marginBottom: 6, transition: 'all 0.1s',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700 }}>{c.label}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, opacity: 0.7 }}>{c.type} · {c.bits} bits</span>
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, opacity: 0.65 }}>{c.info}</div>
                  </button>
                ))}
              </div>

              {curveInfo && (
                <div style={{ padding: '10px', background: 'var(--gray-50)', border: 'var(--border)', marginBottom: 14 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 4 }}>ÉQUATION</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600 }}>
                    {curveInfo.id === 'Ed25519' ? 'ax² + y² = 1 + dx²y²' : curveInfo.id === 'secp256k1' ? 'y² = x³ + 7 (mod p)' : 'y² = x³ + ax + b (mod p)'}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginTop: 4 }}>
                    Sécurité : ~128 bits (équiv. AES-128)
                  </div>
                </div>
              )}

              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 8 }}>SEED NONCE (r)</div>
                <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                  {[true, false].map(r => (
                    <button key={String(r)} onClick={() => setRandomSeed(r)} style={{
                      flex: 1, padding: '7px', cursor: 'pointer',
                      border: randomSeed === r ? '1px solid var(--black)' : 'var(--border)',
                      background: randomSeed === r ? 'var(--black)' : 'transparent',
                      color: randomSeed === r ? 'var(--white)' : 'var(--black)',
                      fontFamily: 'var(--font-mono)', fontSize: 9,
                    }}>
                      {r ? '⟳ Aléatoire' : '✎ Manuel'}
                    </button>
                  ))}
                </div>
                {!randomSeed && (
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Seed (entier 256 bits)</label>
                    <input className="form-control" type="number" placeholder="ex: 42"
                      value={eccSeed} onChange={e => setEccSeed(e.target.value)} />
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#dc2626', marginTop: 4 }}>
                      ⚠ En production, le seed doit être aléatoire et secret
                    </div>
                  </div>
                )}
                <div style={{ padding: '10px', background: 'var(--gray-50)', border: 'var(--border)', marginTop: 10 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 4 }}>RAPPEL MATHÉMATIQUE</div>
                  {[
                    'Q = k × G (clé publique, mult. scalaire)',
                    'R = r × G (point éphémère)',
                    'h = H(R, Q_alice, message)',
                    's = r + h × k_privée',
                    'Vérif : s×G == R + h×Q',
                  ].map(l => <div key={l} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-600)', lineHeight: 1.8 }}>› {l}</div>)}
                </div>
              </div>
            </div>
          )}

          {/* Bouton exécuter */}
          <button className="btn btn-primary" onClick={handleRun} disabled={loading} style={{ padding: '14px', fontFamily: 'var(--font-display)', fontSize: 18, letterSpacing: '0.08em' }}>
            {loading
              ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                  <span className="spinner" style={{ borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} />
                  Calcul en cours…
                </span>
              : '▶ EXÉCUTER LA TRANSACTION'
            }
          </button>

          {error && (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#dc2626', padding: 10, background: '#fef2f2', border: '1px solid #fecaca' }}>
              {error}
            </div>
          )}
        </div>

        {/* ── PANNEAU DROIT : résultats ── */}
        <div>
          {!result && !loading && (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              minHeight: 500, border: '1px dashed var(--gray-200)', gap: 16,
            }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 48, color: 'var(--gray-100)', letterSpacing: '0.05em' }}>A → B</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-400)' }}>
                Configurez les paramètres et lancez la transaction
              </div>
            </div>
          )}

          {loading && (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              minHeight: 500, gap: 16,
            }}>
              <span className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-500)' }}>
                {algo === 'RSA' ? 'Génération des nombres premiers…' : 'Multiplication scalaire sur la courbe…'}
              </div>
            </div>
          )}

          {result && (
            <div>
              {/* Header résultat */}
              <div className="card" style={{ borderTop: `3px solid var(--black)`, marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, letterSpacing: '0.05em' }}>
                      {result.algo === 'RSA' ? `RSA-${result.params.bits_module}` : `ECDSA — ${result.courbe}`}
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginTop: 2 }}>
                      {result.proprietes?.probleme}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <div className="stat-block" style={{ minWidth: 80 }}>
                      <div className="stat-label">Signature</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>{formatMs(result.sign_ms)}</div>
                    </div>
                    <div className="stat-block" style={{ minWidth: 80 }}>
                      <div className="stat-label">Vérification</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>{formatMs(result.verify_ms)}</div>
                    </div>
                    <div className="stat-block" style={{ minWidth: 80 }}>
                      <div className="stat-label">Keygen</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>{formatMs(result.keygen_ms)}</div>
                    </div>
                    <div className="stat-block" style={{ minWidth: 80 }}>
                      <div className="stat-label">Sig. taille</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>{result.signature_bytes}B</div>
                    </div>
                    <div className="stat-block" style={{ minWidth: 80 }}>
                      <div className="stat-label">Sécurité</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>{result.security_bits}b</div>
                    </div>
                  </div>
                  <div>
                    <span style={{
                      fontFamily: 'var(--font-display)', fontSize: 14, letterSpacing: '0.1em',
                      padding: '4px 14px',
                      background: result.is_valid ? 'var(--black)' : '#dc2626',
                      color: 'var(--white)',
                    }}>
                      {result.is_valid ? '✓ SIGNATURE VALIDE' : '✗ INVALIDE'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Onglets */}
              <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: 'var(--border)' }}>
                {[
                  ['flux', '⇄ Flux Alice-Bob'],
                  ['alice', '👤 Alice'],
                  ['bob', '👤 Bob'],
                  ['params', '⚙ Paramètres'],
                  ['signature', '🔏 Signature'],
                ].map(([id, label]) => (
                  <button key={id} onClick={() => setActiveTab(id)} style={{
                    padding: '8px 16px', cursor: 'pointer', border: 'none',
                    borderBottom: activeTab === id ? '2px solid var(--black)' : '2px solid transparent',
                    background: 'none',
                    fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: activeTab === id ? 700 : 400,
                    color: activeTab === id ? 'var(--black)' : 'var(--gray-500)',
                    transition: 'all 0.1s', marginBottom: -1,
                  }}>
                    {label}
                  </button>
                ))}
              </div>

              {/* ═══ Onglet : Flux Alice-Bob ═══ */}
              {activeTab === 'flux' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  {/* Alice signe */}
                  <div className="card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                      <div style={{ width: 36, height: 36, background: 'var(--black)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-display)', fontSize: 18 }}>A</div>
                      <div>
                        <div style={{ fontFamily: 'var(--font-display)', fontSize: 16, letterSpacing: '0.05em' }}>ALICE</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>{result.alice.role}</div>
                      </div>
                    </div>
                    <SectionTitle>Étapes de signature</SectionTitle>
                    {(result.etapes_signature || []).map(s => <StepBubble key={s.num} step={s} actor="Alice" />)}
                  </div>
                  {/* Bob vérifie */}
                  <div className="card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, flexDirection: 'row-reverse', textAlign: 'right' }}>
                      <div style={{ width: 36, height: 36, background: 'var(--gray-200)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-display)', fontSize: 18 }}>B</div>
                      <div>
                        <div style={{ fontFamily: 'var(--font-display)', fontSize: 16, letterSpacing: '0.05em' }}>BOB</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>{result.bob.role}</div>
                      </div>
                    </div>
                    <SectionTitle>Étapes de vérification</SectionTitle>
                    {(result.etapes_verification || []).map(s => <StepBubble key={s.num} step={s} actor="Bob" />)}
                  </div>

                  {/* Message envoyé */}
                  <div className="card" style={{ gridColumn: '1 / -1' }}>
                    <SectionTitle>Message transmis en clair</SectionTitle>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <KV k="Message texte" v={result.message} isMono={false} />
                        <KV k="Encodage hex" v={result.message_bytes} trunc copyable />
                        <KV k="Longueur" v={`${result.message.length} caractères`} />
                      </div>
                      <div>
                        <HexBox label="Hash SHA-512 (512 bits)" value={result.hash_sha512} />
                      </div>
                    </div>
                  </div>

                  {/* Timing */}
                  <div className="card" style={{ gridColumn: '1 / -1' }}>
                    <SectionTitle>Performance chronologique</SectionTitle>
                    <TimingBar sign={result.sign_ms} verify={result.verify_ms} keygen={result.keygen_ms} />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginTop: 12 }}>
                      {[
                        ['Clé générée par Alice', formatMs(result.keygen_ms), '(une seule fois)'],
                        ['Alice signe', formatMs(result.sign_ms), 'par transaction'],
                        ['Bob vérifie', formatMs(result.verify_ms), 'par transaction'],
                      ].map(([l, v, s]) => (
                        <div key={l} style={{ padding: '10px', background: 'var(--gray-50)', textAlign: 'center' }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 4 }}>{l}</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>{v}</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>{s}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ═══ Onglet : Alice ═══ */}
              {activeTab === 'alice' && (
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <div style={{ width: 48, height: 48, background: 'var(--black)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-display)', fontSize: 26 }}>A</div>
                    <div>
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, letterSpacing: '0.05em' }}>ALICE — Expéditrice</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--gray-500)' }}>Possède la clé privée · signe le message · publie sa clé publique</div>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    <div>
                      <SectionTitle>🔓 Clé Publique (partagée avec Bob)</SectionTitle>
                      {result.algo === 'RSA' ? (
                        <>
                          <KV k="Exposant e" v={String(result.alice.cle_publique.e)} />
                          <KV k="Module n (bits)" v={String(result.alice.cle_publique.n_bits)} />
                          <HexBox label="Module n (hex)" value={result.alice.cle_publique.n_hex} />
                        </>
                      ) : (
                        <>
                          <KV k="Courbe" v={result.courbe} />
                          <KV k="Formule" v={result.alice.cle_publique.formule} isMono={false} />
                          <HexBox label="Q.x (hex)" value={result.alice.cle_publique.Qx_hex} />
                          <HexBox label="Q.y (hex)" value={result.alice.cle_publique.Qy_hex} />
                        </>
                      )}
                    </div>

                    <div>
                      <SectionTitle>🔒 Clé Privée (SECRÈTE — visible à des fins pédagogiques)</SectionTitle>
                      {result.algo === 'RSA' ? (
                        <>
                          <HexBox label="d (exposant privé)" value={result.alice.cle_privee.d_hex} />
                          <HexBox label="p (premier secret)" value={result.alice.cle_privee.p_hex} />
                          <HexBox label="q (premier secret)" value={result.alice.cle_privee.q_hex} />
                          <KV k="Keygen" v={formatMs(result.alice.keygen_ms)} />
                        </>
                      ) : (
                        <>
                          <HexBox label="k (scalaire privé)" value={result.alice.cle_privee_hex} />
                          <KV k="Taille k" v={`${result.alice.cle_privee_bits} bits`} />
                          <KV k="Keygen" v={formatMs(result.alice.keygen_ms)} />
                          <div style={{ padding: 10, background: 'var(--gray-50)', border: 'var(--border)', marginTop: 8 }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>
                              La clé publique Q = k×G est un point de la courbe. Il est impossible de retrouver k depuis Q (problème du logarithme discret sur courbe elliptique).
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Intermédiaires de signature */}
                  {result.algo === 'ECDSA' && (
                    <div style={{ marginTop: 16 }}>
                      <SectionTitle>Valeurs intermédiaires — signature</SectionTitle>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                        <div>
                          <KV k="Nonce r (secret éphémère)" v={result.nonce_r?.slice(0, 30) + '…'} copyable />
                          <HexBox label="Point R = r × G  (x)" value={result.point_R?.x_hex} />
                          <HexBox label="Point R = r × G  (y)" value={result.point_R?.y_hex} />
                        </div>
                        <div>
                          <HexBox label="Challenge h = H(R, Q, msg)" value={result.challenge_h_hex} />
                          <HexBox label="s = r + h × k_privée" value={result.s_hex} />
                        </div>
                      </div>
                    </div>
                  )}
                  {result.algo === 'RSA' && (
                    <div style={{ marginTop: 16 }}>
                      <SectionTitle>Valeurs intermédiaires — signature</SectionTitle>
                      <KV k="Hash réduit (hash mod n)" v={result.hash_reduit_hex?.slice(0, 30) + '…'} />
                      <HexBox label="Signature = hash^d mod n" value={result.signature_hex} />
                    </div>
                  )}
                </div>
              )}

              {/* ═══ Onglet : Bob ═══ */}
              {activeTab === 'bob' && (
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <div style={{ width: 48, height: 48, background: 'var(--gray-200)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-display)', fontSize: 26 }}>B</div>
                    <div>
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, letterSpacing: '0.05em' }}>BOB — Destinataire</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--gray-500)' }}>Reçoit message + signature · vérifie avec la clé publique d'Alice</div>
                    </div>
                  </div>

                  <SectionTitle>Ce que Bob reçoit</SectionTitle>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                    <div style={{ padding: 12, border: 'var(--border)', background: 'var(--gray-50)' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 6 }}>MESSAGE EN CLAIR</div>
                      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12 }}>{result.message}</div>
                    </div>
                    <div style={{ padding: 12, border: 'var(--border)', background: 'var(--gray-50)' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 6 }}>SIGNATURE</div>
                      {result.algo === 'RSA'
                        ? <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, wordBreak: 'break-all' }}>{result.signature_hex?.slice(0, 80)}…</div>
                        : <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, wordBreak: 'break-all' }}>R.x: {result.signature?.R_x_hex?.slice(0, 30)}…<br/>s: {result.signature?.s_hex?.slice(0, 30)}…</div>
                      }
                    </div>
                  </div>

                  <SectionTitle>Clé publique d'Alice (connue de Bob)</SectionTitle>
                  {result.algo === 'RSA' ? (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <KV k="e (exposant public)" v={String(result.bob.cle_publique_alice?.e || result.alice.cle_publique.e)} />
                      <KV k="n (bits)" v={String(result.alice.cle_publique.n_bits)} />
                      <HexBox label="n (module)" value={result.alice.cle_publique.n_hex} />
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <HexBox label="Q_alice.x" value={result.bob.cle_publique_alice?.Qx_hex} />
                      <HexBox label="Q_alice.y" value={result.bob.cle_publique_alice?.Qy_hex} />
                    </div>
                  )}

                  {result.algo === 'ECDSA' && (
                    <>
                      <SectionTitle style={{ marginTop: 16 }}>Clé de Bob (indépendante)</SectionTitle>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                        <HexBox label="Clé privée Bob (k_bob)" value={result.bob.cle_privee_hex} />
                        <HexBox label="Clé publique Bob (Q_bob.x)" value={result.bob.cle_publique?.Qx_hex} />
                      </div>
                    </>
                  )}

                  <div style={{ marginTop: 16, padding: 14, border: `2px solid ${result.is_valid ? 'var(--black)' : '#dc2626'}`, background: result.is_valid ? 'var(--black)' : '#fef2f2' }}>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, letterSpacing: '0.08em', color: result.is_valid ? 'white' : '#dc2626' }}>
                      {result.is_valid ? '✓ BOB ACCEPTE LA TRANSACTION' : '✗ BOB REJETTE — SIGNATURE INVALIDE'}
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: result.is_valid ? 'rgba(255,255,255,0.7)' : '#dc2626', marginTop: 6 }}>
                      {result.is_valid
                        ? 'La vérification prouve : (1) le message n\'a pas été altéré · (2) seule Alice a pu générer cette signature'
                        : 'La signature ne correspond pas au message ou à la clé publique d\'Alice'}
                    </div>
                  </div>
                </div>
              )}

              {/* ═══ Onglet : Paramètres ═══ */}
              {activeTab === 'params' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div className="card">
                    <SectionTitle>Paramètres de l'algorithme</SectionTitle>
                    {Object.entries(result.params || {}).map(([k, v]) => (
                      <KV key={k} k={k} v={String(v).length > 60 ? String(v).slice(0, 60) + '…' : String(v)} copyable />
                    ))}
                  </div>
                  <div className="card">
                    <SectionTitle>Propriétés de sécurité</SectionTitle>
                    <KV k="Problème difficile" v={result.proprietes?.probleme} isMono={false} />
                    <KV k="Sens facile" v={result.proprietes?.sens_facile} isMono={false} />
                    <KV k="Sens difficile" v={result.proprietes?.sens_difficile} isMono={false} />
                    <KV k="Bits de sécurité" v={`${result.security_bits} bits`} />
                    <KV k="Taille signature" v={`${result.signature_bytes} octets`} />
                    <KV k="Fonction de hash" v={result.params?.hash || 'SHA-512'} />

                    <div style={{ marginTop: 14, padding: 10, background: 'var(--gray-50)', border: 'var(--border)' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 6 }}>COMPARAISON RSA vs ECDSA</div>
                      {[
                        ['Keygen', 'RSA lent (cherche 2 premiers)', 'ECDSA quasi instantané'],
                        ['Signature', 'RSA : 1 modexp lente', 'ECDSA : mult. scalaire'],
                        ['Vérification', 'RSA : 1 modexp rapide (e petit)', 'ECDSA : 2 mult. scalaires'],
                        ['Taille clé pub.', 'RSA : 256-512 octets', 'ECDSA : 64 octets'],
                        ['Taille signature', `RSA : ${result.algo === 'RSA' ? result.signature_bytes : '256+'} octets`, 'ECDSA : 64 octets'],
                      ].map(([k, r, e]) => (
                        <div key={k} style={{ display: 'grid', gridTemplateColumns: '80px 1fr 1fr', gap: 6, padding: '4px 0', borderBottom: '1px solid var(--gray-100)', fontFamily: 'var(--font-mono)', fontSize: 9 }}>
                          <span style={{ color: 'var(--gray-500)' }}>{k}</span>
                          <span style={{ color: 'var(--gray-700)' }}>{r}</span>
                          <span style={{ color: 'var(--gray-700)' }}>{e}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ═══ Onglet : Signature ═══ */}
              {activeTab === 'signature' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div className="card">
                    <SectionTitle>Données brutes de la signature</SectionTitle>
                    {result.algo === 'RSA' ? (
                      <>
                        <KV k="Algorithme" v="RSA + SHA-512" />
                        <KV k="Taille (bits)" v={String(result.signature_bits)} />
                        <KV k="Taille (octets)" v={String(result.signature_bytes)} />
                        <HexBox label="Signature hexadécimale (= hash^d mod n)" value={result.signature_hex} rows={6} />
                        <HexBox label="Hash SHA-512 original" value={result.hash_sha512} />
                        <HexBox label="Hash réduit mod n (signé)" value={result.hash_reduit_hex} />
                      </>
                    ) : (
                      <>
                        <KV k="Algorithme" v={`ECDSA/${result.courbe} + SHA-512`} />
                        <KV k="Format" v="(R, s) — point + scalaire" />
                        <KV k="Taille totale" v={`${result.signature_bytes} octets`} />
                        <HexBox label="R.x — Point éphémère (256 bits)" value={result.signature?.R_x_hex} />
                        <HexBox label="R.y — Point éphémère (256 bits)" value={result.signature?.R_y_hex} />
                        <HexBox label="s — Scalaire de preuve" value={result.signature?.s_hex} />
                        <HexBox label="Hash SHA-512 du message" value={result.hash_sha512} />
                        <HexBox label="Challenge h = H(R, Q, msg) mod p" value={result.challenge_h_hex} />
                      </>
                    )}
                  </div>

                  <div className="card">
                    <SectionTitle>Pourquoi cette signature prouve l'authenticité</SectionTitle>
                    {result.algo === 'RSA' ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {[
                          ['Seul Alice peut signer', 'Seule Alice connaît d. Sans d, pow(hash, d, n) est impossible car factoriser n pour retrouver φ(n) est infaisable.'],
                          ['N\'importe qui peut vérifier', 'La clé publique (e, n) permet à Bob de calculer sig^e mod n et de comparer au hash du message reçu.'],
                          ['Intégrité garantie', 'Toute modification du message change son SHA-512, donc le hash vérifié ne correspondra plus à la signature.'],
                          ['Non-répudiation', 'Alice ne peut pas nier avoir signé : seule sa clé privée peut produire cette signature pour ce message.'],
                        ].map(([t, d]) => (
                          <div key={t} style={{ padding: 12, border: 'var(--border)', background: 'var(--gray-50)' }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600, marginBottom: 4 }}>{t}</div>
                            <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--gray-600)', lineHeight: 1.6 }}>{d}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {[
                          ['La vérification s×G = R + h×Q', 'Si s = r + h×k, alors s×G = r×G + h×k×G = R + h×Q. Seule la personne connaissant k peut produire un (R, s) satisfaisant cette équation.'],
                          ['Le nonce r doit rester secret', 'Si r est réutilisé pour deux messages différents, un attaquant peut extraire la clé privée k. C\'est pourquoi r est généré aléatoirement à chaque signature.'],
                          ['Le challenge h lie le message à la signature', 'h dépend de R, Q_alice et du message. Modifier le message change h, rendant la vérification impossible sans la bonne clé privée.'],
                          ['Avantage courbe elliptique', `Sur ${result.courbe}, les points peuvent avoir des coordonnées astronomiques (${(result.params?.prime_bits || 255)} bits) rendant le logarithme discret infaisable.`],
                        ].map(([t, d]) => (
                          <div key={t} style={{ padding: 12, border: 'var(--border)', background: 'var(--gray-50)' }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600, marginBottom: 4 }}>{t}</div>
                            <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--gray-600)', lineHeight: 1.6 }}>{d}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}