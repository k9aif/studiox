import { useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { useStore } from '../store';
import { Icon, type IconKind } from './Icons';

// Restructured 2026-09-12 to match Process Studio's own welcome modal
// exactly (Ravi shared a live screenshot: "see how big the card is" — a
// wide, dense single screen with a WELCOME pill, one H1, one intro
// paragraph, then 3 stacked icon+title+description rows with dividers,
// not a "next next" single-topic-per-screen carousel).
//
// Content grouping per Ravi: "cards talk about beauty of the framework
// and its value, ABB/SBB, Abstract classes, and so on.. next cards talk
// about studio and ecosystem" — step 2 is K9-AIF the framework, step 3 is
// K9X Studio + the wider K9X ecosystem (Continuum/HIL/SATAN, "can go in
// the last card"). Framework/Studio copy below is pulled from k9x.ai
// itself (Ravi: "has so much details to reuse") rather than paraphrased,
// so it matches the site's own voice.
type Row = { icon: IconKind; color: string; title: string; desc: string };
type Step = {
  badge: string;
  badgeColor: string;
  title: string;
  intro: React.ReactNode;
  flow?: boolean;
  rows?: Row[];
  quote?: { text: string; attribution: string };
  ecosystem?: { name: string; desc: string }[];
};

function RowIcon({ kind, color }: { kind: IconKind; color: string }) {
  return (
    <div className="ob-row-icon" style={{ color }}>
      <Icon kind={kind} size={18} />
    </div>
  );
}

// Matches Process Studio's own "QUICK START GUIDE" numbered horizontal
// stepper (screenshot: 1-2-3-4 circles joined by a line, label under each,
// current step filled/highlighted) — Ravi: "here is where we show: context
// studio ---> Process studio OR pick blueprint --> generate project
// artifacts --> K9X Studio --> Implementation Scaffold code ready with
// developer guide". This is an illustrative pipeline diagram, not our
// wizard's own step progress (that's ob-dots in the footer) — "K9X Studio"
// is highlighted as "where this app sits" in that pipeline, not as a
// literal current-step marker.
const STAGES = [
  'Your process',
  'BPMN / Spec / Eval plan',
  'K9X Studio',
  'Scaffold + Dev Guide',
];
const STAGE_ACTIVE_INDEX = 2;

function StageStepper() {
  return (
    <div className="ob-stepper">
      {STAGES.map((label, idx) => (
        <div className="ob-stepper-node" key={label}>
          <div className={`ob-stepper-circle ${idx === STAGE_ACTIVE_INDEX ? 'ob-stepper-circle-active' : ''}`}>
            {idx + 1}
          </div>
          <div className={`ob-stepper-label ${idx === STAGE_ACTIVE_INDEX ? 'ob-stepper-label-active' : ''}`}>
            {label}
          </div>
        </div>
      ))}
    </div>
  );
}

const STEPS: Step[] = [
  {
    badge: 'WELCOME',
    badgeColor: '#8a3ffc',
    title: 'Turn your process into implementation-ready agent workflows',
    intro: (
      <p>
        K9X Studio is pure generation — it doesn't design your business
        process for you. Bring the artifacts you already have: a{' '}
        <strong>BPMN diagram</strong> from any BPMN 2.0 tool, a{' '}
        <strong>process specification</strong>, and an{' '}
        <strong>agent evaluation plan</strong> — including exports from{' '}
        <strong>IBM Process Studio</strong>. Any one of them works; all three
        together give the richest result: a fuller architecture canvas, and
        generated test code from the eval plan.
      </p>
    ),
    flow: true,
  },
  {
    badge: 'K9-AIF FRAMEWORK',
    badgeColor: '#24a148',
    title: 'Not just agents, architecture.',
    intro: (
      <p>
        K9-AIF is an architecture-first framework for building governed,
        secure, enterprise-scale AI applications — OOA/OOD principles,
        TOGAF-aligned design. Every capability K9X Studio generates traces
        back to this same foundation.
      </p>
    ),
    rows: [
      {
        icon: 'architecture', color: '#8a3ffc',
        title: 'ABB / SBB & Patterns and Reuse',
        desc: 'Architecture Building Blocks are stable, abstract contracts defining governance and validation; Solution Building Blocks are swappable concrete implementations that extend them — your project-specific code, never a one-off script.',
      },
      {
        icon: 'gauge', color: '#eb6f00',
        title: 'Intelligent Model Router',
        desc: 'K9ModelRouter selects the right model per task by weighing task type, data sensitivity, latency budget, and cost profile — deliberately, not by default.',
      },
      {
        icon: 'loop', color: '#0f62fe',
        title: 'Validation Loop & Critic-Actor Patterns',
        desc: 'AMBER-zone confidence-threshold retries and RED-zone actor-critic review — reliability patterns built into the generated code, not added later.',
      },
    ],
    // Ravi: "the grady booch quote, can be subtle and not that bright. we
    // can in fact put it back in slide-2 at the bottom. best place. since
    // the last slide looks out of place." — back from the closing step,
    // rendered below the rows grid (not folded into it as a 4th box this
    // time) with muted styling so it reads as a closing footnote, not a
    // competing headline.
    quote: {
      text: '"The entire history of software engineering is one of rising levels of abstraction. This is as it was, is now, and always shall be."',
      attribution: '— Grady Booch, IBM Fellow (Ret.)',
    },
  },
  {
    badge: 'K9X STUDIO & ECOSYSTEM',
    badgeColor: '#da1e28',
    title: 'From Spec Doc or BPMN to Governed Architecture',
    intro: (
      <p>
        With the artifacts from step one in hand, K9X Studio generates a
        routed, orchestrated, squad-based agent architecture on a visual
        canvas — even from the BPMN diagram alone, though bringing the
        blueprint spec and eval plan too gives the most complete, traceable
        result. Governance is enforced at every boundary of{' '}
        <strong>Event → Router → Orchestrator → Squad → Agent → LLM</strong>.
      </p>
    ),
    rows: [
      {
        icon: 'shield', color: '#0f62fe',
        title: 'Governed Execution',
        // Ravi: "the first card and second can be same size... make the
        // first card which is small same size as 2nd one" — lengthened to
        // match Zero Trust Execution's body length below.
        desc: 'Policy-checked before every action executes — End-to-End Governance with zone classification (GREEN/AMBER/RED) and audit events on every squad and agent generated.',
      },
      {
        icon: 'shield', color: '#da1e28',
        title: 'Zero Trust Execution',
        desc: 'Every agent action verified and risk-evaluated prior to execution — OWASP Top 10 for LLM apps and Zscaler ThreatLabZ research, enforced automatically.',
      },
      {
        icon: 'package', color: '#8a3ffc',
        title: 'Observable by Default — k9x_Shield',
        desc: 'Every routing decision persisted, full audit trail — k9x_Shield’s 13-check chain (prompt injection, credential/PII boundaries, and more) runs on every call.',
      },
    ],
    ecosystem: [
      { name: 'K9X Enterprise Continuum', desc: 'TOGAF-aligned SBB/ABB catalog' },
      { name: 'K9X HIL', desc: 'Kafka-native human-in-the-loop case management' },
      { name: 'K9X SATAN', desc: 'Adversarial validation & security testing' },
    ],
  },
  {
    // Ravi: "just the title and one liner to indicate it? your choice." —
    // trimmed from a 4-row breakdown to a single line; everything it
    // covered (Import/Review/Adjust/Generate) is already the landing
    // page's own "How It Works" section, no need to re-explain it here.
    // The button below says "Close" (not "Get Started") — Ravi: "clicking
    // on 'Get Started' here goes back to the landing page... only from
    // the landing page one can enter the Studio Dashboard" — this card's
    // job is just to remind the architect what to bring, then close.
    badge: "YOU'RE READY",
    badgeColor: '#8a3ffc',
    title: 'Next Steps',
    intro: (
      <p>
        Keep your BPMN, process spec and eval plan ready, then click Close
        and Get Started.
      </p>
    ),
  },
];

// Ravi went back and forth on the final button's behavior a few times —
// landed here: "when I click on Get Started, show the landing page fully
// to admire the full page. meaning this card would disappear." So the
// final step's button, like every other step's Back/✕, just closes the
// wizard onto the landing page — the landing page's own "Get Started" is
// what actually auto-logs in and launches the studio.
export function OnboardingWizard({ onFinish }: { onFinish: () => void }) {
  const { setHideOnboarding } = useStore();
  const [i, setI] = useState(0);
  const [dontShow, setDontShow] = useState(false);

  const step = STEPS[i];
  const isFirst = i === 0;
  const isLast = i === STEPS.length - 1;

  const close = () => {
    if (dontShow) setHideOnboarding(true);
    onFinish();
  };

  // Ravi: "can I move the card around the screen? ... like cursor on top
  // bar of the card, move around" — drag from the header only (buttons in
  // it stay clickable, checked via closest('button') below), tracked as a
  // fixed-position offset. `pos` stays null (card centered via .ob-overlay's
  // flexbox, untouched) until the first drag; once set, an inline
  // position:fixed style takes the card out of that centered flow.
  const cardRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);

  const onHeaderPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest('button')) return;
    const rect = cardRef.current!.getBoundingClientRect();
    dragRef.current = { startX: e.clientX, startY: e.clientY, origX: rect.left, origY: rect.top };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onHeaderPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const d = dragRef.current;
    if (!d) return;
    const rect = cardRef.current!.getBoundingClientRect();
    const margin = 12;
    const x = Math.min(Math.max(d.origX + (e.clientX - d.startX), margin), window.innerWidth - rect.width - margin);
    const y = Math.min(Math.max(d.origY + (e.clientY - d.startY), margin), window.innerHeight - rect.height - margin);
    setPos({ x, y });
  };

  const onHeaderPointerUp = (e: ReactPointerEvent<HTMLDivElement>) => {
    dragRef.current = null;
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  return (
    <div className="ob-overlay">
      <div
        className="ob-card"
        ref={cardRef}
        style={pos ? { position: 'fixed', left: pos.x, top: pos.y, margin: 0 } : undefined}
      >
        <div
          className="ob-header ob-header-draggable"
          onPointerDown={onHeaderPointerDown}
          onPointerMove={onHeaderPointerMove}
          onPointerUp={onHeaderPointerUp}
        >
          <span className="ob-header-title">K9X Studio</span>
          <button className="ob-close" onClick={close} aria-label="Close">✕</button>
        </div>

        {/* key={i} forces a fresh scroll container per step — otherwise a
            taller step's scrollTop carries over onto the next step and
            clips its badge/title at the top. */}
        <div className="ob-content" key={i}>
          <span className="ob-badge" style={{ background: `${step.badgeColor}22`, color: step.badgeColor }}>
            {step.badge}
          </span>

          <div className="ob-title">{step.title}</div>
          <div className="ob-intro">{step.intro}</div>

          {step.flow && <StageStepper />}

          {step.rows && (
            <div className="ob-rows">
              {step.rows.map((r, idx) => (
                <div className="ob-row" key={idx}>
                  <RowIcon kind={r.icon} color={r.color} />
                  <div>
                    <div className="ob-row-title">{r.title}</div>
                    <div className="ob-row-desc">{r.desc}</div>
                  </div>
                </div>
              ))}
              {/* Ravi: "make it horizontal, add rect boxes, 2 in each row"
                  — folded into the same grid as its 4th cell rather than a
                  separate full-width block underneath, so 3 rows + quote
                  form a compact 2x2 instead of 4 stacked bars. */}
              {step.quote && (
                <blockquote className="ob-row ob-quote">
                  <p>{step.quote.text}</p>
                  <cite>{step.quote.attribution}</cite>
                </blockquote>
              )}
            </div>
          )}

          {step.quote && !step.rows && (
            <blockquote className="ob-quote ob-quote-standalone">
              <p>{step.quote.text}</p>
              <cite>{step.quote.attribution}</cite>
            </blockquote>
          )}

          {step.ecosystem && (
            <div className="ob-ecosystem">
              <div className="ob-ecosystem-label">Part of a growing ecosystem</div>
              <div className="ob-ecosystem-row">
                {step.ecosystem.map((e) => (
                  <div className="ob-ecosystem-chip" key={e.name}>
                    <div className="ob-ecosystem-name">{e.name}</div>
                    <div className="ob-ecosystem-desc">{e.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="ob-footer">
          <label className="ob-dontshow">
            <input
              type="checkbox"
              checked={dontShow}
              onChange={(e) => setDontShow(e.target.checked)}
            />
            Don't show this again
          </label>

          <div className="ob-nav">
            <div className="ob-dots">
              {STEPS.map((_, idx) => (
                <span key={idx} className={`ob-dot ${idx === i ? 'ob-dot-active' : ''}`} />
              ))}
            </div>
            {!isFirst && (
              <button className="ob-btn-back" onClick={() => setI((n) => n - 1)}>Back</button>
            )}
            {!isLast ? (
              <button className="ob-btn-next" onClick={() => setI((n) => n + 1)}>Next</button>
            ) : (
              <button className="ob-btn-next" onClick={close}>Close</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
