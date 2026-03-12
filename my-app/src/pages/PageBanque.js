import React, { useState, useEffect, useRef } from 'react';
import { api, formatEur, formatIban, formatMs, TX_TYPE_LABELS, TX_TYPE_ICONS } from '../utils/api';
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, AreaChart, Area
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      {payload.map(p => (
        <div key={p.name}>{p.name} : {p.value?.toFixed(2)}{p.unit || ''}</div>
      ))}
    </div>
  );
};

/* Gauge circulaire SVG */
function Gauge({ value, max = 100, label, unit = '%', warn = 70, crit = 90 }) {
  const pct = Math.min(value / max, 1);
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = pct * circ * 0.75; // arc = 270°
  const color = value >= crit ? '#dc2626' : value >= warn ? '#d97706' : '#000000';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <svg width={96} height={96} viewBox="0 0 96 96">
        {/* Piste fond */}
        <circle
          cx={48} cy={48} r={r}
          fill="none"
          stroke="var(--gray-100)"
          strokeWidth={8}
          strokeDasharray={`${circ * 0.75} ${circ * 0.25}`}
          strokeDashoffset={circ * 0.125}
          strokeLinecap="butt"
          transform="rotate(135 48 48)"
        />
        {/* Arc valeur */}
        <circle
          cx={48} cy={48} r={r}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeDashoffset={circ * 0.125}
          strokeLinecap="butt"
          transform="rotate(135 48 48)"
          style={{ transition: 'stroke-dasharray 0.5s ease, stroke 0.3s' }}
        />
        {/* Valeur centrale */}
        <text x={48} y={50} textAnchor="middle" dominantBaseline="middle"
          style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700, fill: color }}>
          {unit === '%' ? `${value.toFixed(0)}%` : `${value.toFixed(0)}`}
        </text>
      </svg>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--gray-500)' }}>
        {label}
      </div>
    </div>
  );
}

/* Barre horizontale */
function BarGauge({ label, value, max, unit, warn = 70, crit = 90 }) {
  const pct = Math.min((value / max) * 100, 100);
  const color = pct >= crit ? '#dc2626' : pct >= warn ? '#d97706' : 'var(--black)';
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600, color }}>
          {value.toFixed(1)}{unit}
        </span>
      </div>
      <div style={{ height: 4, background: 'var(--gray-100)' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, transition: 'width 0.5s ease, background 0.3s' }} />
      </div>
    </div>
  );
}

export default function PageBanque({ bankStatus, simRunning, setSimRunning, liveTransactions, liveMetrics, refreshStatus }) {
  const [accounts, setAccounts] = useState([]);
  const [tps, setTps] = useState(0.5);
  const [stats, setStats] = useState(null);
  const [selectedTx, setSelectedTx] = useState(null);
  const [sysMetrics, setSysMetrics] = useState(null);
  const [sysHistory, setSysHistory] = useState([]); // { i, cpu_global, cpu_proc, ram_global, ram_proc }
  const tickRef = useRef(0);

  // Listen to WebSocket system_metrics events via prop drilling isn't available,
  // so we poll /api/system/metrics every 2s as fallback + rely on WS via App.js
  useEffect(() => {
    const fetchSys = () => {
      api.status && fetch('http://localhost:8000/api/system/metrics')
        .then(r => r.json())
        .then(data => {
          setSysMetrics(data);
          setSysHistory(prev => {
            const next = [...prev, {
              i: tickRef.current++,
              cpu_global: data.cpu_global_pct,
              cpu_proc: data.cpu_proc_pct,
              ram_global: data.ram_global_pct,
              ram_proc: data.ram_proc_mb,
            }].slice(-60);
            return next;
          });
        })
        .catch(() => {});
    };
    fetchSys();
    const t = setInterval(fetchSys, 2000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (bankStatus?.initialise) {
      api.getAccounts().then(setAccounts).catch(() => {});
      api.getStats().then(setStats).catch(() => {});
    }
  }, [bankStatus, liveTransactions.length]);

  const handleStartSim = async () => {
    try { await api.startSim(tps, null); setSimRunning(true); }
    catch (e) { alert(e.message); }
  };

  const handleStopSim = async () => {
    try { await api.stopSim(); setSimRunning(false); }
    catch (e) {}
  };

  const handleManualTx = async () => {
    try { await api.randomTransaction(); }
    catch (e) { alert(e.message); }
  };

  const cryptoChartData = liveMetrics.slice(-40).map((m, i) => ({
    i,
    sign: +m.sign_ms?.toFixed(2) || 0,
    verify: +m.verify_ms?.toFixed(2) || 0,
  }));

  const isInit = bankStatus?.initialise;

  return (
    <div>
      <div className="page-header">
        <div className="page-title">BANQUE VIRTUELLE</div>
        <div className="page-subtitle">
          Visualisation en temps réel — transactions, métriques cryptographiques et ressources système
        </div>
      </div>

      {!isInit && (
        <div style={{ padding: '16px', background: 'var(--gray-50)', border: 'var(--border)', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-600)' }}>
          ◎ Veuillez initialiser la banque dans la page Configuration.
        </div>
      )}

      {isInit && (
        <>
          {/* KPIs */}
          <div className="grid-4" style={{ marginBottom: 20 }}>
            {[
              { label: 'Transactions', value: stats?.total_transactions ?? liveTransactions.length, unit: 'total' },
              { label: 'Approuvées', value: stats?.approuvees ?? '—' },
              { label: 'Signature moy.', value: stats?.sign_time_avg_ms ? formatMs(stats.sign_time_avg_ms) : '—' },
              { label: 'Vérif. moy.', value: stats?.verify_time_avg_ms ? formatMs(stats.verify_time_avg_ms) : '—' },
            ].map(s => (
              <div key={s.label} className="stat-block">
                <div className="stat-label">{s.label}</div>
                <div className="stat-value" style={{ fontSize: 22 }}>{s.value}</div>
                {s.unit && <div className="stat-unit">{s.unit}</div>}
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
            {/* LEFT */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* SIMULATION CONTROLS */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Contrôle de Simulation</span>
                  <div className="live-indicator">
                    <span className={`live-dot ${simRunning ? 'pulsing' : ''}`} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: simRunning ? 'var(--black)' : 'var(--gray-400)' }}>
                      {simRunning ? 'SIMULATION EN COURS' : 'ARRÊTÉE'}
                    </span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', letterSpacing: '0.15em', marginBottom: 6 }}>TRANSACTIONS / SECONDE</div>
                    <input type="range" min={0.1} max={2} step={0.1} value={tps}
                      onChange={e => setTps(+e.target.value)} disabled={simRunning} />
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, marginTop: 4 }}>{tps.toFixed(1)} TPS</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {!simRunning
                      ? <button className="btn btn-primary btn-sm" onClick={handleStartSim}>▶ Démarrer</button>
                      : <button className="btn btn-sm" onClick={handleStopSim}>◼ Arrêter</button>
                    }
                    <button className="btn btn-ghost btn-sm" onClick={handleManualTx}>+ Manuel</button>
                  </div>
                </div>
              </div>

              {/* SYSTEM RESOURCES */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Ressources Système</span>
                  <div className="live-indicator">
                    <span className="live-dot pulsing" />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>TEMPS RÉEL · 2s</span>
                  </div>
                </div>

                {sysMetrics ? (
                  <>
                    {/* Gauges circulaires */}
                    <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 20, paddingBottom: 16, borderBottom: 'var(--border)' }}>
                      <Gauge value={sysMetrics.cpu_global_pct} label="CPU Système" warn={60} crit={85} />
                    
                      <Gauge value={sysMetrics.ram_global_pct} label="RAM Système" warn={70} crit={90} />
                      
                    </div>

                    {/* Barres détaillées */}
                    <div style={{ marginBottom: 16 }}>
                      <BarGauge
                        label={`CPU global (${sysMetrics.cpu_cores} cœurs)`}
                        value={sysMetrics.cpu_global_pct} max={100} unit="%" warn={60} crit={85}
                      />
                     
                      <BarGauge
                        label={`RAM système (${sysMetrics.ram_global_total_mb.toFixed(0)} MB total)`}
                        value={sysMetrics.ram_global_used_mb} max={sysMetrics.ram_global_total_mb} unit=" MB" warn={70} crit={90}
                      />
                     
                    </div>

                    {/* Graphiques historiques */}
                    {sysHistory.length > 2 && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                        {/* CPU chart */}
                        <div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 8 }}>
                            Historique CPU (%)
                          </div>
                          <div style={{ height: 110 }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart data={sysHistory} margin={{ top: 2, right: 4, bottom: 2, left: 4 }}>
                                <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" />
                                <XAxis dataKey="i" tick={false} />
                                <YAxis domain={[0, 100]} tick={{ fontFamily: 'var(--font-mono)', fontSize: 8 }} tickFormatter={v => `${v}%`} width={28} />
                                <Tooltip content={({ active, payload }) => {
                                  if (!active || !payload?.length) return null;
                                  return (
                                    <div className="custom-tooltip">
                                      <div>Système : {payload[0]?.value?.toFixed(1)}%</div>
                                      <div>Process : {payload[1]?.value?.toFixed(1)}%</div>
                                    </div>
                                  );
                                }} />
                                <Area type="monotone" dataKey="cpu_global" name="CPU sys" stroke="var(--gray-400)" fill="var(--gray-100)" strokeWidth={1} dot={false} />
                                <Area type="monotone" dataKey="cpu_proc" name="CPU proc" stroke="var(--black)" fill="var(--black)" fillOpacity={0.1} strokeWidth={1.5} dot={false} />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                          <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
                            {[
                              { color: 'var(--black)', label: 'Process' },
                              { color: 'var(--gray-400)', label: 'Système' },
                            ].map(item => (
                              <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>
                                <div style={{ width: 12, height: 1.5, background: item.color }} />
                                {item.label}
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* RAM chart */}
                        <div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 8 }}>
                            Historique RAM (%)
                          </div>
                          <div style={{ height: 110 }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart data={sysHistory} margin={{ top: 2, right: 4, bottom: 2, left: 4 }}>
                                <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" />
                                <XAxis dataKey="i" tick={false} />
                                <YAxis domain={[0, 100]} tick={{ fontFamily: 'var(--font-mono)', fontSize: 8 }} tickFormatter={v => `${v}%`} width={28} />
                                <Tooltip content={({ active, payload }) => {
                                  if (!active || !payload?.length) return null;
                                  return (
                                    <div className="custom-tooltip">
                                      <div>RAM sys : {payload[0]?.value?.toFixed(1)}%</div>
                                      <div>Process : {payload[1]?.value?.toFixed(1)} MB</div>
                                    </div>
                                  );
                                }} />
                                <Area type="monotone" dataKey="ram_global" name="RAM sys" stroke="var(--gray-400)" fill="var(--gray-100)" strokeWidth={1} dot={false} />
                                <Area type="monotone" dataKey="ram_proc" name="RAM proc MB" stroke="var(--black)" fill="var(--black)" fillOpacity={0.1} strokeWidth={1.5} dot={false} />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                          <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
                            {[
                              { color: 'var(--black)', label: 'Process (MB)' },
                              { color: 'var(--gray-400)', label: 'Système (%)' },
                            ].map(item => (
                              <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>
                                <div style={{ width: 12, height: 1.5, background: item.color }} />
                                {item.label}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 0', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-500)' }}>
                    <span className="spinner" />
                    Connexion au serveur de métriques...
                  </div>
                )}
              </div>

              {/* CRYPTO CHART */}
              {cryptoChartData.length > 1 && (
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">Temps de Traitement Cryptographique</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>{bankStatus.algo}</span>
                  </div>
                  <div style={{ height: 160 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={cryptoChartData} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                        <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" />
                        <XAxis dataKey="i" tick={false} />
                        <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} tickFormatter={v => `${v}ms`} />
                        <Tooltip content={<CustomTooltip />} />
                        <Line type="monotone" dataKey="sign" name="Signature (ms)" stroke="var(--black)" dot={false} strokeWidth={1.5} />
                        <Line type="monotone" dataKey="verify" name="Vérification (ms)" stroke="var(--gray-400)" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* TRANSACTION FEED */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Flux de Transactions</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>
                    {liveTransactions.length} entrées
                  </span>
                </div>
                <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                  <table className="tx-table">
                    <thead>
                      <tr>
                        <th>Réf.</th>
                        <th>Type</th>
                        <th>Marchand</th>
                        <th>Montant</th>
                        <th>Signature</th>
                        <th>Statut</th>
                      </tr>
                    </thead>
                    <tbody>
                      {liveTransactions.slice(0, 50).map((tx, i) => (
                        <tr key={tx.id || i} className={i === 0 ? 'tx-new' : ''} style={{ cursor: 'pointer' }}
                          onClick={() => setSelectedTx(selectedTx?.id === tx.id ? null : tx)}>
                          <td style={{ color: 'var(--gray-500)' }}>{tx.reference}</td>
                          <td>{TX_TYPE_ICONS[tx.type_transaction]} {TX_TYPE_LABELS[tx.type_transaction]?.slice(0, 10)}</td>
                          <td style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tx.marchand}</td>
                          <td style={{ fontWeight: 600 }}>{formatEur(tx.montant)}</td>
                          <td style={{ color: 'var(--gray-500)' }}>{tx.metrics ? formatMs(tx.metrics.sign_time_ms) : '—'}</td>
                          <td><span className={`tx-status ${tx.status?.toLowerCase()}`}>{tx.status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {liveTransactions.length === 0 && (
                    <div style={{ padding: '24px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-400)' }}>
                      Aucune transaction — Démarrez la simulation ou créez une transaction manuellement.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* RIGHT PANEL */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* ACCOUNTS */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Comptes Clients</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>{accounts.length} comptes</span>
                </div>
                <div>
                  {accounts.map((acc, i) => (
                    <div key={acc.id} style={{ padding: '12px 0', borderBottom: i < accounts.length - 1 ? 'var(--border)' : 'none' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, fontWeight: 500 }}>{acc.titulaire}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600 }}>{formatEur(acc.solde)}</span>
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>{formatIban(acc.iban)}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)', marginTop: 2 }}>
                        PK: ...{acc.cle_publique_hex?.slice(-16)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* SYSTEM SNAPSHOT */}
              {sysMetrics && (
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">Snapshot Système</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                    {[
                      ['CPU global', `${sysMetrics.cpu_global_pct.toFixed(1)} %`],

                      ['RAM utilisée', `${sysMetrics.ram_global_used_mb.toFixed(0)} / ${sysMetrics.ram_global_total_mb.toFixed(0)} MB`],

                      ['Cœurs CPU', sysMetrics.cpu_cores],
                    ].map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: 'var(--border)' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>{k}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600 }}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SELECTED TX DETAIL */}
              {selectedTx && (
                <div className="card" style={{ borderTop: '2px solid var(--black)' }}>
                  <div className="card-header">
                    <span className="card-title">Détail — {selectedTx.reference}</span>
                    <button className="btn btn-ghost btn-sm" onClick={() => setSelectedTx(null)}>×</button>
                  </div>
                  <div>
                    {[
                      ['Émetteur', selectedTx.titulaire_source],
                      ['Destinataire', selectedTx.titulaire_destination || '—'],
                      ['IBAN source', formatIban(selectedTx.compte_source)],
                      ['Terminal', selectedTx.terminal_id],
                      ['IP Terminal', selectedTx.ip_terminal],
                      ...(selectedTx.metrics ? [
                        ['Algo', selectedTx.metrics.algo],
                        ['Taille clé', `${selectedTx.metrics.key_size_bits} bits`],
                        ['Taille sig.', `${selectedTx.metrics.signature_size_bytes} octets`],
                        ['Sécurité', `${selectedTx.metrics.security_bits} bits`],
                        ['Signature', formatMs(selectedTx.metrics.sign_time_ms)],
                        ['Vérification', formatMs(selectedTx.metrics.verify_time_ms)],
                      ] : []),
                    ].map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: 'var(--border)' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-500)' }}>{k}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500 }}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}