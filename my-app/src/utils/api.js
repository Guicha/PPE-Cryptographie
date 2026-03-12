const BASE = 'http://localhost:8000';

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  status: () => apiFetch('/api/status'),
  health: () => apiFetch('/api/health'),

  // Banque
  initBank: (config) => apiFetch('/api/banque/initialiser', {
    method: 'POST', body: JSON.stringify(config),
  }),
  getAccounts: () => apiFetch('/api/banque/comptes'),
  getStats: () => apiFetch('/api/banque/stats'),

  // Transactions
  createTransaction: (req) => apiFetch('/api/transaction', {
    method: 'POST', body: JSON.stringify(req),
  }),
  randomTransaction: () => apiFetch('/api/transaction/aleatoire', { method: 'POST' }),
  getTransactions: (limit = 50) => apiFetch(`/api/transactions?limit=${limit}`),

  // Simulation
  startSim: (tps, duree) => apiFetch('/api/simulation/demarrer', {
    method: 'POST',
    body: JSON.stringify({ tps, duree_secondes: duree || null }),
  }),
  stopSim: () => apiFetch('/api/simulation/arreter', { method: 'POST' }),
  simStatus: () => apiFetch('/api/simulation/status'),

  // Benchmark
  benchmark: (req) => apiFetch('/api/benchmark', {
    method: 'POST', body: JSON.stringify(req),
  }),
  comparison: (iterations, rsaBits) =>
    apiFetch(`/api/benchmark/comparaison?nb_iterations=${iterations}&rsa_bits=${rsaBits}`, {
      method: 'POST',
    }),

  // Algo info
  algoInfo: (algo, rsaBits = 2048) =>
    apiFetch(`/api/algo/info/${algo}?rsa_bits=${rsaBits}`),
  algoParams: () => apiFetch('/api/algo/parametres'),
};

export function createWebSocket(onMessage) {
  const ws = new WebSocket('ws://localhost:8000/ws');
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  ws.onopen = () => { };
  ws.onerror = () => { };
  return ws;
}

export function formatMs(ms) {
  if (ms === undefined || ms === null) return '—';
  if (ms < 1) return `${(ms * 1000).toFixed(0)} µs`;
  if (ms < 1000) return `${ms.toFixed(2)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function formatEur(amount) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount);
}

export function formatIban(iban) {
  if (!iban) return '—';
  return iban.slice(0, 4) + ' **** **** ' + iban.slice(-4);
}

export const TX_TYPE_LABELS = {
  PAIEMENT_CB: 'Paiement CB',
  RETRAIT_DAB: 'Retrait DAB',
  VIREMENT: 'Virement',
  PAIEMENT_MOBILE: 'Paiement Mobile',
  AUTORISATION: 'Autorisation',
  REMBOURSEMENT: 'Remboursement',
};

export const TX_TYPE_ICONS = {
  PAIEMENT_CB: '▣',
  RETRAIT_DAB: '◈',
  VIREMENT: '⇄',
  PAIEMENT_MOBILE: '◉',
  AUTORISATION: '◎',
  REMBOURSEMENT: '↺',
};
