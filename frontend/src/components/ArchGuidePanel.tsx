export function ArchGuidePanel() {
  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '32px 48px', maxWidth: 900 }}>

      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0', marginBottom: 6 }}>
          Architecture Gate — Classify Before You Build
        </div>
        <div style={{ fontSize: 14, color: '#94a3b8', lineHeight: 1.7 }}>
          Not every step in your pipeline needs an LLM. Use this gate to classify each task before
          adding a component to the canvas. Agentic AI and deterministic adapters each have a
          natural home — mixing them correctly is what makes K9-AIF systems maintainable at scale.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 28 }}>

        {/* Use Agentic AI */}
        <div style={{ background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: 10, padding: '18px 20px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
            ✓ Use Agentic AI when
          </div>
          {[
            'Input is unstructured — text, images, ambiguous events',
            'Decision requires reasoning under uncertainty',
            'Success criteria are subjective or context-dependent',
            'The plan must adapt dynamically mid-execution',
            'Competing options need nuanced trade-off analysis',
            'Recovery from unexpected failure requires judgment',
            'The task involves synthesising information from many sources',
          ].map((item) => (
            <div key={item} style={{ fontSize: 13, color: '#94a3b8', padding: '4px 0 4px 10px', borderLeft: '2px solid rgba(16,185,129,0.4)', marginBottom: 5, lineHeight: 1.5 }}>
              {item}
            </div>
          ))}
        </div>

        {/* Use Adapter */}
        <div style={{ background: 'rgba(245,158,11,0.05)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 10, padding: '18px 20px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
            ⇒ Use an Adapter (Deterministic) when
          </div>
          {[
            'Input is structured and rules are fully defined',
            'Same input always produces the same output',
            'A workflow / BPM / rules platform already owns this logic',
            'LLM latency or cost is prohibitive at this step',
            'Auditability requires an exact, explainable trace',
            'MuleSoft, TIBCO, Appian, Drools, or IBM ODM handles it today',
            'The logic can be written as deterministic code right now',
          ].map((item) => (
            <div key={item} style={{ fontSize: 13, color: '#94a3b8', padding: '4px 0 4px 10px', borderLeft: '2px solid rgba(245,158,11,0.4)', marginBottom: 5, lineHeight: 1.5 }}>
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* Hybrid Pattern */}
      <div style={{ background: 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 10, padding: '18px 24px', marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#a5b4fc', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
          ◈ Hybrid Pattern — Most Real Systems
        </div>
        <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.8 }}>
          The <span style={{ color: '#6366f1', fontWeight: 600 }}>Router</span> classifies incoming events.
          Fully deterministic events (known structure, known rules) go <em>directly</em> to an{' '}
          <span style={{ color: '#f59e0b', fontWeight: 600 }}>Adapter</span> — no LLM involved.
          Complex or ambiguous events route to an{' '}
          <span style={{ color: '#8b5cf6', fontWeight: 600 }}>Orchestrator</span> that freely
          mixes <span style={{ color: '#0ea5e9', fontWeight: 600 }}>Squads</span> (agentic) and
          Adapters (deterministic) in the same pipeline. The K9-AIF canvas enforces these connections.
        </div>
        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#64748b', flexWrap: 'wrap' }}>
          <span style={{ color: '#475569' }}>Event</span>
          <span>→</span>
          <span style={{ color: '#6366f1', background: 'rgba(99,102,241,0.12)', padding: '2px 8px', borderRadius: 4 }}>Router</span>
          <span>→</span>
          <span style={{ color: '#f59e0b', background: 'rgba(245,158,11,0.10)', padding: '2px 8px', borderRadius: 4 }}>Adapter (deterministic)</span>
          <span style={{ color: '#475569', margin: '0 4px' }}>or</span>
          <span style={{ color: '#8b5cf6', background: 'rgba(139,92,246,0.10)', padding: '2px 8px', borderRadius: 4 }}>Orchestrator</span>
          <span>→</span>
          <span style={{ color: '#0ea5e9', background: 'rgba(14,165,233,0.10)', padding: '2px 8px', borderRadius: 4 }}>Squad</span>
          <span style={{ color: '#475569' }}>+</span>
          <span style={{ color: '#f59e0b', background: 'rgba(245,158,11,0.10)', padding: '2px 8px', borderRadius: 4 }}>Adapter</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>

        {/* Anti-patterns */}
        <div style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.18)', borderRadius: 10, padding: '18px 20px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#f87171', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
            ✗ Anti-Patterns to Avoid
          </div>
          {[
            'Routing every event through an LLM "just to be safe"',
            'Wrapping a simple REST call in a ValidationLoop agent',
            'Replacing a rules engine with a prompt that mimics it',
            'Using agents for batch ETL with no decision-making',
            'Building 10+ agents when 2 agents + 1 adapter suffice',
            'Calling an LLM for structured data that a SQL query handles',
          ].map((item) => (
            <div key={item} style={{ fontSize: 13, color: '#94a3b8', padding: '4px 0 4px 10px', borderLeft: '2px solid rgba(239,68,68,0.35)', marginBottom: 5, lineHeight: 1.5 }}>
              {item}
            </div>
          ))}
        </div>

        {/* Quick classification */}
        <div style={{ background: 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.18)', borderRadius: 10, padding: '18px 20px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#a5b4fc', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
            Quick Classification
          </div>
          {[
            ['Is the input structured?',            '→ Adapter'],
            ['Are the rules fully deterministic?',  '→ Adapter'],
            ['Requires judgment or reasoning?',      '→ Agent'],
            ['Can a human write the logic today?',  '→ Adapter / Rules'],
            ['Plan changes on interim results?',     '→ Agent'],
            ['Existing platform owns this step?',    '→ Adapter'],
            ['Output must be auditable & exact?',    '→ Adapter'],
            ['Task involves ambiguity or context?',  '→ Agent'],
          ].map(([q, a]) => (
            <div key={q} style={{ fontSize: 12, color: '#64748b', marginBottom: 7, display: 'flex', justifyContent: 'space-between', gap: 8, lineHeight: 1.4 }}>
              <span>{q}</span>
              <span style={{ color: '#8b5cf6', whiteSpace: 'nowrap', fontWeight: 700 }}>{a}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ borderTop: '1px solid #1e293b', paddingTop: 18, fontSize: 13, color: '#475569', fontStyle: 'italic', lineHeight: 1.7 }}>
        <strong style={{ color: '#64748b', fontStyle: 'normal' }}>K9-AIF principle:</strong>{' '}
        Agents handle uncertainty. Adapters handle certainty. The architecture gate is the first
        decision you make — before touching the canvas. Build cheap deterministic paths first;
        only reach for an LLM when the problem genuinely requires reasoning.
      </div>
    </div>
  );
}
