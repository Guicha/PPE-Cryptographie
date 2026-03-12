//qsdnqndoqnsnsqondoqnsdonqsd
//qsdqosndoqnsdk qsonqsnkqnsihqs/qsd
//qsjdqsodnqosndqnosndqskndqsndknn


import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './utils/api';

import PageConfiguration from './pages/PageConfiguration';
import PageTransaction from './pages/PageTransaction';
import PageBanque from './pages/PageBanque';
import PageBenchmark from './pages/PageBenchmark';
import PageAnalyse from './pages/PageAnalyse';

const NAV = [
  { id: 'configuration', label: 'Configuration', icon: '⚙', section: 'SYSTEME' },
  { id: 'banque', label: 'Banque Virtuelle', icon: '⬡', section: null },
  { id: 'transaction', label: 'Transaction', icon: '◈', section: 'OPERATIONS' },
  { id: 'benchmark', label: 'Benchmark', icon: '▦', section: null },
  { id: 'analyse', label: 'Analyse', icon: '◉', section: null },
];

const PAGE_TITLES = {
  configuration: 'Configuration du Système',
  banque: 'Banque Virtuelle',
  transaction: 'Création de Transaction',
  benchmark: 'Benchmark Cryptographique',
  analyse: 'Analyse de Performance',
};

export default function App() {
  const [page, setPage] = useState('configuration');
  const [bankStatus, setBankStatus] = useState(null);
  const [simRunning, setSimRunning] = useState(false);
  const [liveTransactions, setLiveTransactions] = useState([]);
  const [liveMetrics, setLiveMetrics] = useState([]);
  const [clock, setClock] = useState('');

  useEffect(() => {
    api.status().then(setBankStatus).catch(() => {});
    const t = setInterval(() => { api.status().then(setBankStatus).catch(() => {}); }, 5000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const t = setInterval(() => {
      setClock(new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const handleWsEvent = useCallback((event) => {
    switch (event.type) {
      case 'transaction':
        setLiveTransactions(prev => [event.data, ...prev].slice(0, 200));
        break;
      case 'metric':
        setLiveMetrics(prev => [...prev, event.data].slice(-200));
        break;
      case 'simulation_stopped':
        setSimRunning(false);
        break;
      case 'bank_init':
        api.status().then(setBankStatus).catch(() => {});
        break;
      default: break;
    }
  }, []);

  const { connected } = useWebSocket(handleWsEvent);

  const sharedProps = {
    bankStatus, setBankStatus, simRunning, setSimRunning,
    liveTransactions, liveMetrics, setLiveTransactions, setLiveMetrics,
    refreshStatus: () => api.status().then(setBankStatus).catch(() => {}),
  };

  const renderPage = () => {
    switch (page) {
      case 'configuration': return <PageConfiguration {...sharedProps} />;
      case 'banque':        return <PageBanque {...sharedProps} />;
      case 'transaction':   return <PageTransaction {...sharedProps} />;
      case 'benchmark':     return <PageBenchmark {...sharedProps} />;
      case 'analyse':       return <PageAnalyse {...sharedProps} />;
      default: return null;
    }
  };

  const isInit = bankStatus?.initialise;

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-title">BANKLAB</div>
          <div className="sidebar-logo-sub">Cryptographic Testbed v1.0 </div>
        </div>
        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <React.Fragment key={item.id}>
              {item.section && <div className="nav-section-label">{item.section}</div>}
              <button
                className={`nav-item ${page === item.id ? 'active' : ''}`}
                onClick={() => setPage(item.id)}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </button>
            </React.Fragment>
          ))}
        </nav>
        <div className="sidebar-status">
          <div style={{ marginBottom: 6 }}>
            <span className={`status-dot ${connected ? 'green' : 'red'}`} />
            <span style={{ color: connected ? '#a3a3a3' : '#737373', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
              {connected ? 'API connectée' : 'API déconnectée'}
            </span>
          </div>
          <div>
            <span className={`status-dot ${isInit ? 'green' : 'gray'}`} />
            <span style={{ color: '#737373', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
              {isInit ? `${bankStatus.algo} · ${bankStatus.nb_comptes} comptes` : 'Non initialisée'}
            </span>
          </div>
          {simRunning && (
            <div style={{ marginTop: 6 }}>
              <span className="status-dot green" />
              <span style={{ color: '#a3a3a3', fontFamily: 'var(--font-mono)', fontSize: 10 }}>Simulation active</span>
            </div>
          )}
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-title">{PAGE_TITLES[page]}</div>
          <div className="topbar-right">
            {isInit && (
              <span style={{
                background: bankStatus.algo === 'RSA' ? 'var(--black)' : 'var(--white)',
                color: bankStatus.algo === 'RSA' ? 'var(--white)' : 'var(--black)',
                border: '1px solid var(--black)', padding: '3px 8px',
                fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.15em',
              }}>
                {bankStatus.algo}
              </span>
            )}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--gray-400)' }}>{clock}</span>
          </div>
        </header>
        <div className="page-content">{renderPage()}</div>
      </div>
    </div>
  );
}
