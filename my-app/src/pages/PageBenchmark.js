import React, { useState } from 'react';
import { api, formatMs } from '../utils/api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div style={{ marginBottom: 4, color: 'var(--gray-400)' }}>{label}</div>
      {payload.map(p => (
        <div key={p.name}>{p.name} : {typeof p.value === 'number' ? (p.value < 1 ? p.value.toFixed(3) : p.value.toFixed(2)) : p.value} ms</div>
      ))}
    </div>
  );
};

function ResultCard({ result, label }) {
  if (!result) return null;
  return (
    <div className="card" style={{ borderTop: `2px solid var(--black)` }}>
      <div className="card-header">
        <span className="card-title">{label}</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', padding: '2px 7px',
          background: result.algo === 'RSA' ? 'var(--black)' : 'var(--white)',
          color: result.algo === 'RSA' ? 'var(--white)' : 'var(--black)',
          border: '1px solid var(--black)',
        }}>
          {result.algo}{result.rsa_bits ? ` ${result.rsa_bits}` : ''}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 16 }}>
        {[
          { label: 'Génération clés', avg: result.keygen_time_avg_ms, min: result.keygen_time_min_ms, max: result.keygen_time_max_ms },
          { label: 'Signature', avg: result.sign_time_avg_ms, min: result.sign_time_min_ms, max: result.sign_time_max_ms },
          { label: 'Vérification', avg: result.verify_time_avg_ms, min: result.verify_time_min_ms, max: result.verify_time_max_ms },
        ].map(m => (
          <div key={m.label} className="stat-block">
            <div className="stat-label">{m.label}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700 }}>{formatMs(m.avg)}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)', marginTop: 4 }}>
              min {formatMs(m.min)} · max {formatMs(m.max)}
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
        {[
          ['Clé (bits)', result.key_size_bits],
          ['Sig. (octets)', result.signature_size_bytes],
          ['Sécurité', `${result.security_bits} bits`],
          ['Débit estimé', `${result.throughput_tps} TPS`],
        ].map(([k, v]) => (
          <div key={k} style={{ padding: '8px', background: 'var(--gray-50)', border: 'var(--border)' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', marginBottom: 4 }}>{k}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600 }}>{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PageBenchmark() {
  const [mode, setMode] = useState('single'); // 'single' | 'compare'
  const [algo, setAlgo] = useState('ECDSA');
  const [rsaBits, setRsaBits] = useState(2048);
  const [iterations, setIterations] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [compRsaBits, setCompRsaBits] = useState(2048);
  const [compIterations, setCompIterations] = useState(3);

  const runSingle = async () => {
    setLoading(true); setResult(null);
    try {
      const res = await api.benchmark({
        algo,
        rsa_bits: algo === 'RSA' ? rsaBits : null,
        nb_iterations: iterations,
        message_test: 'Transaction bancaire BankLab test benchmark',
      });
      setResult(res);
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  const runComparison = async () => {
    setLoading(true); setComparison(null);
    try {
      const res = await api.comparison(compIterations, compRsaBits);
      setComparison(res);
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  // Bar chart data for comparison
  const buildCompareChart = (comp) => {
    if (!comp?.rsa || !comp?.ecdsa) return [];
    return [
      { op: 'Keygen', RSA: comp.rsa.keygen_time_avg_ms, ECDSA: comp.ecdsa.keygen_time_avg_ms },
      { op: 'Signature', RSA: comp.rsa.sign_time_avg_ms, ECDSA: comp.ecdsa.sign_time_avg_ms },
      { op: 'Vérification', RSA: comp.rsa.verify_time_avg_ms, ECDSA: comp.ecdsa.verify_time_avg_ms },
    ];
  };

  const radarData = comparison ? [
    { metric: 'Vitesse Keygen', RSA: 100 - Math.min(100, comparison.rsa.keygen_time_avg_ms / 20), ECDSA: 100 - Math.min(100, comparison.ecdsa.keygen_time_avg_ms / 20) },
    { metric: 'Vitesse Sign.', RSA: 100 - Math.min(100, comparison.rsa.sign_time_avg_ms / 5), ECDSA: 100 - Math.min(100, comparison.ecdsa.sign_time_avg_ms / 5) },
    { metric: 'Vitesse Vérif.', RSA: 100 - Math.min(100, comparison.rsa.verify_time_avg_ms / 5), ECDSA: 100 - Math.min(100, comparison.ecdsa.verify_time_avg_ms / 5) },
    { metric: 'Compacité clé', RSA: Math.max(0, 100 - comparison.rsa.key_size_bits / 50), ECDSA: Math.max(0, 100 - comparison.ecdsa.key_size_bits / 50) },
    { metric: 'Compacité sig.', RSA: Math.max(0, 100 - comparison.rsa.signature_size_bytes / 5), ECDSA: Math.max(0, 100 - comparison.ecdsa.signature_size_bytes / 5) },
  ] : [];

  return (
    <div>
      <div className="page-header">
        <div className="page-title">BENCHMARK</div>
        <div className="page-subtitle">
          Mesure précise des performances cryptographiques — génération de clés, signature, vérification
        </div>
      </div>

      {/* MODE TABS */}
      <div className="tabs">
        <button className={`tab ${mode === 'single' ? 'active' : ''}`} onClick={() => setMode('single')}>
          Benchmark Individuel
        </button>
        <button className={`tab ${mode === 'compare' ? 'active' : ''}`} onClick={() => setMode('compare')}>
          Comparaison RSA vs ECDSA
        </button>
      </div>

      {mode === 'single' && (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card">
              <div className="card-header"><span className="card-title">Paramètres</span></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Algorithme</label>
                  <div className="seg-control" style={{ width: '100%' }}>
                    <button className={`seg-btn ${algo === 'ECDSA' ? 'active' : ''}`} style={{ flex: 1 }} onClick={() => setAlgo('ECDSA')}>ECDSA</button>
                    <button className={`seg-btn ${algo === 'RSA' ? 'active' : ''}`} style={{ flex: 1 }} onClick={() => setAlgo('RSA')}>RSA</button>
                  </div>
                </div>
                {algo === 'RSA' && (
                  <div className="form-group">
                    <label className="form-label">Taille clé RSA (bits)</label>
                    <select className="form-control" value={rsaBits} onChange={e => setRsaBits(+e.target.value)}>
                      {[1024, 2048, 3072, 4096].map(b => <option key={b} value={b}>{b} bits</option>)}
                    </select>
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">Nombre d'itérations : {iterations}</label>
                  <input type="range" min={1} max={10} value={iterations} onChange={e => setIterations(+e.target.value)} />
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)', marginTop: 4 }}>
                    {iterations} {iterations === 1 ? 'itération' : 'itérations'}
                    {algo === 'RSA' && rsaBits >= 3072 ? ' · Durée estimée : longue' : ' · Durée estimée : courte'}
                  </div>
                </div>
                <button className="btn btn-primary" onClick={runSingle} disabled={loading}>
                  {loading ? <><span className="spinner" style={{ borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} /> Calcul...</> : '▶ Lancer le Benchmark'}
                </button>
              </div>
            </div>

            {/* Info */}
            <div className="card">
              <div className="card-header"><span className="card-title">À propos du Benchmark</span></div>
              <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--gray-600)', lineHeight: 1.7 }}>
                Chaque itération mesure indépendamment la génération de clés, la signature et la vérification avec <code style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>time.perf_counter()</code> Python.
                Les statistiques min/max/moy sont calculées sur l'ensemble des itérations.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {loading && (
              <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 24 }}>
                <span className="spinner" />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-600)' }}>
                  Benchmark en cours — {iterations} itération(s)...
                  {algo === 'RSA' && rsaBits >= 3072 && ' (La génération RSA-3072 peut prendre quelques minutes)'}
                </span>
              </div>
            )}
            {result && <ResultCard result={result} label="Résultats" />}
            {result && (
              <div className="card">
                <div className="card-header"><span className="card-title">Visualisation</span></div>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart margin={{ top: 4, right: 8, bottom: 4, left: 8 }}
                      data={[
                        { op: 'Keygen', moy: result.keygen_time_avg_ms, min: result.keygen_time_min_ms, max: result.keygen_time_max_ms },
                        { op: 'Signature', moy: result.sign_time_avg_ms, min: result.sign_time_min_ms, max: result.sign_time_max_ms },
                        { op: 'Vérif.', moy: result.verify_time_avg_ms, min: result.verify_time_min_ms, max: result.verify_time_max_ms },
                      ]}>
                      <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" vertical={false} />
                      <XAxis dataKey="op" tick={{ fontFamily: 'var(--font-mono)', fontSize: 10 }} />
                      <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} tickFormatter={v => `${v.toFixed(0)}ms`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="moy" name="Moyenne (ms)" fill="var(--black)" />
                      <Bar dataKey="min" name="Min (ms)" fill="var(--gray-400)" />
                      <Bar dataKey="max" name="Max (ms)" fill="var(--gray-200)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {mode === 'compare' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Config row */}
          <div className="card">
            <div className="card-header"><span className="card-title">Paramètres de Comparaison</span></div>
            <div style={{ display: 'flex', gap: 20, alignItems: 'flex-end' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Taille clé RSA (bits)</label>
                <select className="form-control" value={compRsaBits} onChange={e => setCompRsaBits(+e.target.value)}>
                  {[1024, 2048, 3072, 4096].map(b => <option key={b} value={b}>{b} bits</option>)}
                </select>
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Itérations : {compIterations}</label>
                <input type="range" min={1} max={5} value={compIterations} onChange={e => setCompIterations(+e.target.value)} />
              </div>
              <button className="btn btn-primary" onClick={runComparison} disabled={loading} style={{ minWidth: 160, marginBottom: 2 }}>
                {loading ? <><span className="spinner" style={{ borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} /> Calcul...</> : '▶ Comparer'}
              </button>
            </div>
          </div>

          {loading && (
            <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 24 }}>
              <span className="spinner" />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-600)' }}>
                Benchmark RSA-{compRsaBits} et ECDSA en cours...
              </span>
            </div>
          )}

          {comparison && (
            <>
              {/* Ratio cards */}
              <div className="grid-4">
                {[
                  { label: 'Ratio Keygen', value: comparison.ratio_keygen, unit: '× plus lent (RSA)' },
                  { label: 'Ratio Signature', value: comparison.ratio_sign, unit: '× plus lent (RSA)' },
                  { label: 'Ratio Vérif.', value: comparison.ratio_verify, unit: '× plus lent (RSA)' },
                  { label: 'Ratio Taille Clé', value: comparison.ratio_key_size, unit: '× plus grande (RSA)' },
                ].map(r => (
                  <div key={r.label} className="stat-block">
                    <div className="stat-label">{r.label}</div>
                    <div className="stat-value" style={{ fontSize: 26 }}>{r.value?.toFixed(1) ?? '—'}×</div>
                    <div className="stat-unit">{r.unit}</div>
                  </div>
                ))}
              </div>

              {/* Side-by-side results */}
              <div className="grid-2">
                <ResultCard result={comparison.rsa} label={`RSA — ${compRsaBits} bits`} />
                <ResultCard result={comparison.ecdsa} label="ECDSA — Ed25519 (256 bits)" />
              </div>

              {/* Bar chart comparison */}
              <div className="card">
                <div className="card-header"><span className="card-title">Comparaison Visuelle des Temps</span></div>
                <div style={{ height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={buildCompareChart(comparison)} margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" vertical={false} />
                      <XAxis dataKey="op" tick={{ fontFamily: 'var(--font-mono)', fontSize: 10 }} />
                      <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} tickFormatter={v => `${v.toFixed(0)}ms`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="RSA" name="RSA" fill="var(--black)" />
                      <Bar dataKey="ECDSA" name="ECDSA" fill="var(--gray-300)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                  {[['var(--black)', 'RSA'], ['var(--gray-300)', 'ECDSA']].map(([c, l]) => (
                    <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>
                      <div style={{ width: 12, height: 12, background: c }} />
                      {l}
                    </div>
                  ))}
                </div>
              </div>

              {/* Radar */}
              {radarData.length > 0 && (
                <div className="card">
                  <div className="card-header"><span className="card-title">Profil Multi-Critères (score normalisé)</span></div>
                  <div style={{ height: 280 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData}>
                        <PolarGrid stroke="var(--gray-200)" />
                        <PolarAngleAxis dataKey="metric" tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} />
                        <Radar name="RSA" dataKey="RSA" stroke="var(--black)" fill="var(--black)" fillOpacity={0.1} strokeWidth={1.5} />
                        <Radar name="ECDSA" dataKey="ECDSA" stroke="var(--gray-500)" fill="var(--gray-500)" fillOpacity={0.1} strokeWidth={1.5} strokeDasharray="4 2" />
                        <Legend iconSize={10} wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 10 }} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
