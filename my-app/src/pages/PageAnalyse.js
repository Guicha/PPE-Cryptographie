import React, { useMemo, useState } from 'react';
import { formatMs, formatEur } from '../utils/api';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, Legend
} from 'recharts';

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      {payload.map(p => (
        <div key={p.name}>{p.name} : {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</div>
      ))}
    </div>
  );
};

const GRAYS = ['var(--black)', 'var(--gray-400)', 'var(--gray-600)', 'var(--gray-300)', 'var(--gray-700)'];
const TX_COLORS = {
  PAIEMENT_CB: 'var(--black)', RETRAIT_DAB: 'var(--gray-600)',
  VIREMENT: 'var(--gray-400)', PAIEMENT_MOBILE: 'var(--gray-700)',
  AUTORISATION: 'var(--gray-300)', REMBOURSEMENT: 'var(--gray-500)',
};

const TX_FR = {
  PAIEMENT_CB: 'Paiement CB', RETRAIT_DAB: 'Retrait DAB',
  VIREMENT: 'Virement', PAIEMENT_MOBILE: 'Paiement Mobile',
  AUTORISATION: 'Autorisation', REMBOURSEMENT: 'Remboursement',
};

function InfoBox({ title, children }) {
  return (
    <div style={{ padding: 14, background: 'var(--gray-50)', border: 'var(--border)' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--gray-500)', marginBottom: 8 }}>{title}</div>
      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--gray-700)', lineHeight: 1.6 }}>{children}</div>
    </div>
  );
}

export default function PageAnalyse({ liveTransactions, liveMetrics, bankStatus }) {
  const [tab, setTab] = useState('temps');

  // Prepare data
  const metrics = liveMetrics.slice(-200);
  const txs = liveTransactions.slice(0, 200);

  // Time series
  const timeSeries = metrics.map((m, i) => ({
    i,
    sign: +m.sign_ms?.toFixed(3) || 0,
    verify: +m.verify_ms?.toFixed(3) || 0,
    total: +(m.sign_ms + m.verify_ms)?.toFixed(3) || 0,
  }));

  // Scatter: sign time vs montant
  const scatterData = txs
    .filter(t => t.metrics && t.montant)
    .map(t => ({ x: +t.montant.toFixed(2), y: +t.metrics.sign_time_ms?.toFixed(2), type: t.type_transaction }));

  // Distribution histogram of sign times
  const histData = useMemo(() => {
    if (!metrics.length) return [];
    const vals = metrics.map(m => m.sign_ms || 0);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const bins = 10;
    const step = (max - min) / bins || 1;
    const buckets = Array.from({ length: bins }, (_, i) => ({
      range: `${(min + i * step).toFixed(0)}-${(min + (i + 1) * step).toFixed(0)}ms`,
      count: 0,
    }));
    vals.forEach(v => {
      const idx = Math.min(Math.floor((v - min) / step), bins - 1);
      if (idx >= 0) buckets[idx].count++;
    });
    return buckets;
  }, [metrics]);

  // TX type breakdown
  const txTypeData = useMemo(() => {
    const counts = {};
    txs.forEach(t => {
      counts[t.type_transaction] = (counts[t.type_transaction] || 0) + 1;
    });
    return Object.entries(counts).map(([k, v]) => ({ name: TX_FR[k] || k, value: v, key: k }));
  }, [txs]);

  // Status breakdown
  const statusData = useMemo(() => {
    const counts = { APPROUVE: 0, REFUSE: 0, ERREUR: 0 };
    txs.forEach(t => { if (counts[t.status] !== undefined) counts[t.status]++; });
    return [
      { name: 'Approuvé', value: counts.APPROUVE, fill: '#000' },
      { name: 'Refusé', value: counts.REFUSE, fill: '#9a9a9a' },
      { name: 'Erreur', value: counts.ERREUR, fill: '#dedede' },
    ].filter(d => d.value > 0);
  }, [txs]);

  // Stats
  const signTimes = metrics.map(m => m.sign_ms || 0);
  const verifyTimes = metrics.map(m => m.verify_ms || 0);
  const avg = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
  const std = arr => {
    const m = avg(arr);
    return Math.sqrt(arr.reduce((a, b) => a + (b - m) ** 2, 0) / (arr.length || 1));
  };

  const hasData = metrics.length > 0 || txs.length > 0;

  return (
    <div>
      <div className="page-header">
        <div className="page-title">ANALYSE</div>
        <div className="page-subtitle">
          Visualisation approfondie de la consommation computationnelle cryptographique
        </div>
      </div>

      {!hasData && (
        <div style={{ padding: '24px', background: 'var(--gray-50)', border: 'var(--border)', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-600)', textAlign: 'center' }}>
          Aucune donnée disponible. Créez des transactions via la page Banque ou Transaction.
        </div>
      )}

      {hasData && (
        <>
          {/* KPIs */}
          <div className="grid-4" style={{ marginBottom: 20 }}>
            {[
              { label: 'Échantillons', value: metrics.length },
              { label: 'Sign. moy.', value: formatMs(avg(signTimes)) },
              { label: 'Vérif. moy.', value: formatMs(avg(verifyTimes)) },
              { label: 'Débit estimé', value: `${avg(signTimes) + avg(verifyTimes) > 0 ? (1000 / (avg(signTimes) + avg(verifyTimes))).toFixed(2) : '—'} TPS` },
            ].map(s => (
              <div key={s.label} className="stat-block">
                <div className="stat-label">{s.label}</div>
                <div className="stat-value" style={{ fontSize: 22 }}>{s.value}</div>
              </div>
            ))}
          </div>

          <div className="tabs">
            {[
              ['temps', 'Séries Temporelles'],
              ['distribution', 'Distribution'],
              ['correlation', 'Corrélation'],
              ['repartition', 'Répartition'],
            ].map(([id, label]) => (
              <button key={id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>{label}</button>
            ))}
          </div>

          {tab === 'temps' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Évolution Temporelle — Signature & Vérification</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>{bankStatus?.algo || '—'}</span>
                </div>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={timeSeries} margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" />
                      <XAxis dataKey="i" tick={false} />
                      <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} tickFormatter={v => `${v.toFixed(0)}ms`} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="sign" name="Signature (ms)" stroke="var(--black)" dot={false} strokeWidth={1.5} />
                      <Line type="monotone" dataKey="verify" name="Vérification (ms)" stroke="var(--gray-400)" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
                      <Line type="monotone" dataKey="total" name="Total (ms)" stroke="var(--gray-700)" dot={false} strokeWidth={1} strokeDasharray="1 3" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Stats table */}
              <div className="card">
                <div className="card-header"><span className="card-title">Statistiques Descriptives</span></div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                  <thead>
                    <tr>
                      {['Opération', 'Moyenne', 'Min', 'Max', 'Écart-type', 'Médiane'].map(h => (
                        <th key={h} style={{ textAlign: 'left', padding: '8px 0', borderBottom: 'var(--border)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--gray-500)', fontWeight: 400 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ['Signature', signTimes],
                      ['Vérification', verifyTimes],
                    ].map(([name, arr]) => {
                      const sorted = [...arr].sort((a, b) => a - b);
                      const med = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
                      return (
                        <tr key={name}>
                          <td style={{ padding: '9px 0', borderBottom: 'var(--border)' }}>{name}</td>
                          <td style={{ padding: '9px 0', borderBottom: 'var(--border)' }}>{formatMs(avg(arr))}</td>
                          <td style={{ padding: '9px 0', borderBottom: 'var(--border)', color: 'var(--gray-500)' }}>{formatMs(Math.min(...arr))}</td>
                          <td style={{ padding: '9px 0', borderBottom: 'var(--border)', color: 'var(--gray-500)' }}>{formatMs(Math.max(...arr))}</td>
                          <td style={{ padding: '9px 0', borderBottom: 'var(--border)', color: 'var(--gray-500)' }}>{formatMs(std(arr))}</td>
                          <td style={{ padding: '9px 0', borderBottom: 'var(--border)', color: 'var(--gray-500)' }}>{formatMs(med)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="grid-2">
                <InfoBox title="Interprétation — Signature">
                  La signature nécessite un calcul cryptographique avec la clé privée. En RSA, cela implique une exponentiation modulaire avec un exposant privé de grande taille. En ECDSA, une multiplication scalaire sur la courbe elliptique.
                </InfoBox>
                <InfoBox title="Interprétation — Vérification">
                  La vérification utilise la clé publique. En RSA, l'exposant public (65537) est petit, rendant la vérification très rapide. En ECDSA, deux multiplications scalaires sont nécessaires, ce qui est plus coûteux.
                </InfoBox>
              </div>
            </div>
          )}

          {tab === 'distribution' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="card">
                <div className="card-header"><span className="card-title">Distribution des Temps de Signature</span></div>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={histData} margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" vertical={false} />
                      <XAxis dataKey="range" tick={{ fontFamily: 'var(--font-mono)', fontSize: 8 }} />
                      <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Fréquence" fill="var(--black)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <InfoBox title="Distribution des Temps">
                La distribution des temps de traitement révèle la variance de l'algorithme. Une distribution étroite indique des performances stables et prévisibles, essentielle pour les systèmes de paiement temps-réel. Une grande variance peut indiquer des interférences du système d'exploitation ou des variations dans la taille des données.
              </InfoBox>
            </div>
          )}

          {tab === 'correlation' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Temps de Signature vs Montant de la Transaction</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--gray-400)' }}>Chaque point = 1 transaction</span>
                </div>
                <div style={{ height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" />
                      <XAxis type="number" dataKey="x" name="Montant" tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} tickFormatter={v => `${v}€`} />
                      <YAxis type="number" dataKey="y" name="Signature" tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} tickFormatter={v => `${v.toFixed(0)}ms`} />
                      <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0]?.payload;
                        return (
                          <div className="custom-tooltip">
                            <div>Montant : {formatEur(d?.x)}</div>
                            <div>Signature : {formatMs(d?.y)}</div>
                          </div>
                        );
                      }} />
                      <Scatter data={scatterData} fill="var(--black)" opacity={0.6} r={3} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <InfoBox title="Corrélation Montant / Temps">
                Le temps de signature cryptographique ne dépend pas du montant de la transaction : il dépend uniquement de la taille de la clé et du message. Un nuage de points vertical indique l'absence de corrélation, ce qui est le comportement attendu et souhaitable.
              </InfoBox>
            </div>
          )}

          {tab === 'repartition' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="card">
                <div className="card-header"><span className="card-title">Types de Transactions</span></div>
                {txTypeData.length > 0 ? (
                  <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={txTypeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                          {txTypeData.map((entry, i) => (
                            <Cell key={entry.key} fill={GRAYS[i % GRAYS.length]} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend iconSize={10} wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div style={{ padding: 20, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-400)' }}>Pas de données</div>
                )}
              </div>

              <div className="card">
                <div className="card-header"><span className="card-title">Statut des Transactions</span></div>
                {statusData.length > 0 ? (
                  <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                          {statusData.map((entry) => (
                            <Cell key={entry.name} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend iconSize={10} wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div style={{ padding: 20, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-400)' }}>Pas de données</div>
                )}
              </div>

              {/* Volume chart */}
              <div className="card" style={{ gridColumn: '1 / -1' }}>
                <div className="card-header"><span className="card-title">Volume par Type (nombre de transactions)</span></div>
                <div style={{ height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={txTypeData} layout="vertical" margin={{ top: 4, right: 20, bottom: 4, left: 80 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="var(--gray-100)" horizontal={false} />
                      <XAxis type="number" tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} />
                      <YAxis type="category" dataKey="name" tick={{ fontFamily: 'var(--font-mono)', fontSize: 9 }} width={76} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="value" name="Transactions" fill="var(--black)" barSize={14} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
