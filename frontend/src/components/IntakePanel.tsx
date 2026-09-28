import { useState } from 'react';
import { useStore } from '../store';
import { K9Meter, useClimbingProgress } from './K9Meter';
import { Icon } from './Icons';

function Section({ title, defaultOpen = false, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: 12 }}>
      <button onClick={() => setOpen(v => !v)} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(99,102,241,0.05)', border: '1px solid var(--border)',
        borderRadius: 6, padding: '7px 12px', cursor: 'pointer', marginBottom: open ? 10 : 0,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: '#8892a4', letterSpacing: '0.8px', textTransform: 'uppercase' }}>{title}</span>
        <span style={{ fontSize: 10, color: '#475569' }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && <div>{children}</div>}
    </div>
  );
}

function ProcessStudioGroup({ children }: { children: React.ReactNode }) {
  const KEY = 'k9x-intake-ps-group-open';
  const [open, setOpen] = useState<boolean>(() => {
    try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
  });
  const toggle = () => setOpen(v => {
    try { localStorage.setItem(KEY, v ? '0' : '1'); } catch { /* optional */ }
    return !v;
  });
  return (
    <div className={`intake-ps-group${open ? ' intake-ps-group--open' : ''}`}>
      <button type="button" className="intake-ps-group-header" onClick={toggle} aria-expanded={open}>
        <span className="intake-ps-group-title">IBM Process Studio</span>
        <span className="intake-ps-group-sub">Enterprise App Kit import</span>
        <span className="intake-ps-group-chevron">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="intake-ps-group-body">{children}</div>}
    </div>
  );
}

export function IntakePanel({ onSwitchTab }: { onSwitchTab?: (tab: string) => void }) {
  const { project, setProject, nodes, generating, setGenerating, llmConfig, addLog, setLlmActive, addGeneratedDoc, setPendingCanvasSuggestion, pendingMappingDocument, setPendingMappingDocument, setMappingDocumentConfirmed, specImported, setSpecImported, clearCanvas, clearProject, setLastSpecFile, setLastBpmnFile, canvasIsRuleBased, setCanvasIsRuleBased, setGenResult, setLastTemplateId, stagedBpmn, setStagedBpmn, stagedBlueprint, setStagedBlueprint, stagedEvals, setStagedEvals } = useStore();
  const [wifBusy, setWifBusy] = useState(false);
  const [specBusy, setSpecBusy] = useState(false);
  const [specError, setSpecError] = useState('');
  const [specFileName, setSpecFileName] = useState('');
  const [stagingError, setStagingError] = useState('');
  const [showResume, setShowResume] = useState(false);
  const [showManualEntry, setShowManualEntry] = useState(false);

  // ── Staged-inputs intake (Ravi: "uploading ANY single file ... immediately
  // kicks off canvas/scaffold generation ... makes the three inputs mutually
  // exclusive in practice"). Role is detected by CONTENT, not which of the
  // three upload affordances was used — a file dropped on any of them routes
  // to the right handler. Staging never auto-generates; only the Generate
  // button below does. Implementation Plan restore is the one exception,
  // preserved exactly as it worked before (immediate restore, not staged) —
  // it's a "resume a prior session" action, not an input to combine.
  const looksLikeImplementationPlanText = (text: string): { orchestrators?: unknown } | null => {
    const m = text.match(/```json\n([\s\S]*?)\n```/);
    if (!m) return null;
    try {
      const parsed = JSON.parse(m[1]);
      return 'orchestrators' in parsed ? parsed : null;
    } catch { return null; }
  };
  const looksLikeBpmnText = (text: string) => /<(?:bpmn:)?definitions[\s>]/i.test(text) || /<(?:bpmn:)?process\b/i.test(text);
  // Process Studio's companion eval plan (filename suffix "-evals.md").
  // Checked BEFORE looksLikeBlueprintText below — its own "Behavioral Evals"
  // heading would otherwise count toward that check's threshold and get an
  // eval plan misrouted into blueprint parsing (wrong: it has no MCP tool
  // register, agent roster, etc. — it's test cases, not architecture input).
  const looksLikeEvalsText = (text: string) => {
    if (/^#\s*Agent Evaluation Plan/im.test(text)) return true;
    const headings = [
      /^##\s*Functional Evals/im, /^##\s*Adversarial Evals/im,
      /^##\s*Failure Mode\s*(?:&|and)\s*Fallback Testing/im,
      /^##\s*Human-in-the-Loop Validation/im, /^##\s*Observability Validation/im,
    ];
    return headings.filter((h) => h.test(text)).length >= 2;
  };
  const looksLikeBlueprintText = (text: string) => {
    const headings = [
      /Atomic Thinking Step Register/i, /MCP Tool Register/i,
      /Agent (?:Definition Register|Roster)/i, /Observability Requirements/i, /Behavioral Evals/i,
    ];
    return headings.filter((h) => h.test(text)).length >= 2;
  };

  // ── Mandatory pre-checks, ahead of every staging call. Ravi: "so, here is
  // the flow for the Studio: intake document → pre-validation based on file
  // name and extension → pass checks with granite guardian → only then it
  // is considered to process and generate." Two gates, in order: (1) a
  // free, instant structural check that the CONTENT actually matches the
  // slot it was dropped on (an eval plan uploaded under Process
  // Specification is rejected, not silently re-routed) — "people cannot
  // upload 'eval' into project spec and it would reject"; (2) Granite
  // Guardian, a mandatory LLM safety screen for prompt injection/malicious
  // payloads/unsafe content — "granite guardian is mandatory... some
  // employee uploading a nasty adult document as project is not
  // acceptable." Fails closed: Guardian unreachable or misconfigured blocks
  // the upload rather than skipping the check.
  type IntakeSlot = 'bpmn' | 'spec' | 'evals';
  // Ravi: "we show live flow. pre-processing → IBM Granite Guardian checks
  // → passed green tick. then, Generate will now become Active. until
  // then inactive." — `step` tracks which of the two gates is currently
  // running/last completed, so the UI can render a live 3-node pipeline per
  // upload instead of a single status line. `canGenerate` below already
  // requires stagedBpmn/stagedBlueprint to be set, which gatedStage only
  // does after both gates pass — so Generate is naturally inactive until
  // this pipeline reaches "done" for at least one staged input.
  type CheckStep = 'preprocessing' | 'guardian' | 'done';
  type CheckEntry = { status: 'checking' | 'passed' | 'failed'; step: CheckStep; message?: string; fileName: string };
  const [checkState, setCheckState] = useState<Record<IntakeSlot, CheckEntry | undefined>>({} as any);
  // Ravi: "for all we could just have 1 display at the bottom of those
  // boxes to show the flow beautifully... and below the top box just have
  // a green tick" — one shared pipeline for whichever file is currently
  // (or was most recently) being checked, instead of repeating the same
  // 3-node diagram under all 4 tiles. Each tile keeps only a compact final
  // result (✓/✕).
  const [lastCheckedSlot, setLastCheckedSlot] = useState<IntakeSlot | null>(null);

  // Ravi: "the filenames should be checked. eg. what if I upload a .md into
  // .html? that can be checked immediately when I click upload, right
  // there it should not accept it." — an instant, synchronous check on the
  // extension alone, run before even reading the file's content (no
  // FileReader round-trip, no network) so a mismatched file is rejected the
  // moment it's picked.
  const SLOT_EXTENSIONS: Record<IntakeSlot, string[]> = {
    bpmn: ['.bpmn', '.xml', '.zip'],
    spec: ['.md', '.txt', '.html', '.htm'],
    evals: ['.md'],
  };
  const extensionPreCheck = (slot: IntakeSlot, file: File): { ok: true } | { ok: false; message: string } => {
    const name = file.name.toLowerCase();
    const allowed = SLOT_EXTENSIONS[slot];
    if (!allowed.some((ext) => name.endsWith(ext))) {
      return { ok: false, message: `"${file.name}" has the wrong file type for this slot — expected ${allowed.join('/')}.` };
    }
    return { ok: true };
  };

  const structuralPreCheck = (slot: IntakeSlot, file: File, text: string): { ok: true } | { ok: false; message: string } => {
    const name = file.name;
    const isBpmn = looksLikeBpmnText(text);
    const isEvals = looksLikeEvalsText(text);

    if (slot === 'bpmn') {
      if (/\.zip$/i.test(name)) return { ok: true }; // binary — can't text-inspect, extension is the only signal
      if (!isBpmn) {
        const guess = isEvals ? 'an Agent Evaluation Plan' : looksLikeBlueprintText(text) ? 'a process blueprint' : 'something other than a BPMN diagram';
        return { ok: false, message: `"${name}" doesn't look like a BPMN diagram (expected <definitions>/<process> XML) — it looks like ${guess}. Upload it under the matching slot instead.` };
      }
      return { ok: true };
    }
    if (slot === 'evals') {
      if (!isEvals) {
        return { ok: false, message: `"${name}" doesn't look like an Agent Evaluation Plan (expected a "# Agent Evaluation Plan" heading, or Functional/Adversarial/HITL Evals sections). Upload it under the matching slot instead.` };
      }
      return { ok: true };
    }
    if (slot === 'spec') {
      if (isBpmn) return { ok: false, message: `"${name}" looks like a BPMN diagram — upload it under BPMN Diagram instead.` };
      if (isEvals) return { ok: false, message: `"${name}" looks like an Agent Evaluation Plan — upload it under Agent Evaluation Plan instead.` };
      return { ok: true };
    }
    return { ok: true };
  };

  const runGuardianCheck = async (file: File, text: string): Promise<{ ok: true } | { ok: false; message: string }> => {
    // Ravi: "wire to this under the hood" — the server prefers its own
    // GOVERNANCE_LLM_ENDPOINT/MODEL env config over anything sent here (see
    // routes.py's _guardian_config), so it can resolve Guardian even when
    // Setup was never touched. Don't gate the request on local llmConfig
    // being populated — that would block every upload on a deployed
    // instance where Guardian is already wired server-side and Setup is
    // legitimately empty. Whatever's in llmConfig is sent as a local-dev
    // fallback only; the server has the final say.
    try {
      const res = await fetch('/api/guardian/check', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name, content: text,
          llm_endpoint: llmConfig?.endpoint ?? '', llm_provider: llmConfig?.provider ?? '',
          llm_model: llmConfig?.guardianModel ?? '', llm_api_key: llmConfig?.api_key ?? '',
        }),
      });
      const data = await res.json();
      if (!res.ok) return { ok: false, message: data.detail ?? `Guardian check failed (${res.status})` };
      if (data.skipped) return { ok: true };
      if (!data.safe) return { ok: false, message: `Guardian flagged this file as unsafe${data.reason ? ': ' + data.reason : ''}.` };
      return { ok: true };
    } catch (err: any) {
      return { ok: false, message: `Guardian unreachable: ${err.message ?? 'network error'}` };
    }
  };

  const gatedStage = async (slot: IntakeSlot, file: File, doStage: (f: File) => Promise<void>) => {
    setStagingError('');
    setLastCheckedSlot(slot);
    setCheckState((s) => ({ ...s, [slot]: { status: 'checking', step: 'preprocessing', fileName: file.name } }));

    // Instant, synchronous — rejected before any file read or network call.
    const extCheck = extensionPreCheck(slot, file);
    if (!extCheck.ok) {
      setCheckState((s) => ({ ...s, [slot]: { status: 'failed', step: 'preprocessing', message: extCheck.message, fileName: file.name } }));
      addLog(`✕ Pre-check failed: ${extCheck.message}`, 'error');
      return;
    }

    let text = '';
    try { text = await file.text(); } catch { /* binary file */ }

    const structural = structuralPreCheck(slot, file, text);
    if (!structural.ok) {
      setCheckState((s) => ({ ...s, [slot]: { status: 'failed', step: 'preprocessing', message: structural.message, fileName: file.name } }));
      addLog(`✕ Pre-check failed: ${structural.message}`, 'error');
      return;
    }

    setCheckState((s) => ({ ...s, [slot]: { status: 'checking', step: 'guardian', fileName: file.name } }));
    addLog(`Pre-check passed for ${file.name} — running Granite Guardian safety screen…`);
    const guardian = await runGuardianCheck(file, text);
    if (!guardian.ok) {
      setCheckState((s) => ({ ...s, [slot]: { status: 'failed', step: 'guardian', message: guardian.message, fileName: file.name } }));
      addLog(`✕ Guardian blocked upload: ${guardian.message}`, 'error');
      return;
    }

    setCheckState((s) => ({ ...s, [slot]: { status: 'passed', step: 'done', fileName: file.name } }));
    addLog(`✓ Pre-checks passed — ${file.name}`);
    await doStage(file);
  };

  // Live 3-node pipeline per upload: Pre-processing → Granite Guardian →
  // Passed. Each node is grey (not reached), amber+spinner (active), green
  // check (cleared), or red X (failed here) — mirrors the landing page's
  // GuardianFlowDiagram but reflects real per-file state instead of being
  // static.
  //
  // Ravi: "under each upload we display pre-check, guardian etc.. but for
  // all we could just have 1 display at the bottom of those boxes to show
  // the flow beautifully... and below the top box just have a green tick."
  // — one shared 3-node pipeline for whichever file was most recently
  // checked (lastCheckedSlot), instead of repeating it under all 4 tiles;
  // each tile itself now only shows a compact final result.
  const nodeState = (st: CheckEntry, step: CheckStep): 'pending' | 'active' | 'done' | 'failed' => {
    const order: CheckStep[] = ['preprocessing', 'guardian', 'done'];
    const curIdx = order.indexOf(st.step);
    const stepIdx = order.indexOf(step);
    if (st.status === 'failed' && st.step === step) return 'failed';
    if (stepIdx < curIdx || st.status === 'passed') return 'done';
    if (stepIdx === curIdx && st.status === 'checking') return 'active';
    return 'pending';
  };
  const nodeStyle = (s: 'pending' | 'active' | 'done' | 'failed') => ({
    color: s === 'done' ? '#34d399' : s === 'failed' ? '#f87171' : s === 'active' ? '#f59e0b' : '#475569',
    fontWeight: s === 'pending' ? 400 : 600,
  });
  const nodeGlyph = (s: 'pending' | 'active' | 'done' | 'failed') =>
    s === 'done' ? '✓' : s === 'failed' ? '✕' : s === 'active' ? <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span> : '○';

  // Compact per-tile result — just the outcome, not the pipeline breakdown.
  const TileCheckBadge = ({ slot }: { slot: IntakeSlot }) => {
    const st = checkState[slot];
    if (!st) return null;
    if (st.status === 'checking') return (
      <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 6, display: 'flex', alignItems: 'center', gap: 5 }}>
        <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span> Checking…
      </div>
    );
    if (st.status === 'passed') return (
      <div style={{ fontSize: 11, color: '#34d399', marginTop: 6 }}>✓ Passed</div>
    );
    return (
      <div style={{ fontSize: 11, color: '#f87171', marginTop: 6 }}>✕ {st.message}</div>
    );
  };

  // The one shared, elegant pipeline strip at the bottom of Import Sources.
  const ImportPipeline = () => {
    if (!lastCheckedSlot) return null;
    const st = checkState[lastCheckedSlot];
    if (!st) return null;
    return (
      <div className="intake-pipeline">
        <div className="intake-pipeline-file">
          {st.status === 'checking' ? 'Checking' : st.status === 'passed' ? 'Cleared' : 'Blocked'}: <code>{st.fileName}</code>
        </div>
        <div className="intake-pipeline-row">
          <span style={nodeStyle(nodeState(st, 'preprocessing'))}>{nodeGlyph(nodeState(st, 'preprocessing'))} Pre-checks</span>
          <span className="intake-pipeline-arrow">→</span>
          <span style={nodeStyle(nodeState(st, 'guardian'))}>{nodeGlyph(nodeState(st, 'guardian'))} Granite Guardian</span>
          <span className="intake-pipeline-arrow">→</span>
          <span style={nodeStyle(nodeState(st, 'done'))}>{nodeGlyph(nodeState(st, 'done'))} Passed</span>
        </div>
        {st.status === 'failed' && st.message && (
          <div style={{ fontSize: 11.5, color: '#f87171', marginTop: 6 }}>✕ {st.message}</div>
        )}
      </div>
    );
  };

  const restoreImplementationPlan = async (file: File, snapshot: any) => {
    setPendingCanvasSuggestion(null);
    setLastTemplateId(null);
    clearCanvas();
    setGenerating(true);
    onSwitchTab?.('canvas');
    await new Promise((r) => setTimeout(r, 50));
    setLastSpecFile(null);
    setLastBpmnFile(file);
    setCanvasIsRuleBased(true);
    if (snapshot.project_name) setProject({ ...project, ...snapshot });
    try {
      const res = await fetch('/api/mapping-document/from-project', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(snapshot),
      });
      const mapping_document = await res.json();
      if (!res.ok) throw new Error((mapping_document as any).detail ?? `Server error ${res.status}`);
      setPendingMappingDocument({ suggestion: snapshot, mapping_document });
      setMappingDocumentConfirmed(false);
      onSwitchTab?.('mapping');
      addLog(`Implementation plan imported — ${file.name} · ${mapping_document.rows?.length ?? '?'} rows restored`);
    } catch (err: any) {
      addLog(`Implementation plan import failed: ${err.message ?? 'unknown'}`, 'error');
    } finally {
      setGenerating(false);
    }
  };

  const stageBpmnFile = async (file: File) => {
    setStagingError('');
    addLog(`Staging BPMN: ${file.name}…`);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/bpmn/import', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Server error ${res.status}`);
      setStagedBpmn({ fileName: file.name, result: data });
      setProject({ ...project, source_bpmn_filename: file.name });
      addLog(`✓ Staged BPMN (${file.name}) — ${data.mapping_document?.rows?.length ?? '?'} tasks. Not generated yet — click Generate below.`);
    } catch (err: any) {
      setStagingError(`BPMN staging failed: ${err.message ?? 'unknown'}`);
      addLog(`BPMN staging failed: ${err.message ?? 'unknown'}`, 'error');
    }
  };

  const stageEvalsFile = async (file: File) => {
    setStagingError('');
    addLog(`Staging eval plan: ${file.name}…`);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/evals/import', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Server error ${res.status}`);
      setStagedEvals({ fileName: file.name, result: data });
      setProject({
        ...project,
        source_evals_filename: file.name,
        source_evals_case_count: data.total ?? null,
        source_evals_rows: data.rows ?? [],
      });
      addLog(`✓ Staged eval plan (${file.name}) — ${data.total} test cases across ${Object.keys(data.counts ?? {}).length} ` +
        `categories. Generate Scaffold will add one test stub per case under tests/evals/.`);
    } catch (err: any) {
      setStagingError(`Eval plan staging failed: ${err.message ?? 'unknown'}`);
      addLog(`Eval plan staging failed: ${err.message ?? 'unknown'}`, 'error');
    }
  };

  const stageBlueprintFile = async (file: File) => {
    setStagingError('');
    addLog(`Staging blueprint: ${file.name}…`);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/blueprint/import', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Server error ${res.status}`);
      setStagedBlueprint({ fileName: file.name, result: data });
      setProject({ ...project, source_spec_filename: file.name });
      const c = data.counts;
      addLog(`✓ Staged blueprint (${file.name}) — ${c.agents} agents, ${c.tools} tools, ${c.behavioral} behavioral rules, ${c.observability} observability signals. Not generated yet — click Generate below.`);
    } catch (err: any) {
      setStagingError(`Blueprint staging failed: ${err.message ?? 'unknown'}`);
      addLog(`Blueprint staging failed: ${err.message ?? 'unknown'}`, 'error');
    }
  };

  const stageGenericSpecFile = async (file: File) => {
    setSpecBusy(true); setSpecError(''); setStagingError('');
    addLog(`Staging spec doc: ${file.name}…`);
    const fd = new FormData();
    fd.append('file', file);
    if (llmConfig?.endpoint?.trim()) {
      fd.append('llm_config', JSON.stringify(llmConfig));
      addLog(`Spec import — using LLM (${llmConfig.endpoint})…`);
      setLlmActive(true);
    } else {
      addLog('Spec import — rule-based (no LLM configured)');
    }
    try {
      const res = await fetch('/api/spec/import', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Server error ${res.status}`);
      // Intake fields (name/domain/description) are safe to apply immediately
      // — that's pre-filling a form, not generating a canvas.
      setProject({ ...project, ...(data.intake ?? {}), source_spec_filename: file.name });
      setSpecImported(true);
      setSpecFileName(file.name);
      // Stage the suggestion itself instead of building the canvas now — a
      // generic (non-EAEF) spec doc reuses the blueprint slot since it plays
      // the same role in the staged set (one governance/context input, held
      // until Generate).
      setStagedBlueprint({
        fileName: file.name,
        result: { suggestion: data.suggestion, source: data.source ?? 'spec', counts: null, process_name: data.intake?.project_name },
      });
      const sc = data.scoring;
      if (sc) {
        const w = sc[sc.winner];
        const l = sc.winner === 'llm' ? sc.rule_based : sc.llm;
        const wLabel = sc.winner === 'llm' ? 'LLM' : 'Rule-based';
        const lLabel = sc.winner === 'llm' ? 'Rule-based' : 'LLM';
        setGenResult({ winner: wLabel, winnerScore: w?.score, winnerAgents: w?.agent_count, winnerSquads: w?.squad_count });
        addLog(`✓ ${wLabel} selected (score: ${w?.score}) — ${w?.agent_count} agents, ${w?.squad_count} squads — staged, not generated yet`);
        addLog(`  ${lLabel} score: ${l?.score} (${l?.agent_count} agents) — not selected`);
      } else {
        addLog(`✓ Staged spec doc (${file.name}) · ${(data.suggestion?.agents ?? []).length} agents. Not generated yet — click Generate below.`);
      }
    } catch (err: any) {
      setSpecError(`Failed — ${err.message ?? 'unknown'}`);
      addLog(`Spec import failed: ${err.message ?? 'unknown'}`, 'error');
    } finally {
      setLlmActive(false);
      setSpecBusy(false);
    }
  };

  const stageFile = async (file: File) => {
    setStagingError('');
    let text = '';
    try { text = await file.text(); } catch { /* binary file, fall through to rejection */ }

    const implPlan = looksLikeImplementationPlanText(text);
    if (implPlan) { await restoreImplementationPlan(file, implPlan); return; }
    if (looksLikeBpmnText(text)) { await stageBpmnFile(file); return; }
    if (looksLikeEvalsText(text)) { await stageEvalsFile(file); return; }
    if (looksLikeBlueprintText(text)) { await stageBlueprintFile(file); return; }
    if (/\.(md|txt)$/i.test(file.name)) { await stageGenericSpecFile(file); return; }

    setStagingError(
      `"${file.name}" doesn't look like a BPMN, a process spec or blueprint (.md/.txt/.html), or an Implementation Plan — nothing staged.`
    );
    addLog(`Rejected unrecognized file: ${file.name}`, 'error');
  };

  // Once a mapping document already exists, clicking Generate again would
  // silently overwrite it (and reset mappingDocumentConfirmed) — discarding
  // any edits made in the Traceability tab with zero warning. Ravi: "after
  // I make changes to the table, accidentally if I click generate it could
  // reset it." Disabled until Clear (clearProject) resets
  // pendingMappingDocument to null, which naturally re-enables this.
  const alreadyGenerated = Boolean(pendingMappingDocument);
  const canGenerate = Boolean(stagedBpmn || stagedBlueprint) && !alreadyGenerated;

  // Ravi: "if it fails, the button generate turns RED with title 'Document
  // pre-checks failed' / Guardian rejected etc." — surfaces the most recent
  // failed gate directly on the Generate button itself, not just on the
  // tile it happened in.
  const failedEntry = (Object.entries(checkState) as [IntakeSlot, { status: string; step: CheckStep; message?: string } | undefined][])
    .find(([, s]) => s?.status === 'failed');
  const failedTitle = failedEntry
    ? failedEntry[1]!.step === 'guardian'
      ? `Guardian rejected — ${failedEntry[1]!.message ?? 'unsafe content detected'}`
      : 'Document pre-checks failed'
    : null;

  // Purely cosmetic staging — the actual work below is rule-based and near-
  // instant, which read as suspiciously fast/fake for what looks like a
  // heavyweight operation (Ravi: "you are way too fast"). A minimum
  // perceived duration makes it read as real work without slowing anything
  // down when the real request happens to take longer than this.
  // Ravi: "it would be nice to show a bar like Generating.... square box
  // like a amp vol.... and then within 15secs full. that is more
  // satisfying." — a VU-meter-style segmented bar rather than the old
  // instant 2.1s text-cycle (Ravi: "currently, it is in a flash"). Shared
  // K9Meter component/hook (Ravi: "have similar bar wherever possible...
  // like from traceability to canvas") — climbs on an easing curve while
  // `generating` is true, snapped to 100 the instant the real fetch
  // resolves so a genuinely fast response still finishes promptly instead
  // of a padded fake wait.
  const [genProgress, setGenProgress] = useClimbingProgress(generating);
  const genStageLabel =
    genProgress < 30 ? 'Analyzing…' : genProgress < 65 ? 'Processing…' : genProgress < 99 ? 'Generating…' : 'Done!';

  const handleGenerate = async () => {
    if (!canGenerate || generating) return;
    setGenerating(true);

    // Ravi: "upload docs, click generate, no delay no instant traceability
    // page" — onSwitchTab used to fire from inside doWork(), the instant
    // the real work finished. Since IntakePanel (which renders the K9Meter)
    // only renders while centerTab === 'intake', switching tabs immediately
    // unmounted it before the meter's climb — or even its 100%-settle step
    // — was ever visible. doWork() now just returns which tab to switch to;
    // the actual switch happens after the settle delay, once the meter has
    // had its moment on screen.
    const doWork = async (): Promise<'mapping' | 'canvas' | null> => {
      if (stagedBpmn && stagedBlueprint) {
        const res = await fetch('/api/intake/combine', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_name: project.project_name || stagedBpmn.result.process_name,
            bpmn_parsed: stagedBpmn.result.suggestion,
            blueprint_parsed: stagedBlueprint.result.parsed,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail ?? `Server error ${res.status}`);
        // Ravi: "so, we do not yet have MCP" — the blueprint's §3.4 MCP Tool
        // Engineering Plan data now flows in data.suggestion.mcp_tools (was
        // silently dropped in blueprint_service.py before); persisted onto
        // `project` directly here since it has no canvas-node
        // representation (mirrors how source_evals_rows is carried).
        setProject({
          ...project,
          project_name: project.project_name || stagedBpmn.result.process_name,
          mcp_tools: data.suggestion?.mcp_tools ?? [],
          // Ravi: "I had input all 3 files" but docs/main.html's hero
          // still showed no Target Outcome/Process Reference — same
          // "found the drop, fixed the drop" bug as mcp_tools above:
          // combine()'s response carries suggestion.header_meta (blueprint's
          // own title/subtitle/Target Outcome/Process Reference/atomic-step
          // stats), but this merge never copied it onto `project`, so
          // _gen_main_html always saw an empty header_meta whenever BPMN +
          // blueprint were combined (the real, common Intake path).
          header_meta: data.suggestion?.header_meta ?? {},
        });
        setPendingMappingDocument({ suggestion: data.suggestion, mapping_document: data.mapping_document });
        setMappingDocumentConfirmed(false);
        setCanvasIsRuleBased(true);
        (data.warnings ?? []).forEach((w: string) => addLog(`⚠ Reconciliation: ${w}`, 'warn'));
        addLog(`✓ Generated from BPMN + blueprint · ${data.mapping_document?.rows?.length ?? '?'} rows` +
          (data.warnings?.length ? ` · ${data.warnings.length} reconciliation warning(s) — see above` : ' · fully reconciled, no warnings'));
        return 'mapping';
      } else if (stagedBpmn) {
        const data = stagedBpmn.result;
        if (data.process_name && !project.project_name) setProject({ ...project, project_name: data.process_name });
        setPendingMappingDocument({ suggestion: data.suggestion, mapping_document: data.mapping_document });
        setMappingDocumentConfirmed(false);
        setCanvasIsRuleBased(true);
        addLog(`✓ Generated from BPMN — structural only, no blueprint staged: no tools, observability, ` +
          `or behavioral guardrails generated · ${data.mapping_document?.rows?.length ?? '?'} rows`);
        return 'mapping';
      } else if (stagedBlueprint) {
        const data = stagedBlueprint.result;
        setProject({
          ...project,
          project_name: project.project_name || data.process_name,
          mcp_tools: data.suggestion?.mcp_tools ?? [],
          header_meta: data.suggestion?.header_meta ?? {},
        });
        addLog(`✓ Generated from ${data.source === 'blueprint' ? 'blueprint' : 'spec doc'} · ` +
          `${data.mapping_document?.rows?.length ?? (data.suggestion?.agents ?? []).length} rows`);
        if (data.mapping_document) {
          setPendingMappingDocument({ suggestion: data.suggestion, mapping_document: data.mapping_document });
          setMappingDocumentConfirmed(false);
          setCanvasIsRuleBased(true);
          return 'mapping';
        } else {
          // Generic (non-EAEF) spec doc — no mapping document (that gate is
          // for structured BPMN/blueprint input only), same as before.
          setPendingCanvasSuggestion(data.suggestion);
          return 'canvas';
        }
      }
      return null;
    };

    // Ravi: "i loved the generate scaffold from traceability... the bars
    // at the bottom was very nice this time. a bit slow is nicer to
    // admire." That one already waits out a fixed minimum before doing its
    // (near-instant) work; Generate's real /api/intake/combine call was
    // fast enough that snapping to 100% the moment it resolved cut the
    // climb short regardless of how slow the per-tick rate was. Matching
    // that same minimum here — ~12.5s, enough for the climb to reach CAP
    // (94 / 1.5-per-tick / 200ms ticks) — so the full square-by-square
    // sequence plays out regardless of how fast the backend actually is.
    const MIN_DISPLAY_MS = 12500;
    try {
      const [targetTab] = await Promise.all([
        doWork(),
        new Promise((r) => setTimeout(r, MIN_DISPLAY_MS)),
      ]);
      setGenProgress(100);
      await new Promise((r) => setTimeout(r, 400)); // let the meter read "full" briefly
      if (targetTab) onSwitchTab?.(targetTab);
    } catch (err: any) {
      addLog(`Generate failed: ${err.message ?? 'unknown'}`, 'error');
    } finally {
      setGenerating(false);
    }
  };

  const set = (key: string, value: string) =>
    setProject({ ...project, [key]: value });

  const wifFilename = () => {
    const slugify = (s: string) => s.toLowerCase().trim().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    const proj = slugify(project.project_name || 'project');
    const app  = slugify((project as any).app_name || '');
    return app ? `${proj}_${app}_intake.md` : `${proj}_intake.md`;
  };

  const buildWIFContent = () => {
    const today = new Date().toISOString().split('T')[0];
    const s = (label: string, val: string) => val.trim() ? `\n## ${label}\n\n${val.trim()}\n` : '';
    return `# Work Intake Form — ${project.project_name || 'Untitled'}

**Date:** ${today}
**Author:** ${project.author || '—'}
**Application:** ${(project as any).app_name || '—'}
**Domain:** ${project.domain || '—'}
**Description:** ${project.description || '—'}
${s('Business Vision', (project as any).vision ?? '')}${s('Current State', (project as any).current_state ?? '')}${s('Pain Points', (project as any).pain_points ?? '')}${s('Target Goals', (project as any).target_goals ?? '')}${s('Notes', (project as any).notes ?? '')}
---
*Generated by K9X Studio*`.trim();
  };

  const handleGenerateWIF = async () => {
    setWifBusy(true);
    addLog(`Generating ${wifFilename()}…`);
    const content = buildWIFContent();

    addGeneratedDoc(wifFilename(), content);
    addLog('✓ initial_project_WIF.md generated — see Generated Docs tab');
    onSwitchTab?.('docs');

    if (project.project_folder) {
      try {
        const res = await fetch('/api/save-wif', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_folder: project.project_folder,
            project_name: project.project_name,
            author: project.author,
            domain: project.domain,
            description: project.description,
            vision: (project as any).vision ?? '',
            current_state: (project as any).current_state ?? '',
            target_goals: (project as any).target_goals ?? '',
            notes: (project as any).notes ?? '',
          }),
        });
        const data = await res.json();
        if (res.ok) addLog(`✓ Saved to disk → ${data.path}`);
      } catch { /* disk save optional */ }
    }
    setWifBusy(false);
  };


  return (
    <div className="intake-panel">
      <div className="intake-header">
        <div className="intake-title">Project Intake</div>
        <div className="intake-sub">Define your business context — the foundation for architecture generation</div>
        <button
          className="intake-clear-btn"
          onClick={() => {
            clearProject();
            addLog('Intake cleared — ready for new project');
          }}
          title="Clear all fields and start over"
        >✕ Clear</button>
      </div>

      {/* Ravi: "if I again go back clicking on Intake, I expect that it says
          current process is based on already input BPMN file <name> ...
          something the user can know." canvasIsRuleBased + project_name are
          both persisted, so this survives a refresh unlike the File object
          itself (see canvasIsRuleBased's own comment in store.ts). */}
      {canvasIsRuleBased && nodes.length > 0 && (
        <div className="intake-source-banner">
          <span>
            ✨ Current process is based on an imported BPMN file
            {project.project_name ? <> — <strong>{project.project_name}</strong></> : null}.
          </span>
          <button className="intake-source-banner-clear" onClick={() => { clearProject(); addLog('Intake cleared — ready for new project'); }}>
            Clear
          </button>
        </div>
      )}

      <div className="intake-form">

        {/* Ravi: "intake screen has to be much nicer, like Grok's
            suggestion" — numbered, icon-led cards instead of a flat list of
            upload rows. Each tile stages a file (content detects its role,
            not the tile clicked) — none of them generate on their own; only
            the Generate button in card 2 does, and only once every staged
            file has cleared both gates below. */}
        <div className="intake-numbered-card">
          <div className="intake-numbered-card-header">
            <div className="intake-numbered-card-icon"><Icon kind="package" size={16} /></div>
            <div>
              <div className="intake-numbered-card-title">1. Import Sources</div>
              <div className="intake-numbered-card-subtitle">BPMN, process specification and agent evaluation plan</div>
            </div>
          </div>

          <div className="intake-import-grid">
            <div className="intake-import-tile">
              <div className="intake-import-tile-icon" style={{ background: 'rgba(251,146,60,0.12)', color: '#fb923c' }}>
                <Icon kind="flow" size={16} />
              </div>
              <div className="intake-import-tile-title">BPMN Diagram</div>
              <div className="intake-import-tile-hint">Any BPMN 2.0 tool — Camunda, Bizagi, Blueworks Live, Process Studio (.bpmn, .xml, .zip)</div>
              <label
                className={`intake-upload-btn intake-upload-btn--bpmn${alreadyGenerated ? ' intake-upload-btn--disabled' : ''}`}
                style={{ width: '100%', justifyContent: 'center' }}
                title={alreadyGenerated ? 'Already generated — Clear above to start over before staging a different file.' : "Stages, doesn't generate."}
              >
                <span>⬆ Upload BPMN</span>
                <input
                  type="file"
                  accept=".bpmn,.xml,.zip"
                  style={{ display: 'none' }}
                  disabled={alreadyGenerated}
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    e.target.value = '';
                    if (file) await gatedStage('bpmn', file, stageBpmnFile);
                  }}
                />
              </label>
              <TileCheckBadge slot="bpmn" />
            </div>

            <div className="intake-import-tile">
              <div className="intake-import-tile-icon" style={{ background: 'rgba(52,211,153,0.12)', color: '#34d399' }}>
                <Icon kind="document" size={16} />
              </div>
              <div className="intake-import-tile-title">Process Specification</div>
              <div className="intake-import-tile-hint">
                Process spec or blueprint (.md/.txt/.html) — <code>.docx</code>/<code>.pdf</code> not yet supported
              </div>
              <label
                className={`intake-upload-btn intake-upload-btn--spec${specBusy ? ' intake-upload-btn--busy' : ''}${alreadyGenerated ? ' intake-upload-btn--disabled' : ''}`}
                style={{ width: '100%', justifyContent: 'center' }}
                title={alreadyGenerated ? 'Already generated — Clear above to start over before staging a different file.' : "Stages, doesn't generate."}
              >
                <span>{specBusy ? '⟳ Staging…' : '⬆ Upload Spec (.md)'}</span>
                <input
                  type="file"
                  accept=".md,.txt,.html,.htm"
                  style={{ display: 'none' }}
                  disabled={specBusy || alreadyGenerated}
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    e.target.value = '';
                    if (file) await gatedStage('spec', file, stageFile);
                  }}
                />
              </label>
              <TileCheckBadge slot="spec" />
            </div>

            <div className="intake-import-tile">
              <div className="intake-import-tile-icon" style={{ background: 'rgba(167,139,250,0.12)', color: '#a78bfa' }}>
                <Icon kind="checklist" size={16} />
              </div>
              <div className="intake-import-tile-title">Agent Evaluation Plan</div>
              <div className="intake-import-tile-hint">Functional/Behavioral/Adversarial test cases (.md) — generates one test stub per case under tests/evals/</div>
              <label
                className={`intake-upload-btn intake-upload-btn--evals${alreadyGenerated ? ' intake-upload-btn--disabled' : ''}`}
                style={{ width: '100%', justifyContent: 'center' }}
                title={alreadyGenerated ? 'Already generated — Clear above to start over before staging a different file.' : "Stages, doesn't generate."}
              >
                <span>⬆ Upload Evals (.md)</span>
                <input
                  type="file"
                  accept=".md"
                  style={{ display: 'none' }}
                  disabled={alreadyGenerated}
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    e.target.value = '';
                    if (file) await gatedStage('evals', file, stageEvalsFile);
                  }}
                />
              </label>
              <TileCheckBadge slot="evals" />
            </div>
          </div>

          {/* IBM Process Studio-specific inputs, grouped and collapsible so the
              generic tiles above stay the main path. BPMN, spec/blueprint and
              eval-plan files from Process Studio already work in the tiles
              above (content-detected); only the Enterprise App Kit is
              Process Studio-specific. */}
          <ProcessStudioGroup>
            <div className="intake-kit-bar" aria-disabled="true">
              <div className="intake-kit-bar-label">Enterprise Integration Kit</div>
              <div className="intake-kit-bar-icon"><Icon kind="package" size={14} /></div>
              <div className="intake-kit-bar-text">
                <span className="intake-kit-bar-title">Have the Enterprise App Kit for this project?</span>
                <span className="intake-kit-bar-hint">
                  Upload <code>process-studio-enterprise-app-kit.zip</code> instead of the files above — it already
                  carries the blueprint, scope and integration decisions.
                </span>
              </div>
              <span className="intake-kit-bar-badge">Coming soon</span>
              <button
                type="button"
                className="intake-upload-btn intake-upload-btn--kit intake-upload-btn--disabled"
                disabled
                aria-label="Upload Enterprise App Kit (.zip) — coming soon"
              >
                <span>⬆ Upload App Kit (.zip)</span>
              </button>
            </div>
          </ProcessStudioGroup>

          <ImportPipeline />

          {stagingError && (
            <div style={{ fontSize: 11, color: '#f87171', marginTop: 12 }}>✕ {stagingError}</div>
          )}
        </div>

        {/* Ravi: "where is our old beautiful Generate button and progress
            bar?" — this card used to disappear entirely until something
            was staged, which read as the button having vanished rather
            than "not active yet". Always rendered now; the button itself
            is what's disabled/active/failed/generating, matching "Generate
            will now become Active. until then inactive" — inactive, not
            invisible. */}
        <div className="intake-numbered-card">
          <div className="intake-numbered-card-header" style={{ marginBottom: 12 }}>
            <div className="intake-numbered-card-icon">✨</div>
            {/* Ravi: "redundant. the title Generation Status do we need to
                say that? below already would activate the button when
                governance passes." — dropped the separate green/grey
                status bar entirely; the Generate button's own color,
                label, and title now carry all of that state. */}
            <div className="intake-numbered-card-title">2. Generate</div>
          </div>

          {/* Ravi: "too tall. I would make it nice and lean. 2. Generate
              <the generate bar here> thats it" — dropped the idle hint
              line and the extra wrapping box; the button's own title
              tooltip already explains why it's inactive. */}
          <div>
              {(stagedBpmn || stagedBlueprint || stagedEvals) && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                {stagedBpmn && (
                  <span className="intake-staged-chip">
                    BPMN: {stagedBpmn.result.mapping_document?.rows?.length ?? '?'} tasks
                    ({stagedBpmn.fileName})
                    <button onClick={() => setStagedBpmn(null)} title="Remove staged BPMN">✕</button>
                  </span>
                )}
                {stagedBlueprint && (
                  <span className="intake-staged-chip">
                    {stagedBlueprint.result.counts
                      ? `Blueprint: ${stagedBlueprint.result.counts.agents} agents, ${stagedBlueprint.result.counts.tools} tools, ` +
                        `${stagedBlueprint.result.counts.behavioral} behavioral rules, ${stagedBlueprint.result.counts.observability} observability signals`
                      : `Spec doc: ${(stagedBlueprint.result.suggestion?.agents ?? []).length} agents`}
                    {' '}({stagedBlueprint.fileName})
                    <button onClick={() => setStagedBlueprint(null)} title="Remove staged spec/blueprint">✕</button>
                  </span>
                )}
                {stagedEvals && (
                  <span className="intake-staged-chip">
                    Evals: {stagedEvals.result.total} test cases
                    {' '}({stagedEvals.fileName}) — will generate tests/evals/*.py
                    <button onClick={() => setStagedEvals(null)} title="Remove staged eval plan">✕</button>
                  </span>
                )}
              </div>
              )}
              {stagedBpmn && !stagedBlueprint && (
                <div className="intake-staged-warning">
                  ⚠ No blueprint staged — scaffold will be structural only; no tools, observability, or
                  behavioral guardrails generated. Stage a blueprint spec too for the full governance layer.
                </div>
              )}
              <button
                className={`intake-btn-generate-primary${!canGenerate && failedTitle ? ' intake-btn-generate-primary--failed' : ''}`}
                onClick={handleGenerate}
                disabled={!canGenerate || generating}
                title={
                  alreadyGenerated
                    ? 'Already generated — edit on the Traceability tab, or Clear above to start over. Disabled so a stray click here can\'t silently discard your edits.'
                    : canGenerate ? 'Build the canvas/traceability matrix from the staged input(s)'
                    : failedTitle ?? 'Stage a BPMN or blueprint first — Generate stays inactive until pre-checks + Guardian clear.'
                }
              >
                {generating ? '⟳ Generating…' : alreadyGenerated ? '✓ Generated' : !canGenerate && failedTitle ? '✕ Generate' : '✦ Generate'}
              </button>
              {generating && <K9Meter progress={genProgress} label={genStageLabel} />}
            </div>
          </div>

        {/* Ravi: "resume previous proposal... should be on its own box.
            not combined with the top one." then "the resume can go bottom
            to Generate" — its own numbered-card, ordered after Generate
            rather than between Import Sources and Generate.
            Ravi: "i clicked on it and it expanded but cannot collapse
            back. why?" — same bug as Manual Entry below: the toggle only
            existed in the collapsed branch, so it vanished once expanded.
            Same fix — a persistent header that always toggles, content
            collapses beneath it. */}
        <div className="intake-numbered-card">
          <button className="intake-manual-entry-toggle" onClick={() => setShowResume((v) => !v)}>
            <span className="intake-manual-entry-toggle-chevron">{showResume ? '▾' : '▸'}</span>
            <span>↻ Resume a Previous Project</span>
          </button>
          {showResume && (
            <div className="intake-import-resume" style={{ paddingTop: 14, marginTop: 14 }}>
              <div className="intake-import-resume-text">
                <span className="intake-import-resume-hint">A previously downloaded implementation-plan.md — restores immediately, not staged</span>
              </div>
              <label
                className={`intake-upload-btn intake-upload-btn--resume${nodes.length > 0 ? ' intake-upload-btn--disabled' : ''}`}
                title={nodes.length > 0 ? 'Clear above to discard the current project before importing a different one — this restores immediately, with no confirmation.' : 'Restores immediately, not staged.'}
              >
                <span>⬆ Import Implementation Plan</span>
                <input
                  type="file"
                  accept=".md"
                  style={{ display: 'none' }}
                  disabled={nodes.length > 0}
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    e.target.value = '';
                    if (file) await stageFile(file);
                  }}
                />
              </label>
            </div>
          )}
        </div>

        <div>
          {specBusy && (
            <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
              Processing document — LLM analysing, please wait…
            </div>
          )}
          {specFileName && !specError && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
              <div style={{
                fontSize: 11, color: '#34d399',
                background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.25)',
                borderRadius: 4, padding: '3px 8px',
              }}>
                ✓ {specFileName}
              </div>
            </div>
          )}
          {specError && (
            <div style={{ fontSize: 11, color: '#f87171', marginTop: 4 }}>
              ✕ {specError} — check Activity Log
            </div>
          )}
        </div>

        {/* Ravi: "basic info, business context and all that not needed for
            this version of studio right? ... entire thing can be in a
            table and collapsed or in fact even removed. do we even need
            this? since this is mainly for process studio." Manual-entry
            fields (Basic Info through Governance) and the two LLM-suggest
            buttons below only matter for a from-scratch project with no
            uploaded document — not the primary Process Studio flow this
            fork exists to demo. Nothing removed (the capability still
            works if opened), just collapsed by default so it doesn't
            compete with the upload cards above.
            Ravi: "I uncollapsed it and cannot see a way to collapse again
            because it disappeared" — the toggle itself must stay visible
            in both states, not vanish once expanded; it now lives in its
            own persistent card header, bigger/clearer per "that manual
            input can be bigger and visible with the icon to collapse and
            expand", with only the CONTENT below it collapsing. */}
        <div className="intake-numbered-card">
          <button className="intake-manual-entry-toggle" onClick={() => setShowManualEntry((v) => !v)}>
            <span className="intake-manual-entry-toggle-chevron">{showManualEntry ? '▾' : '▸'}</span>
            <span>Manual Entry — no document to upload? Fill in project details by hand</span>
          </button>
          {showManualEntry && (
            <div style={{ marginTop: 16 }}>
        <Section title="Basic Info">
          <div className="intake-field">
            <label className="intake-label">Industry Blueprint</label>
            <select className="intake-input" disabled>
              <option value="">— select a blueprint (coming soon) —</option>
            </select>
          </div>
          <div className="intake-row-2">
            <div className="intake-field">
              <label className="intake-label">Project Name <span style={{ color: '#f87171', marginLeft: 2 }}>*</span></label>
              <input className="intake-input" placeholder="e.g. Insurance Transformation 2026" value={project.project_name} onChange={(e) => set('project_name', e.target.value)} />
            </div>
            <div className="intake-field">
              <label className="intake-label">Application Name</label>
              <input className="intake-input" placeholder="e.g. Enterprise Claims Processor" value={(project as any).app_name ?? ''} onChange={(e) => set('app_name', e.target.value)} />
            </div>
          </div>
          <div className="intake-row-2">
            <div className="intake-field">
              <label className="intake-label">Domain</label>
              <input className="intake-input" placeholder="e.g. Insurance / Banking / Healthcare" value={project.domain} onChange={(e) => set('domain', e.target.value)} />
            </div>
            <div className="intake-field">
              <label className="intake-label">Author</label>
              <input className="intake-input" placeholder="Your name" value={project.author} onChange={(e) => set('author', e.target.value)} />
            </div>
          </div>
          <div className="intake-field">
            <label className="intake-label">Description <span style={{ color: '#94a3b8', fontSize: 9, marginLeft: 2 }}>* at least one context field required</span></label>
            <textarea className="intake-textarea" placeholder="Describe the application — what it does, who uses it, and the business context" value={project.description} onChange={(e) => set('description', e.target.value)} rows={3} />
          </div>
        </Section>

        {/* ── Section 2: Business Context ── */}
        <Section title="Business Context">
          <div className="intake-field">
            <label className="intake-label">Business Vision</label>
            <textarea className="intake-textarea" placeholder="What is the desired end-state? What business problem does this solve?" value={(project as any).vision ?? ''} onChange={(e) => set('vision', e.target.value)} rows={3} />
          </div>
          <div className="intake-field">
            <label className="intake-label">Current State</label>
            <textarea className="intake-textarea" placeholder="Describe the current process, pain points, and limitations" value={(project as any).current_state ?? ''} onChange={(e) => set('current_state', e.target.value)} rows={3} />
          </div>
          <div className="intake-field">
            <label className="intake-label">Pain Points</label>
            <textarea className="intake-textarea" placeholder="Key pain points, blockers, and frustrations with the current state" value={(project as any).pain_points ?? ''} onChange={(e) => set('pain_points', e.target.value)} rows={2} />
          </div>
          <div className="intake-field">
            <label className="intake-label">Target Goals</label>
            <textarea className="intake-textarea" placeholder="Key objectives, KPIs, and success metrics" value={(project as any).target_goals ?? ''} onChange={(e) => set('target_goals', e.target.value)} rows={3} />
          </div>
          <div className="intake-field">
            <label className="intake-label">Notes</label>
            <textarea className="intake-textarea" placeholder="Additional context, stakeholders, constraints, preferred models…" value={(project as any).notes ?? ''} onChange={(e) => set('notes', e.target.value)} rows={2} />
          </div>
        </Section>

        {/* ── Section 3: Key Processes (enriches LLM) ── */}
        <Section title="Key Processes — optional, enriches LLM generation">
          <div className="intake-field">
            <label className="intake-label">Main Workflows</label>
            <textarea className="intake-textarea" placeholder="List 3-5 main business workflows (one per line)&#10;e.g. Claim Intake&#10;Fraud Detection&#10;Payment Processing" value={(project as any).key_processes ?? ''} onChange={(e) => set('key_processes', e.target.value)} rows={4} />
          </div>
          <div className="intake-field">
            <label className="intake-label">Volume & SLA</label>
            <input className="intake-input" placeholder="e.g. 1000 events/day, response < 2s" value={(project as any).volume_sla ?? ''} onChange={(e) => set('volume_sla', e.target.value)} />
          </div>
        </Section>

        {/* ── Section 4: Systems & Integration ── */}
        <Section title="Systems & Integration — optional, enriches LLM generation">
          <div className="intake-field">
            <label className="intake-label">Systems of Record</label>
            <textarea className="intake-textarea" placeholder="e.g. Salesforce CRM, SAP ERP, IBM FileNet, Oracle Financials" value={(project as any).systems_of_record ?? ''} onChange={(e) => set('systems_of_record', e.target.value)} rows={2} />
          </div>
          <div className="intake-field">
            <label className="intake-label">Integration Patterns</label>
            <input className="intake-input" placeholder="e.g. REST APIs, Apache Kafka, Batch, IBM MQ" value={(project as any).integration_patterns ?? ''} onChange={(e) => set('integration_patterns', e.target.value)} />
          </div>
        </Section>

        {/* ── Section 5: Governance ── */}
        <Section title="Governance & Compliance — optional, enriches LLM generation">
          <div className="intake-field">
            <label className="intake-label">Compliance Requirements</label>
            <input className="intake-input" placeholder="e.g. HIPAA, GDPR, SOX, PCI-DSS" value={(project as any).compliance_requirements ?? ''} onChange={(e) => set('compliance_requirements', e.target.value)} />
          </div>
          <div className="intake-field">
            <label className="intake-label">Human-in-the-Loop Decisions</label>
            <textarea className="intake-textarea" placeholder="Which decisions require human approval? e.g. Payments > $50K, Fraud escalations, Coverage denials" value={(project as any).hitl_decisions ?? ''} onChange={(e) => set('hitl_decisions', e.target.value)} rows={2} />
          </div>
        </Section>


        <div className="intake-actions">
          {nodes.length === 0 && (
            <button
              className="intake-btn-flow"
              onClick={async () => {
                const hasContext = project.description.trim() || (project as any).vision?.trim() || (project as any).current_state?.trim() || (project as any).pain_points?.trim() || (project as any).target_goals?.trim();
                if (generating || !hasContext) return;
                setGenerating(true);
                const usingLlm = Boolean(llmConfig?.endpoint?.trim());
                addLog(usingLlm ? `Generating flow via LLM…` : 'Generating flow (rule-based)…');
                if (usingLlm) setLlmActive(true);
                try {
                  const payload: any = { ...project };
                  if (usingLlm) payload.llm = llmConfig;
                  const res = await fetch('/api/suggest', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                  });
                  const data = await res.json();
                  if (data.suggestion) {
                    setLastTemplateId(null);
                    setPendingCanvasSuggestion(data.suggestion);
                    onSwitchTab?.('canvas');
                    addLog(`Flow generated · source: ${data.source ?? 'default'}`);
                  }
                } catch (err: any) {
                  addLog(`Flow generation failed: ${err.message ?? 'unknown'}`, 'error');
                } finally {
                  setGenerating(false);
                  setLlmActive(false);
                }
              }}
              disabled={generating || !project.project_name.trim() || (!project.description.trim() && !(project as any).vision?.trim() && !(project as any).current_state?.trim() && !(project as any).pain_points?.trim() && !(project as any).target_goals?.trim())}
              title="Generate architecture flow on canvas"
            >
              {generating ? '⟳ Generating…' : '✦ Generate Flow'}
            </button>
          )}
          <button
            className="intake-btn-generate"
            onClick={handleGenerateWIF}
            disabled={wifBusy || !project.project_name.trim() || specImported}
            title={specImported ? 'Spec document already uploaded — WIF not needed' : !project.project_name.trim() ? 'Enter a project name first' : 'Generate Work Intake Form'}
          >
            {wifBusy ? '⟳ Generating…' : `Generate ${wifFilename()}`}
          </button>
        </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
