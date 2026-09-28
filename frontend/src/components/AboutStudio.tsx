export function AboutStudio() {
  return (
    <div style={{ maxWidth: 640, padding: '4px 0' }}>
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>
          K9X Studio
        </div>
        <div style={{ fontSize: 14, color: '#6366f1', fontStyle: 'italic', marginBottom: 16 }}>
          Not just agents — architecture.
        </div>
        <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.8 }}>
          K9X Studio is a visual drag-and-drop workbench for designing K9-AIF compliant
          multi-agent architectures. Upload a <strong style={{ color: '#c8d0de' }}>BPMN
          diagram</strong>, <strong style={{ color: '#c8d0de' }}>process spec (.md)</strong>, and{' '}
          <strong style={{ color: '#c8d0de' }}>Agent Evaluation Plan (-evals.md)</strong> — from any BPMN 2.0
          tool or IBM Process Studio — to generate the full set of artifacts: canvas, traceability matrix, framework coverage
          analysis, and a ready-to-run scaffold.
        </div>
      </div>

      {/* Where this fits — design-time flow originating upstream of this studio */}
      <div style={{
        marginBottom: 28, padding: '12px 16px',
        background: 'rgba(20,184,166,0.05)', border: '1px solid #14b8a633', borderRadius: 8,
        fontSize: 13, color: '#94a3b8', lineHeight: 2,
      }}>
        <span style={{ color: '#14b8a6', fontWeight: 600 }}>Design-time flow: </span>
        <span>Your process (any BPMN 2.0 tool, a written spec, or IBM Process Studio)</span>
        <span style={{ color: '#475569' }}> → </span>
        <span style={{ color: '#a5b4fc', fontWeight: 600 }}>K9X Studio (this)</span>
      </div>

      {/* Workflow */}
      <div style={{
        marginBottom: 28, padding: '12px 16px',
        background: 'rgba(99,102,241,0.06)', border: '1px solid #2a2d3e', borderRadius: 8,
        fontSize: 13, color: '#94a3b8', lineHeight: 2,
      }}>
        <span style={{ color: '#6366f1', fontWeight: 600 }}>How to use: </span>
        <span style={{ color: '#a5b4fc' }}>Setup LLM (optional — BPMN/spec import is rule-based by default)</span>
        <span style={{ color: '#475569' }}> → </span>
        <span>Upload BPMN + Spec + Eval Plan</span>
        <span style={{ color: '#475569' }}> → </span>
        <span>Canvas auto-generates</span>
        <span style={{ color: '#475569' }}> → </span>
        <span style={{ color: '#10b981', fontWeight: 600 }}>⬇ Generate Scaffold</span>
      </div>

      {/* What it does */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '1px' }}>
          What it does
        </div>
        {[
          ['📄', 'Upload Spec Doc',    'Upload a project spec or blueprint (.md) — canvas auto-generates with Router, Orchestrators, Squads, Agents.'],
          ['🔵', 'Upload BPMN',        'Upload BPMN 2.0 exports from Camunda, Bizagi, Blueworks Live, Process Studio or any other tool — canvas auto-generates from the process flow.'],
          ['🛡',  'Upload Eval Plan',   'Upload an Agent Evaluation Plan (-evals.md) — stages test cases, maps each to the framework component that already covers it, and generates a tests/evals/*.py stub per case in the scaffold.'],
          ['🎨', 'Visual Canvas',      'Drag-and-drop K9-AIF components. Connect Router → Orchestrator → Squad → Agents visually.'],
          ['📐', 'Templates',          'Start from pre-built templates: Insurance, Finance, Healthcare, Customer Service, and more.'],
          ['⬇',  'Generate Scaffold',  'Download a ready-to-run K9-AIF project ZIP with all boilerplate generated.'],
        ].map(([icon, title, desc]) => (
          <div key={title as string} style={{ display: 'flex', gap: 12, marginBottom: 12, padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
            <span style={{ fontSize: 18 }}>{icon}</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>{title as string}</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>{desc as string}</div>
            </div>
          </div>
        ))}
      </div>

      {/* How canvas is generated */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '1px' }}>
          How the Canvas is Generated
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.8, marginBottom: 8 }}>
          The studio uses a <strong style={{ color: '#c8d0de' }}>layered approach</strong> to generate the architecture canvas. The backend has built-in rules to decide when the LLM needs to be used — and when it doesn't. If you don't see the processing overlay, it means the canvas was generated instantly using rule-based logic, which is by design.
        </div>
        {[
          ['1', 'Structured spec document (.md)', 'The spec doc contains section 3.1.8 Agent Definition Register — a table with agent names, zones (GREEN/AMBER/RED), and patterns. Generated by enterprise architecture tools, process modelers, or hand-crafted. The parser extracts agents directly and groups by zone. No LLM required. Deterministic and instant.', '#10b981'],
          ['2', 'LLM grouping (optional, when configured)', 'If an LLM is configured and the spec has structured agents, the LLM is asked to group them semantically into squads. Both the LLM result and rule-based result are scored — the richer output wins. If LLM returns fewer agents than expected, rule-based is used.', '#6366f1'],
          ['3', 'Free-form spec / manual entry', 'If the document has no structured agent register (a free-form spec, or a Project Intake Form), the configured LLM generates the architecture from its text. With no LLM configured, a generic starter template is used instead. Templates, BPMN, blueprints and eval plans never use the LLM.', '#f59e0b'],
          ['4', 'BPMN / template / manual', 'BPMN uploads extract tasks from process flows. Templates use hand-designed architectures. Manual entry uses the intake fields with LLM or rule-based defaults.', '#8b5cf6'],
        ].map(([num, title, desc, color]) => (
          <div key={num as string} style={{ display: 'flex', gap: 12, marginBottom: 12, marginTop: 8, padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
            <div style={{ width: 22, height: 22, borderRadius: '50%', background: color as string, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, flexShrink: 0, marginTop: 1 }}>{num as string}</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#c8d0de', marginBottom: 3 }}>{title as string}</div>
              <div style={{ fontSize: 11, color: '#64748b', lineHeight: 1.6 }}>{desc as string}</div>
            </div>
          </div>
        ))}
      </div>

      {/* k9x_ output prefix convention — Ravi: "somewhere in the About, we
          have to mention that for the input files, the corresponding
          output files with the prefix k9x_ is generated to show the
          mapping with the framework component / task." */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Every Input Gets a Mapped k9x_ Output
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.8, marginBottom: 8 }}>
          Every file you upload gets a corresponding <code style={{ color: '#c8d0de' }}>k9x_</code>-prefixed
          document back in the scaffold, showing exactly how it maps onto the generated K9-AIF components —
          your original content stays intact; K9X Studio only adds the mapping on top.
        </div>
        {[
          ['📄', 'Process specification (.md)', 'k9x_traceability-matrix.xlsx / .csv', 'Every process element mapped to its generated component, base class, zone, and governance posture.'],
          ['🌐', 'HTML spec export (e.g. IBM Process Studio)', 'k9x_<filename>.html', 'The same document, unmodified, with "K9X "-prefixed Component/Base Type columns injected directly into its own Agent Definition Register table.'],
          ['🛡', 'Agent Evaluation Plan (-evals.md)', 'k9x_<filename>-evals.md', 'Every test case with its real k9x_Shield framework coverage — the same view shown live in the Evals tab.'],
        ].map(([icon, input, output, desc]) => (
          <div key={input as string} style={{ display: 'flex', gap: 12, marginBottom: 12, padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
            <span style={{ fontSize: 18 }}>{icon}</span>
            <div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                <span style={{ color: '#c8d0de', fontWeight: 500 }}>{input as string}</span>
                <span style={{ color: '#475569' }}> → </span>
                <code style={{ color: '#a78bfa' }}>{output as string}</code>
              </div>
              <div style={{ fontSize: 11, color: '#64748b', lineHeight: 1.6, marginTop: 3 }}>{desc as string}</div>
            </div>
          </div>
        ))}
      </div>

      {/* LLM note */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Architecture Standards & LLM
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.8, marginBottom: 10 }}>
          The canvas always follows <strong style={{ color: '#c8d0de' }}>K9-AIF architecture standards</strong> — Router → Orchestrator → Squad → Agent hierarchy, with zone-based agent classification (GREEN / AMBER / RED).<br/><br/>
          When an LLM is configured, it interprets the uploaded spec and groups agents into squads. The <strong style={{ color: '#c8d0de' }}>flow on the canvas may differ depending on the LLM chosen</strong> — a stronger model produces richer, more contextual groupings. A weaker model may return fewer agents or incomplete structure, in which case the system falls back to rule-based grouping.
        </div>
        {[
          ['✓ Best',     'Claude Haiku / Sonnet / Opus',      'Reliable JSON, consistent groupings every run — recommended for production use'],
          ['✓ Good',     'qwen2.5:7b or 13b+ instruct',       'Strong JSON output, good squad grouping. 13b+ gives more consistent results than 7b'],
          ['⚠ Limited', 'granite3.3:8b (reasoning model)',   'Reasoning model, not optimised for JSON generation — inconsistent squad groupings'],
          ['✗ Avoid',   'granite-code / code models',         'Code generation models — not designed for architecture analysis or JSON structuring'],
          ['✗ Avoid',   'Models under 7B',                    'Too small for structured JSON output — falls back to rule-based automatically'],
        ].map(([badge, model, desc]) => (
          <div key={model as string} style={{ display: 'flex', gap: 12, marginBottom: 8, padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6 }}>
            <span style={{ fontSize: 11, color: (badge as string).startsWith('✓') ? '#10b981' : '#f59e0b', flexShrink: 0, marginTop: 1 }}>{badge as string}</span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)' }}>{model as string}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>{desc as string}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Eval Coverage by Category */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Built-In Coverage for Agent Evaluation Plans
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.8, marginBottom: 10 }}>
          An Agent Evaluation Plan (-evals.md, e.g. from IBM Process Studio) classifies every test case into
          one of eight categories. Two of those categories are already substantially implemented by the K9-AIF
          framework — not asserted, verified against the framework's own source and{' '}
          <span style={{ color: '#c8d0de' }}>k9x_satan</span>'s attack suite. Stage an eval plan on the
          Intake tab and the Evals tab shows this same breakdown per test case, for the actual project.
        </div>
        {[
          ['✓ Covered',  'Adversarial Evals',
            '45 of 50 typical cases map directly to one of k9x_Shield’s 13 built-in vulnerability checks (prompt injection, insecure output handling, memory/system-prompt exfiltration, tool authorization, execution guardrails, PII, DoS). Wired into every generated agent by default — an SA verifies the config is on, not writes new detection logic.'],
          ['✓ Covered',  'Behavioral Evals',
            'AMBER-zone "never auto-approves" is real, generated code today: K9ValidationLoopAgent.should_continue’s confidence-threshold ESCALATE path.'],
          ['⚠ Partial',  'Behavioral & Adversarial — RED zone / Overreliance',
            'The ESCALATE decision plumbing (K9CriticActorAgent.should_accept) is framework-provided, but critique()’s domain judgment is a TODO stub the SA must implement before the test can be trusted.'],
          ['— Solution', 'Functional Evals',
            'Tests the solution’s own business logic (e.g. "Classify & Code GL Account") — the framework provides the agent pattern to put that logic in, not the logic itself. Can never be framework-generic.'],
          ['— Solution', 'Domain Evals',
            'Domain-specific correctness rubrics defined per solution — same reasoning as Functional Evals.'],
          ['□ Planned',  'Observability Validation',
            'No metrics-emission ABB exists yet. Roadmap: a BaseMetricsEmitter contract with OOB adapters (Stdout/Prometheus), alert thresholds declared as SBB config — mirroring how security.shield is configured today.'],
          ['□ Planned',  'Human-in-the-Loop Validation',
            'No HITL-routing ABB exists yet. Roadmap: an EscalationSink contract with an OOB K9HilEscalationAdapter routing ESCALATE outcomes into k9x_hil’s queue with SLA tracking.'],
          ['□ Planned',  'Failure Mode & Fallback Testing',
            'Overlaps Observability (dashboards) and HITL routing (fallback path) above — closes once both roadmap items do.'],
        ].map(([badge, category, desc]) => (
          <div key={category as string} style={{ display: 'flex', gap: 12, marginBottom: 8, padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6 }}>
            <span style={{
              fontSize: 11, flexShrink: 0, marginTop: 1, minWidth: 74,
              color: (badge as string).startsWith('✓') ? '#10b981' : (badge as string).startsWith('⚠') ? '#f59e0b' : (badge as string).startsWith('□') ? '#6366f1' : '#64748b',
            }}>{badge as string}</span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{category as string}</div>
              <div style={{ fontSize: 11, color: '#64748b', lineHeight: 1.6 }}>{desc as string}</div>
            </div>
          </div>
        ))}
      </div>

      {/* K9X Ecosystem */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '1px' }}>
          K9X Ecosystem
        </div>
        {[
          ['studio.k9x.ai',    'This tool — visual K9-AIF designer', true],
          ['pip install k9x',  'Run your own instance of this Studio — locally or in a container', '#ffd166'],
          ['k9x-modernize',    'Reverse-engineer legacy code → K9-AIF blueprint → feed into Studio', false],
          ['graph.k9x.ai',     'Neo4j graph explorer for K9-AIF architectures', false],
          ['k9-aif-framework', 'The K9-AIF ABB library — BaseAgent, K9ValidationLoopAgent, K9CriticActorAgent, BaseGovernance', false],
        ].map(([name, desc, highlight]) => (
          <div key={name as string} style={{ display: 'flex', gap: 12, marginBottom: 8, fontSize: 12 }}>
            <span style={{ color: typeof highlight === 'string' ? highlight : highlight ? '#34d399' : '#6366f1', minWidth: 160, fontWeight: highlight ? 600 : 500 }}>{name as string}</span>
            <span style={{ color: '#94a3b8' }}>{desc as string}</span>
          </div>
        ))}
      </div>

      {/* How the studio itself is built */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '1px' }}>
          How This Studio Is Built
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.8, marginBottom: 12 }}>
          K9X Studio doesn't just help you design K9-AIF architectures — it is one. It runs{' '}
          <span style={{ color: '#a5b4fc' }}>pip install k9-aif</span> to pull in the published{' '}
          <span style={{ color: '#a5b4fc' }}>k9_aif_abb</span> framework package and builds its
          own router and agent layers — <span style={{ color: '#a5b4fc' }}>studio_core</span> /{' '}
          <span style={{ color: '#a5b4fc' }}>studio_agents</span> — directly on top of it.
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.8, marginBottom: 12 }}>
          The spec-import flow you just used — upload a doc, get a canvas — runs as a real
          K9-AIF squad: <span style={{ color: '#a5b4fc' }}>GovernanceAgent</span> screens the
          document, then <span style={{ color: '#a5b4fc' }}>SpecParserAgent</span> spawns three
          sub-agents in parallel (project info, agent table, zone mapping) via{' '}
          <span style={{ color: '#a5b4fc' }}>K9SubAgentSpawner</span>, and{' '}
          <span style={{ color: '#a5b4fc' }}>LLMGroupingAgent</span> /{' '}
          <span style={{ color: '#a5b4fc' }}>ScoringAgent</span> /{' '}
          <span style={{ color: '#a5b4fc' }}>CanvasBuilderAgent</span> assemble the suggested
          architecture you see on the canvas.
        </div>
        <a
          href="/architecture/index.html"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            fontSize: 12, fontWeight: 600, color: '#34d399',
            padding: '8px 14px', border: '1px solid #2a2d3e', borderRadius: 8,
            background: 'rgba(52,211,153,0.06)', textDecoration: 'none',
          }}
        >
          🏗 View the Studio's own architecture (v2.0) ↗
        </a>
      </div>

      {/* Future enhancements — documented ideas, not yet built. Running list —
          add here first, batch-implement later, rather than one-off notes
          scattered across tabs. */}
      <div style={{
        marginBottom: 28, padding: '12px 16px',
        background: 'rgba(245,158,11,0.05)', border: '1px solid #f59e0b33', borderRadius: 8,
        fontSize: 12, color: '#94a3b8', lineHeight: 1.8,
      }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#f59e0b', marginBottom: 10 }}>
          🔮 Future Enhancements
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ color: '#f59e0b', fontWeight: 600, marginBottom: 4 }}>1. Requirements Compliance Check</div>
          <div>
            After scaffold generation, use a backend LLM to check the generated
            <span style={{ color: '#c8d0de' }}> implementation-plan.md</span> traceability matrix against the original
            <span style={{ color: '#c8d0de' }}> spec/blueprint .md</span> (not the BPMN — that's structure-only; not the
            eval plan — that's derived from the blueprint, not the original ask) — flagging any named agent, tool,
            HITL touchpoint, observability metric, or behavioral rule from the blueprint with no corresponding row in
            the generated matrix, using whichever LLM is configured in Setup.
          </div>
        </div>

        <div>
          <div style={{ color: '#f59e0b', fontWeight: 600, marginBottom: 4 }}>2. Document the Intake→Traceability Pipeline</div>
          <div>
            Deepen this page's <span style={{ color: '#c8d0de' }}>"How the Canvas is Generated"</span> section with
            the actual under-the-hood mechanics: BPMN/blueprint/eval files are fully parsed at <em>upload</em> time
            (XML tree walk / regex table extraction), not at Generate time — clicking Generate just joins two
            already-parsed structures via <span style={{ color: '#c8d0de' }}>blueprint_service.combine()</span>'s
            three-way match (BPMN task name ↔ blueprint ATS step name ↔ agent's Owned Steps), which is why it
            completes in milliseconds with zero LLM calls. Worth explaining so it doesn't read as suspiciously fast.
          </div>
        </div>
      </div>

      {/* Build info */}
      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {[
          ['Version',    '0.5.3'],
          ['Created by', 'Ravi Natarajan & Claude Code'],
          ['Framework',  'K9-AIF · Architecture-First Agentic AI'],
          ['Website',    'k9x.ai'],
        ].map(([label, value]) => (
          <div key={label as string} style={{ display: 'flex', gap: 12, fontSize: 11 }}>
            <span style={{ color: '#475569', minWidth: 90 }}>{label as string}</span>
            {label === 'Website'
              ? <a href="https://k9x.ai" target="_blank" rel="noopener noreferrer" style={{ color: '#6366f1' }}>{value as string}</a>
              : <span style={{ color: '#64748b' }}>{value as string}</span>
            }
          </div>
        ))}
      </div>
    </div>
  )
}
