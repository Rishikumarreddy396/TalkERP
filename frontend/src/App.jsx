import { useState, useRef, useEffect } from 'react';

/* ── Icons ──────────────────────────────────────────────────────────── */
const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);
const SparklesIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" />
  </svg>
);
const DatabaseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
  </svg>
);
const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const AlertIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);
const ClockIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
);

/* ── Color tokens ───────────────────────────────────────────────────── */
const C = {
  bgPrimary: '#0a0e1a',
  bgCard: '#1a1f36',
  bgCardHover: '#222847',
  bgInput: '#151b30',
  brand: '#6366f1',
  brandLight: '#818cf8',
  emerald: '#10b981',
  amber: '#f59e0b',
  rose: '#f43f5e',
  cyan: '#06b6d4',
  text1: '#f1f5f9',
  text2: '#94a3b8',
  text3: '#64748b',
  border: '#1e293b',
};

/* ── Loading Dots ───────────────────────────────────────────────────── */
function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 py-3">
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 8, height: 8, borderRadius: '50%', background: C.brandLight, display: 'inline-block',
          animation: `dotPulse 1.2s ease-in-out infinite`, animationDelay: `${i * 0.15}s`,
        }} />
      ))}
      <style>{`@keyframes dotPulse { 0%,80%,100%{opacity:.3;transform:scale(.8)} 40%{opacity:1;transform:scale(1.2)} }`}</style>
    </div>
  );
}

/* ── SQL Code Block ─────────────────────────────────────────────────── */
function SqlBlock({ sql }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => { navigator.clipboard.writeText(sql); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  return (
    <div style={{ borderRadius: 8, overflow: 'hidden', border: `1px solid ${C.border}`, background: C.bgPrimary }}>
      <div className="flex items-center justify-between px-4 py-2" style={{ background: C.bgCard, borderBottom: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-2 text-xs" style={{ color: C.text3, fontFamily: 'var(--font-mono)' }}>
          <DatabaseIcon /><span>PostgreSQL</span>
        </div>
        <button onClick={handleCopy} className="text-xs px-2 py-1 rounded cursor-pointer transition-colors" style={{ color: C.text3, background: 'transparent' }}
          onMouseEnter={e => e.target.style.color = C.text1} onMouseLeave={e => e.target.style.color = C.text3}>
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 text-sm overflow-x-auto leading-relaxed" style={{ color: C.cyan, fontFamily: 'var(--font-mono)', margin: 0 }}>
        <code>{sql}</code>
      </pre>
    </div>
  );
}

/* ── Data Table ─────────────────────────────────────────────────────── */
function DataTable({ columns, rows, rowCount, executionTime, truncated }) {
  return (
    <div style={{ borderRadius: 8, border: `1px solid ${C.border}`, overflow: 'hidden' }}>
      <div className="flex items-center justify-between px-4 py-2.5" style={{ background: C.bgCard, borderBottom: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-2 text-sm" style={{ color: C.text2 }}>
          <DatabaseIcon /><span className="font-medium">{rowCount} rows</span>
          {truncated && <span className="text-xs" style={{ color: C.amber }}>(truncated)</span>}
        </div>
        {executionTime && (
          <div className="flex items-center gap-1 text-xs" style={{ color: C.text3 }}>
            <ClockIcon /><span>{executionTime.toFixed(1)} ms</span>
          </div>
        )}
      </div>
      <div className="overflow-x-auto" style={{ maxHeight: 400, overflowY: 'auto' }}>
        <table className="w-full text-sm">
          <thead style={{ background: C.bgCard, position: 'sticky', top: 0, zIndex: 10 }}>
            <tr>
              {columns.map((col, i) => (
                <th key={i} className="text-left px-4 py-2.5 text-xs font-semibold uppercase tracking-wider whitespace-nowrap"
                  style={{ color: C.text2, borderBottom: `1px solid ${C.border}` }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="transition-colors" style={{ borderBottom: `1px solid ${C.border}` }}
                onMouseEnter={e => e.currentTarget.style.background = C.bgCardHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                {columns.map((col, j) => (
                  <td key={j} className="px-4 py-2.5 whitespace-nowrap text-xs"
                    style={{ color: C.text1, fontFamily: 'var(--font-mono)' }}>
                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : <span style={{ color: C.text3, fontStyle: 'italic' }}>null</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Insight Card ───────────────────────────────────────────────────── */
function InsightCard({ title, items, icon, color }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{ borderRadius: 8, border: `1px solid ${C.border}`, background: C.bgCard, padding: 16 }}>
      <div className="flex items-center gap-2 mb-3">
        <span style={{ color }}>{icon}</span>
        <h4 className="text-sm font-semibold" style={{ color: C.text1 }}>{title}</h4>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm leading-relaxed" style={{ color: C.text2 }}>
            <span style={{ marginTop: 6, width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Status Badge ───────────────────────────────────────────────────── */
function StatusBadge({ status }) {
  const map = {
    success: { bg: 'rgba(16,185,129,0.15)', color: C.emerald, border: 'rgba(16,185,129,0.3)' },
    failed:  { bg: 'rgba(244,63,94,0.15)', color: C.rose, border: 'rgba(244,63,94,0.3)' },
    pending: { bg: 'rgba(245,158,11,0.15)', color: C.amber, border: 'rgba(245,158,11,0.3)' },
    running: { bg: 'rgba(99,102,241,0.15)', color: C.brandLight, border: 'rgba(99,102,241,0.3)' },
    retrying:{ bg: 'rgba(245,158,11,0.15)', color: C.amber, border: 'rgba(245,158,11,0.3)' },
  };
  const s = map[status] || map.pending;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full"
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
      {status === 'success' ? <CheckIcon /> : <AlertIcon />}{status}
    </span>
  );
}

/* ── AI Response ────────────────────────────────────────────────────── */
function AIResponse({ data }) {
  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={data.status} />
        {data.total_duration_ms && (
          <span className="flex items-center gap-1 text-xs" style={{ color: C.text3 }}>
            <ClockIcon /> {(data.total_duration_ms / 1000).toFixed(1)}s total
          </span>
        )}
      </div>

      {data.error && (
        <div className="rounded-lg p-4 text-sm" style={{ background: 'rgba(244,63,94,0.1)', border: `1px solid rgba(244,63,94,0.3)`, color: C.rose }}>
          <div className="flex items-center gap-2 font-semibold mb-1"><AlertIcon /> Error</div>
          {data.error}
        </div>
      )}

      {data.generator?.sql && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: C.text3 }}>Generated SQL</h3>
          <SqlBlock sql={data.generator.sql} />
          <div className="flex gap-3 mt-2 text-xs" style={{ color: C.text3 }}>
            <span>Complexity: <span style={{ color: C.text2 }}>{data.generator.complexity}</span></span>
            <span>Tables: <span style={{ color: C.text2 }}>{data.generator.tables_referenced?.join(', ')}</span></span>
          </div>
        </div>
      )}

      {data.validator && (
        <div className="flex items-center gap-2 text-xs flex-wrap" style={{ color: C.text3 }}>
          {data.validator.is_valid
            ? <span className="flex items-center gap-1" style={{ color: C.emerald }}><CheckIcon /> Validated</span>
            : <span className="flex items-center gap-1" style={{ color: C.rose }}><AlertIcon /> Validation issues</span>}
          <span>({data.validator.validation_attempts} attempt{data.validator.validation_attempts > 1 ? 's' : ''})</span>
          {data.validator.issues?.length > 0 && (
            <span style={{ color: C.amber }}>— {data.validator.issues.join('; ')}</span>
          )}
        </div>
      )}

      {data.execution && data.execution.rows?.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: C.text3 }}>Query Results</h3>
          <DataTable columns={data.execution.columns} rows={data.execution.rows} rowCount={data.execution.row_count}
            executionTime={data.execution.execution_time_ms} truncated={data.execution.truncated} />
        </div>
      )}

      {data.summarizer?.summary && (
        <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(6,182,212,0.1))', border: `1px solid rgba(99,102,241,0.2)` }}>
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: C.brandLight }}>
            <SparklesIcon /> AI Summary
          </h3>
          <p className="text-sm leading-relaxed" style={{ color: C.text1 }}>{data.summarizer.summary}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <InsightCard title="Key Insights" items={data.summarizer?.key_insights} icon={<SparklesIcon />} color={C.cyan} />
        <InsightCard title="Recommended Actions" items={data.summarizer?.recommended_actions} icon={<CheckIcon />} color={C.emerald} />
      </div>
    </div>
  );
}

/* ── Example Questions ──────────────────────────────────────────────── */
const EXAMPLES = [
  "Show me all recent orders",
  "Which product category generates the most revenue?",
  "List top 5 vendors by total sales value",
  "What is the average order value by customer city?",
  "Show canceled orders with their customer details",
];

/* ── Main App ───────────────────────────────────────────────────────── */
export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const handleSubmit = async (question) => {
    const q = question || input.trim();
    if (!q || loading) return;
    setInput('');
    setMessages(prev => [...prev, { type: 'user', text: q }]);
    setLoading(true);
    try {
      const res = await fetch('/api/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q, max_rows: 500 }) });
      const data = await res.json();
      setMessages(prev => [...prev, { type: 'ai', data }]);
    } catch (err) {
      setMessages(prev => [...prev, { type: 'ai', data: { status: 'failed', error: `Network error: ${err.message}`, question: q } }]);
    } finally { setLoading(false); }
  };

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', width: '100%', background: C.bgPrimary, color: C.text1 }}>

      {/* ── Header ──────────────────────────────────────────────────── */}
      <header style={{ position: 'sticky', top: 0, zIndex: 40, width: '100%', borderBottom: `1px solid ${C.border}`, background: 'rgba(10,14,26,0.85)', backdropFilter: 'blur(20px)' }}>
        <div style={{ maxWidth: 896, margin: '0 auto', padding: '16px 24px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold text-sm"
              style={{ background: `linear-gradient(135deg, ${C.brand}, ${C.cyan})`, boxShadow: `0 4px 12px rgba(99,102,241,0.25)` }}>T</div>
            <div>
              <h1 className="text-lg font-bold tracking-tight" style={{ color: C.text1 }}>TalkERP</h1>
              <p className="text-xs" style={{ color: C.text3 }}>AI-Powered ERP Analytics</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs" style={{ color: C.text3 }}>
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: C.emerald }} />Online
          </div>
        </div>
      </header>

      {/* ── Chat Area ───────────────────────────────────────────────── */}
      <main style={{ flex: 1, overflowY: 'auto', width: '100%' }}>
        <div style={{ maxWidth: 896, margin: '0 auto', padding: '32px 24px', width: '100%' }} className="space-y-6">

          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-20 animate-fade-in-up">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 animate-pulse-glow text-white"
                style={{ background: `linear-gradient(135deg, ${C.brand}, ${C.cyan})` }}>
                <SparklesIcon />
              </div>
              <h2 className="text-2xl font-bold mb-2" style={{ color: C.text1 }}>Ask your ERP anything</h2>
              <p className="text-sm mb-8 text-center max-w-md" style={{ color: C.text2 }}>
                Type a business question in plain English. TalkERP generates SQL, queries your database, and delivers executive insights.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
                {EXAMPLES.map((ex, i) => (
                  <button key={i} onClick={() => handleSubmit(ex)}
                    className="text-left px-4 py-3 rounded-lg text-sm cursor-pointer transition-all"
                    style={{ border: `1px solid ${C.border}`, background: C.bgCard, color: C.text2 }}
                    onMouseEnter={e => { e.target.style.background = C.bgCardHover; e.target.style.borderColor = 'rgba(99,102,241,0.4)'; e.target.style.color = C.text1; }}
                    onMouseLeave={e => { e.target.style.background = C.bgCard; e.target.style.borderColor = C.border; e.target.style.color = C.text2; }}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}
              style={{ animationDelay: `${i * 0.05}s` }}>
              {msg.type === 'user' ? (
                <div className="max-w-[80%] px-5 py-3 rounded-2xl text-sm font-medium text-white"
                  style={{ borderBottomRightRadius: 4, background: `linear-gradient(135deg, ${C.brand}, ${C.brandLight})`, boxShadow: `0 4px 12px rgba(99,102,241,0.2)` }}>
                  {msg.text}
                </div>
              ) : (
                <div className="w-full">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-6 h-6 rounded-md flex items-center justify-center text-white"
                      style={{ background: `linear-gradient(135deg, ${C.brand}, ${C.cyan})` }}>
                      <SparklesIcon />
                    </div>
                    <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: C.text3 }}>TalkERP Agent</span>
                  </div>
                  <div style={{ paddingLeft: 32 }}>
                    <AIResponse data={msg.data} />
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex justify-start animate-fade-in-up">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md flex items-center justify-center animate-pulse text-white"
                  style={{ background: `linear-gradient(135deg, ${C.brand}, ${C.cyan})` }}>
                  <SparklesIcon />
                </div>
                <span className="text-xs" style={{ color: C.text3 }}>Thinking...</span>
                <LoadingDots />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* ── Input Bar ───────────────────────────────────────────────── */}
      <footer style={{ position: 'sticky', bottom: 0, width: '100%', borderTop: `1px solid ${C.border}`, background: 'rgba(10,14,26,0.92)', backdropFilter: 'blur(20px)' }}>
        <div style={{ maxWidth: 896, margin: '0 auto', padding: '16px 24px', width: '100%' }}>
          <div className="flex items-center gap-3 rounded-xl px-4 py-2"
            style={{ background: C.bgInput, border: `1px solid ${C.border}`, boxShadow: '0 4px 24px rgba(0,0,0,0.2)', transition: 'border-color 0.2s' }}
            onFocus={e => e.currentTarget.style.borderColor = C.brand}
            onBlur={e => e.currentTarget.style.borderColor = C.border}>
            <input type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder="Ask a business question..." disabled={loading} id="query-input"
              className="flex-1 text-sm outline-none py-2"
              style={{ background: 'transparent', color: C.text1, opacity: loading ? 0.5 : 1 }} />
            <button onClick={() => handleSubmit()} disabled={loading || !input.trim()} id="send-button"
              className="flex items-center justify-center w-9 h-9 rounded-lg text-white cursor-pointer transition-all"
              style={{ background: C.brand, opacity: loading || !input.trim() ? 0.3 : 1 }}>
              <SendIcon />
            </button>
          </div>
          <p className="text-center text-xs mt-2" style={{ color: C.text3 }}>
            TalkERP generates read-only SQL queries. Results are limited to 500 rows.
          </p>
        </div>
      </footer>
    </div>
  );
}
