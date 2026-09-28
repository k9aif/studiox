import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { OnboardingWizard } from './OnboardingWizard';
import { Icon, type IconKind } from './Icons';
import logo from '../assets/k9aif-logo.png';
import bgEcosystem from '../assets/landing-bg-ecosystem.png';
import bgCanvas from '../assets/landing-bg-canvas.png';

// Public landing page for K9X Studio. Generic by design: any BPMN 2.0 tool,
// a written process spec, or an agent evaluation plan can feed the Studio;
// IBM Process Studio artifacts are one supported source among them.
// Own look (k9l-* classes, teal/amber on navy) — deliberately distinct from
// the studiox_ibm landing page.

const INPUTS: { icon: IconKind; title: string; body: string }[] = [
  { icon: 'flow', title: 'BPMN 2.0', body: 'Camunda, Bizagi, Blueworks Live, Process Studio — any .bpmn / .xml export' },
  { icon: 'document', title: 'Process specification', body: 'Markdown, text or HTML spec or blueprint' },
  { icon: 'checklist', title: 'Agent evaluation plan', body: 'Test cases become tests/evals stubs in the scaffold' },
  { icon: 'package', title: 'IBM Process Studio', body: 'BPMN, blueprint and eval plan exports supported' },
];

const PIPELINE: { icon: IconKind; label: string; sub: string }[] = [
  { icon: 'document', label: 'Your process', sub: 'BPMN · spec · evals' },
  { icon: 'shield-check', label: 'Guardian screen', sub: 'every upload checked' },
  { icon: 'architecture', label: 'K9-AIF architecture', sub: 'Router → Orchestrator → Squad → Agent' },
  { icon: 'bolt', label: 'Governed scaffold', sub: 'Shield · Zero Trust · HIL wired in' },
];

const STEPS: { title: string; body: string; where: string }[] = [
  {
    title: 'Import',
    where: 'Intake',
    body: 'Upload a BPMN diagram, a process spec, an agent evaluation plan — or all three. Each file is pre-checked and screened by Granite Guardian before Studio touches it.',
  },
  {
    title: 'Trace',
    where: 'Traceability',
    body: 'Every process step is mapped to a K9-AIF component and a GREEN / AMBER / RED autonomy zone. Review the matrix, edit it, then Confirm & Build Canvas.',
  },
  {
    title: 'Shape',
    where: 'Canvas',
    body: 'Routers, Orchestrators, Squads and Agents composed from K9-AIF Architecture Building Blocks. Rename, regroup or add components before you generate.',
  },
  {
    title: 'Generate',
    where: 'Generate Scaffold',
    body: 'Download a runnable K9-AIF project: agents on the right loop patterns, k9x_Shield and governance wired in, eval test stubs, and a developer guide.',
  },
];

const ECOSYSTEM: { name: string; icon: IconKind; body: string }[] = [
  { name: 'K9-AIF Framework', icon: 'architecture', body: 'The open-source ABB library every scaffold builds on — pip install k9-aif.' },
  { name: 'Enterprise Continuum', icon: 'package', body: 'Governed SBB/ABB catalog: publish, review and promote proven components.' },
  { name: 'K9X HIL', icon: 'loop', body: 'Kafka-native human-in-the-loop case management for escalated agent decisions.' },
  { name: 'K9X SATAN', icon: 'shield', body: 'Red-team harness that attacks K9-AIF pipelines to prove the security layers hold.' },
];

export function LandingPage() {
  const { setScreen, hideOnboarding } = useStore();
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    if (!hideOnboarding) setShowWizard(true);
  }, []);

  const getStarted = () => {
    setScreen(sessionStorage.getItem('k9x_authed') === '1' ? 'studio' : 'splash');
  };

  return (
    <div className="k9l">
      {/* Subtle dark backdrop: the K9X ecosystem diagram (inverted) and a real
          Studio canvas, both faded well below the content. */}
      <div className="k9l-bg" aria-hidden="true">
        <div className="k9l-bg-img k9l-bg-eco" style={{ backgroundImage: `url(${bgEcosystem})` }} />
        <div className="k9l-bg-img k9l-bg-canvas" style={{ backgroundImage: `url(${bgCanvas})` }} />
        <div className="k9l-bg-vignette" />
      </div>
      <header className="k9l-top">
        <a className="k9l-brand" href="https://k9x.ai" target="_blank" rel="noopener noreferrer">
          <img src={logo} alt="" className="k9l-brand-logo" />
          <span>K9X</span>
        </a>
        <nav className="k9l-nav">
          <button type="button" onClick={() => setShowWizard(true)}>How it works</button>
          <a href="https://github.com/k9aif/k9-aif-framework" target="_blank" rel="noopener noreferrer">Framework</a>
          <button type="button" className="k9l-nav-cta" onClick={getStarted}>Sign in</button>
        </nav>
      </header>

      <section className="k9l-hero">
        <div className="k9l-hero-text">
          <div className="k9l-eyebrow">K9X Studio · Beta</div>
          <h1>From process to governed multi-agent code.</h1>
          <p>
            Bring the process you already have — a BPMN diagram, a written spec, an evaluation plan.
            K9X Studio maps it onto the K9-AIF architecture and generates a runnable,
            governed scaffold. Not just agents: architecture.
          </p>
          <div className="k9l-cta-row">
            <button type="button" className="k9l-btn-primary" onClick={getStarted}>Get Started</button>
            <button type="button" className="k9l-btn-ghost" onClick={() => setShowWizard(true)}>Take the tour</button>
          </div>
          <div className="k9l-pip">
            <span>Run your own instance</span>
            <code>pip install k9x</code>
          </div>
          <p className="k9l-demo-note">
            This hosted Studio is a demo. K9X Studio is open source (Apache 2.0) —{' '}
            <a href="#run-it-yourself">run it yourself</a> and connect your own LLM.
          </p>
        </div>

        <div className="k9l-pipeline" aria-label="How a process becomes a scaffold">
          {PIPELINE.map((p, idx) => (
            <div className="k9l-pipe-row" key={p.label}>
              <div className="k9l-pipe-icon"><Icon kind={p.icon} size={18} /></div>
              <div>
                <div className="k9l-pipe-label">{p.label}</div>
                <div className="k9l-pipe-sub">{p.sub}</div>
              </div>
              {idx < PIPELINE.length - 1 && <span className="k9l-pipe-line" aria-hidden="true" />}
            </div>
          ))}
        </div>
      </section>

      <section className="k9l-section">
        <div className="k9l-label">Works with</div>
        <div className="k9l-inputs">
          {INPUTS.map((i) => (
            <div className="k9l-input" key={i.title}>
              <div className="k9l-input-icon"><Icon kind={i.icon} size={18} /></div>
              <div className="k9l-input-title">{i.title}</div>
              <div className="k9l-input-body">{i.body}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="k9l-section">
        <div className="k9l-label">How it works</div>
        <h2>Four steps, one source of truth</h2>
        <ol className="k9l-steps">
          {STEPS.map((s, idx) => (
            <li className="k9l-step" key={s.title}>
              <div className="k9l-step-num">{String(idx + 1).padStart(2, '0')}</div>
              <div className="k9l-step-main">
                <div className="k9l-step-title">
                  {s.title}
                  <span className="k9l-step-where">{s.where}</span>
                </div>
                <div className="k9l-step-body">{s.body}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="k9l-section" id="run-it-yourself">
        <div className="k9l-label">Run it yourself</div>
        <h2>Open source, on your machine, with your model</h2>
        <p className="k9l-lede">
          studio.k9x.ai is a shared demo instance. For real work, install K9X Studio locally or in
          your own container, point it at the LLM you choose, and keep your documents on your side.
        </p>
        <div className="k9l-run">
          <div className="k9l-run-step">
            <div className="k9l-run-num">1</div>
            <div className="k9l-run-title">Install</div>
            <code>pip install k9x</code>
          </div>
          <div className="k9l-run-step">
            <div className="k9l-run-num">2</div>
            <div className="k9l-run-title">Start</div>
            <code>k9x studio</code>
          </div>
          <div className="k9l-run-step">
            <div className="k9l-run-num">3</div>
            <div className="k9l-run-title">Configure on the Setup tab</div>
            <div className="k9l-run-body">
              Choose your LLM provider and model (Ollama, OpenAI, Anthropic, watsonx) and your Granite
              Guardian model. Or set them once in <code>.env</code> (<code>k9x config</code> writes a starter file).
            </div>
          </div>
        </div>
        <p className="k9l-run-foot">
          No model is built in: templates, BPMN, blueprints and eval plans never need one, and an LLM is
          only used for free-form specs and manual entry, when you configure it.{' '}
          <a href="https://pypi.org/project/k9x/" target="_blank" rel="noopener noreferrer">PyPI</a>
          {' · '}
          <a href="https://github.com/k9aif/studiox" target="_blank" rel="noopener noreferrer">Source</a>
        </p>
      </section>

      <section className="k9l-section">
        <div className="k9l-label">The K9X ecosystem</div>
        <h2>A framework, and the tools around it</h2>
        <div className="k9l-eco">
          {ECOSYSTEM.map((e) => (
            <div className="k9l-eco-card" key={e.name}>
              <div className="k9l-eco-icon"><Icon kind={e.icon} size={18} /></div>
              <div className="k9l-eco-name">{e.name}</div>
              <div className="k9l-eco-body">{e.body}</div>
            </div>
          ))}
        </div>
      </section>

      <footer className="k9l-footer">
        K9-AIF Framework · <a href="https://k9x.ai" target="_blank" rel="noopener noreferrer">k9x.ai</a>
        {' · '}Apache 2.0
      </footer>

      {showWizard && <OnboardingWizard onFinish={() => setShowWizard(false)} />}
    </div>
  );
}
