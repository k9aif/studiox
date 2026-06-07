import { useEffect, useState } from 'react';

interface Step {
  delay: number;
  text: string;
  phase: 'gen' | 'inspect';
}

const STEPS: Step[] = [
  // Phase 1: Analysis
  { delay: 0,    text: 'Parsing spec document…',                                phase: 'gen' },
  { delay: 800,  text: 'Extracting agent definitions from spec…',               phase: 'gen' },
  { delay: 1800, text: 'Running rule-based analysis…',                          phase: 'gen' },
  { delay: 2800, text: 'Calling LLM for intelligent grouping…',                 phase: 'gen' },
  { delay: 4000, text: 'Scoring rule-based output…',                            phase: 'gen' },
  { delay: 5000, text: 'Scoring LLM output…',                                   phase: 'gen' },
  { delay: 6000, text: 'Comparing results — selecting best output…',            phase: 'gen' },
  { delay: 7000, text: 'Building canvas from winner…',                          phase: 'gen' },
  // Phase 2: Validation
  { delay: 8000, text: 'Verifying Router → Orchestrator → Squad connections…', phase: 'inspect' },
  { delay: 9000, text: 'Validating agent zone assignments (GREEN/AMBER/RED)…',  phase: 'inspect' },
  { delay: 9800, text: 'Architecture validated ✓',                              phase: 'inspect' },
];

interface Props {
  visible: boolean;
  result?: { winner: string; winnerScore: number; winnerAgents: number; winnerSquads: number } | null;
}

export function GeneratingOverlay({ visible, result }: Props) {
  const [visibleSteps, setVisibleSteps] = useState<number[]>([]);

  useEffect(() => {
    if (!visible) { setVisibleSteps([]); return; }
    setVisibleSteps([]);
    const timers = STEPS.map((s, i) =>
      setTimeout(() => setVisibleSteps((prev) => [...prev, i]), s.delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [visible]);

  if (!visible) return null;

  const lastVisible = visibleSteps[visibleSteps.length - 1] ?? -1;
  const inInspectPhase = lastVisible >= STEPS.findIndex((s) => s.phase === 'inspect');

  return (
    <div className="gen-overlay">
      <div className="gen-card">
        <div className="gen-logo">
          <span className="logo-k9">K9X</span>
          <span className="logo-studio">Studio</span>
        </div>

        <div className="gen-spinner">
          <div className="gen-spinner-ring" />
        </div>

        <div className="gen-steps">
          {/* Generation phase header */}
          <div className="gen-phase-label">◈ Architecture Generation</div>

          {STEPS.filter((s) => s.phase === 'gen').map((s, i) => (
            <div
              key={i}
              className={`gen-step ${visibleSteps.includes(i) ? 'gen-step-visible' : ''}`}
            >
              <span className="gen-step-dot">
                {visibleSteps.includes(i) ? (i === lastVisible ? '›' : '✓') : '·'}
              </span>
              <span className="gen-step-text">{s.text}</span>
            </div>
          ))}

          {/* Inspector phase header — only shown when inspector steps start */}
          {inInspectPhase && (
            <div className="gen-phase-label gen-phase-inspector">
              <span className="gen-inspector-icon">⊛</span> K9X Inspector Validation
            </div>
          )}

          {STEPS.filter((s) => s.phase === 'inspect').map((s, gi) => {
            const i = STEPS.findIndex((st) => st.phase === 'inspect') + gi;
            return (
              <div
                key={i}
                className={`gen-step gen-step-inspect ${visibleSteps.includes(i) ? 'gen-step-visible' : ''}`}
              >
                <span className="gen-step-dot" style={{ color: '#f59e0b' }}>
                  {visibleSteps.includes(i) ? (i === lastVisible ? '›' : '✓') : '·'}
                </span>
                <span className="gen-step-text">{s.text}</span>
              </div>
            );
          })}
        </div>

        {result && (
          <div style={{
            margin: '12px 0 4px', padding: '8px 12px',
            background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)',
            borderRadius: 6, fontSize: 12, color: '#6ee7b7', textAlign: 'center',
          }}>
            ✓ <strong>{result.winner}</strong> selected · {result.winnerAgents} agents · {result.winnerSquads} squads · score {result.winnerScore}
          </div>
        )}
        <div className="gen-footer">
          Powered by K9-AIF Architecture-First Framework · k9x.ai
        </div>
      </div>
    </div>
  );
}
