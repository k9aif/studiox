import { useEffect, useState } from 'react';

// Ravi: "It has to say stuff in a card like Analyzing..... Processing....
// Generating..... in a card to make it look like it is working ... rather
// than being lightning fast." Scaffold export (handleExport in Studio.tsx)
// is a separate flow from canvas generation (GeneratingOverlay, bound to
// `generating`) — this is bound to `exporting` instead, reusing the same
// .gen-* CSS classes for visual consistency rather than duplicating them.
// Deliberately just 3 stages, matching the same cadence already used for
// the Intake tab's own staged Generate button.
const STEPS = [
  { delay: 0,    text: 'Analyzing project structure…' },
  { delay: 700,  text: 'Processing agents & orchestrators…' },
  { delay: 1400, text: 'Generating scaffold files…' },
];

// Ravi: "I want to know when the backend LLM is being used. Display while
// processing... it will be nice to see." Shown only when usingLlm is true
// (richDocs checkbox on) — deliberately never auto-advances to a "✓ done"
// checkmark like the fake STEPS above, since the real LLM call's duration
// is genuinely unknown; it just stays lit until the request actually
// finishes and `visible` goes false.
const LLM_STEP_DELAY = 2100; // right after the last fake STEPS entry

export function ExportingOverlay({ visible, usingLlm = false }: { visible: boolean; usingLlm?: boolean }) {
  const [visibleSteps, setVisibleSteps] = useState<number[]>([]);
  const [llmStepShown, setLlmStepShown] = useState(false);

  useEffect(() => {
    if (!visible) { setVisibleSteps([]); setLlmStepShown(false); return; }
    setVisibleSteps([]);
    setLlmStepShown(false);
    const timers = STEPS.map((s, i) =>
      setTimeout(() => setVisibleSteps((prev) => [...prev, i]), s.delay)
    );
    if (usingLlm) {
      timers.push(setTimeout(() => setLlmStepShown(true), LLM_STEP_DELAY));
    }
    return () => timers.forEach(clearTimeout);
  }, [visible, usingLlm]);

  if (!visible) return null;

  const lastVisible = visibleSteps[visibleSteps.length - 1] ?? -1;

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
          <div className="gen-phase-label">◈ Building Scaffold</div>
          {STEPS.map((s, i) => (
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

          {llmStepShown && (
            <div className="gen-step gen-step-visible" style={{ marginTop: 4 }}>
              <span className="gen-step-dot" style={{ color: '#a78bfa', animation: 'llm-pulse 0.8s ease-in-out infinite' }}>🧠</span>
              <span className="gen-step-text" style={{ color: '#c4b5fd' }}>
                Calling the configured LLM to narrate documents — this can take a minute…
              </span>
            </div>
          )}
        </div>

        <div className="gen-footer">
          Powered by K9-AIF Architecture-First Framework · k9x.ai
        </div>
      </div>
    </div>
  );
}
