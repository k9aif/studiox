import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { OnboardingWizard } from './OnboardingWizard';
import { Icon, type IconKind } from './Icons';
import { autoLogin } from '../lib/autoLogin';
import logo from '../assets/k9aif-logo.png';

// Public, no-login hero page. Same layout as the studiox_ibm landing page
// (hero, "HOW IT WORKS" 4 numbered cards chevron-separated, quick-reference
// flow bar, ecosystem cards) but vendor-neutral copy and its own colour
// theme (.landing-k9x: teal/amber on navy). The onboarding wizard opens
// over this automatically on first visit (unless previously dismissed), and
// can always be reopened via "How K9X Studio works" below.
//
// Each step ties the UI action (import/review/arrange/generate) back to what
// the framework is doing underneath (ABB/SBB composition, zone
// classification, k9x_Shield), not just the mechanical click-path.
const HOW_IT_WORKS: { n: number; color: string; icon: IconKind; title: string; body: string }[] = [
  {
    n: 1, color: '#14b8a6', icon: 'flow', title: 'Import',
    body: 'Bring in a BPMN 2.0 diagram from any modeling tool, a written process specification, and an agent evaluation plan — each optional alone, but together they give the richest result: a fuller architecture canvas, matched GREEN/AMBER/RED zones, and generated test code from the eval plan.',
  },
  {
    n: 2, color: '#0ea5e9', icon: 'gauge', title: 'Review',
    body: 'Every process element is mapped to a GREEN/AMBER/RED autonomy zone and a K9-AIF component. The Traceability tab connects each process step and assertion to its K9X Studio artifact, the same crosswalk the scaffold is generated from.',
  },
  {
    n: 3, color: '#22c55e', icon: 'architecture', title: 'Arrange / Customize',
    body: 'The canvas composes Squads, Agents, and Orchestrators from K9-AIF’s reusable Architecture Building Blocks. The architect can then customize the generated model directly on the canvas — rename, rearrange, or restructure anything before generating.',
  },
  {
    n: 4, color: '#f59e0b', icon: 'shield', title: 'Generate Scaffold',
    body: 'Click Generate to build the traceability matrix, review it and Confirm & Build Canvas, then in Canvas click Generate Scaffold — download as a .zip, or browse the full folder structure in the Studio’s View Scaffold tab.',
  },
];

// Every file dropped on Intake is screened before K9X Studio will touch it.
// Shown inside Card 1 so the safety gate is visible on the very first thing
// a visitor reads, not buried in Setup.
const GUARDIAN_FLOW: { icon: IconKind; label: string }[] = [
  { icon: 'document', label: 'Intake' },
  { icon: 'checklist', label: 'Pre-validation' },
  { icon: 'shield-check', label: 'Granite Guardian' },
  { icon: 'bolt', label: 'Generate' },
];

function GuardianFlowDiagram() {
  return (
    <div className="guardian-flow">
      {GUARDIAN_FLOW.map((step, idx) => (
        <div className="guardian-flow-item" key={step.label}>
          <div className="guardian-flow-box">
            <Icon kind={step.icon} size={18} />
          </div>
          <div className="guardian-flow-label">{step.label}</div>
          {idx < GUARDIAN_FLOW.length - 1 && <span className="guardian-flow-arrow">→</span>}
        </div>
      ))}
    </div>
  );
}

// The real click-path, verified against the running app's actual button
// labels (IntakePanel.tsx's Generate button, MappingDocumentPanel.tsx's
// "✓ Confirm & Build Canvas", Studio.tsx's "⬇ Generate Scaffold").
const FLOW_STEPS: { loc: string; btn?: string }[] = [
  { loc: 'Intake', btn: 'Generate' },
  { loc: 'Traceability', btn: 'Confirm & Build Canvas' },
  { loc: 'Canvas', btn: 'Generate Scaffold' },
  { loc: 'Implement Solution' },
];

// The wider K9X ecosystem, visible on the landing page itself rather than
// only mentioned during onboarding.
const ECOSYSTEM: { name: string; color: string; icon: IconKind; body: string }[] = [
  {
    name: 'K9X Enterprise Continuum', color: '#0ea5e9', icon: 'architecture',
    body: 'A TOGAF-aligned catalog of Architecture and Solution Building Blocks — the reuse layer K9X Studio composes from.',
  },
  {
    name: 'K9X HIL', color: '#22c55e', icon: 'loop',
    body: 'Kafka-native human-in-the-loop case management for AMBER/RED-zone touchpoints your generated agents escalate to.',
  },
  {
    name: 'K9X SATAN', color: '#ef4444', icon: 'package',
    body: 'Adversarial validation and security testing — the same attack suite k9x_Shield’s 13 checks are built to withstand. Future direction: made available per-project so teams can run it against their own generated scaffold.',
  },
];

export function LandingPage() {
  const { setScreen, hideOnboarding, clientId, clearProject, setCenterTab } = useStore();
  const [showWizard, setShowWizard] = useState(false);
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    if (!hideOnboarding) setShowWizard(true);
  }, []);

  // Get Started signs in as the demo user automatically (the SplashScreen
  // form is the fallback if the backend is unreachable), clears any project
  // left over from a prior visit in this browser, and opens on Intake.
  const handleGetStarted = async () => {
    setSigningIn(true);
    const ok = await autoLogin(clientId);
    setSigningIn(false);
    if (ok) { clearProject(); setCenterTab('intake'); }
    setScreen(ok ? 'studio' : 'splash');
  };

  return (
    <div className="landing-screen landing-k9x">
      <div className="landing-topbar">
        <a
          className="landing-brand"
          href="https://k9x.ai"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img src={logo} alt="K9X" className="landing-brand-logo" />
          K9X
        </a>
      </div>

      <div className="landing-hero">
        <h1 className="landing-title">
          K9X Studio
        </h1>
        <p className="landing-tagline">
          <strong>Not Just Agents, Architecture.</strong> Turn an approved
          business process blueprint into governed, production-ready
          multi-agent code.
        </p>
        <div className="landing-cta-row">
          <button className="landing-btn-primary" onClick={handleGetStarted} disabled={signingIn}>
            {signingIn ? 'Loading…' : 'Get Started'}
          </button>
          <button className="landing-btn-ghost" onClick={() => setShowWizard(true)}>
            How K9X Studio works
          </button>
        </div>
      </div>

      <div className="landing-how">
        <div className="landing-how-label">HOW IT WORKS</div>
        <h2 className="landing-how-title">Four steps to a governed, implementation-ready scaffold</h2>
      </div>

      {/* One shared wrapper so the cards row and the flow bar resolve to the
          same width by construction. */}
      <div className="landing-section">
        <div className="landing-steps">
          {HOW_IT_WORKS.map((s, idx) => (
            <div className="landing-step-wrap" key={s.n}>
              <div className="landing-step-card">
                <div className="landing-step-head">
                  <div className="landing-step-badge" style={{ background: s.color }}>{s.n}</div>
                  <div className="landing-step-icon" style={{ color: s.color }}><Icon kind={s.icon} size={20} /></div>
                </div>
                <div className="landing-step-title">{s.title}</div>
                <div className="landing-step-body">{s.body}</div>
                {s.n === 1 && <GuardianFlowDiagram />}
              </div>
              {idx < HOW_IT_WORKS.length - 1 && <span className="landing-step-chevron">›</span>}
            </div>
          ))}
        </div>

        {/* Quick-reference strip naming the exact button clicks, for anyone
            skimming rather than reading all 4 cards. */}
        <div className="landing-flowbar">
          {FLOW_STEPS.map((f, idx) => (
            <div className="landing-flowbar-wrap" key={f.loc}>
              <div className="landing-flowbar-step">
                <div className="landing-flowbar-loc">{f.loc}</div>
                {f.btn && <div className="landing-flowbar-btn">({f.btn})</div>}
              </div>
              {idx < FLOW_STEPS.length - 1 && <span className="landing-flowbar-arrow">→</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="landing-how" style={{ paddingTop: 0 }}>
        <div className="landing-how-label">THE WIDER ECOSYSTEM</div>
        <h2 className="landing-how-title">K9-AIF is a framework — K9X is a growing ecosystem</h2>
      </div>

      <div className="landing-ecosystem">
        {ECOSYSTEM.map((e) => (
          <div className="landing-eco-card" key={e.name}>
            <div className="landing-eco-icon" style={{ color: e.color, background: `${e.color}1a` }}>
              <Icon kind={e.icon} size={20} />
            </div>
            <div className="landing-eco-name">{e.name}</div>
            <div className="landing-eco-body">{e.body}</div>
          </div>
        ))}
      </div>

      <div className="landing-footer">
        K9-AIF Framework · <a href="https://k9x.ai" target="_blank" rel="noopener noreferrer">k9x.ai</a>
      </div>

      {showWizard && <OnboardingWizard onFinish={() => setShowWizard(false)} />}
    </div>
  );
}
