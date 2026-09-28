import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { useStore } from '../store';
import { K9Meter, useClimbingProgress } from './K9Meter';

// Process -> Implementation Traceability Matrix, reviewed/editable before
// anything is built. Mapping-document-first gate (see plan.md): this panel
// is a checkpoint, not just a display — canvas generation only proceeds via
// the Confirm button here, never automatically on import.

const ZONE_COLORS: Record<string, string> = { GREEN: '#24a148', AMBER: '#f1c21b', RED: '#da1e28' };
const ZONE_OPTIONS = ['GREEN', 'AMBER', 'RED'];
// Agent Base Type is deliberately NOT independently editable — see the
// zone-change handler below. Ravi: "why would the SA change it? what if
// they wrongly check BaseAgent, not knowing [what that removes]?" A free
// dropdown here let Zone=RED (dual-approval, cannot-override per the
// source blueprint) coexist with Base Type=BaseAgent (no oversight loop at
// all) — an inconsistent, dangerous combination nothing prevented. Same
// mapping bpmn_service.py's _ZONE_TO_AGENT_TYPE uses server-side, kept in
// sync by hand since this is a small, stable, rarely-changing table, not
// worth a build-time codegen step for three entries.
const ZONE_TO_AGENT_TYPE: Record<string, string> = {
  GREEN: 'BaseAgent', AMBER: 'K9ValidationLoopAgent', RED: 'K9CriticActorAgent',
};

// CSV export/import (Ravi: edit online or offline in a spreadsheet, either
// works — kept simple on purpose: no database, no saved-project model, CSV
// only — see plan.md). Column order here is the contract between export and
// import; keep them in sync.
const CSV_COLUMNS = [
  'process_id', 'process_element', 'zone', 'orchestrator', 'squad', 'component',
  'component_kind', 'agent_base_type', 'governance', 'zero_trust', 'hitl_touchpoint',
] as const;

function csvEscape(value: unknown): string {
  const s = value == null ? '' : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function rowsToCsv(rows: Row[]): string {
  const header = CSV_COLUMNS.join(',');
  const body = rows.map((r) => CSV_COLUMNS.map((c) => csvEscape((r as any)[c])).join(','));
  return [header, ...body].join('\r\n');
}

// Minimal RFC4180-ish parser — handles quoted fields, escaped quotes, and
// commas/newlines inside quotes. Good enough for a matrix a human edited in
// Excel/Numbers/Sheets; not a general-purpose CSV library.
function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let field = '', row: string[] = [], inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else { inQuotes = false; }
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.some((f) => f !== '')) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  if (rows.length === 0) return [];
  const header = rows[0];
  return rows.slice(1).map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ''])));
}

function downloadText(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

interface Row {
  process_id: string | null;
  process_element: string;
  zone: string | null;
  orchestrator: string | null;
  squad: string | null;
  component: string;
  component_kind: 'agent' | 'adapter' | 'hil_orchestrator';
  agent_base_type: string;
  governance: string;
  zero_trust: string | null;
  hitl_touchpoint: string;
}

// Ravi: "I see in the traceability that there is HITL touchpoint. but, on
// the canvas, however, I do not see the HIL orchestration... if possible,
// add to the traceability in there, so one row is added for HIL Orch (but
// the studio should know about the component in left panel)" — same
// component the Palette lists (BaseHILOrchestrator, teal `#14b8a6`) and the
// same one Palette.tsx's buildCanvas() now auto-adds to Canvas under the
// identical AMBER/RED condition, so the matrix and the canvas always agree.
// process_id/zone/orchestrator stay null (this row isn't a BPMN task, it
// has no zone of its own) — every render path below already treats null
// there as "not applicable" for a row, so this needs no special-casing.
const HIL_SYNTHETIC_ROW: Row = {
  process_id: null,
  process_element: 'Human-in-the-Loop checkpoint (synthesized)',
  zone: null,
  orchestrator: null,
  squad: 'HILSquad',
  component: 'HILOrch',
  component_kind: 'hil_orchestrator',
  agent_base_type: 'BaseHILOrchestrator',
  governance: 'Event-driven HIL orchestrator — resumes the workflow after a human decision.',
  zero_trust: null,
  hitl_touchpoint: 'Auto-added: at least one AMBER/RED row above requires human review. Matches the HIL Orchestrator auto-wired onto Canvas.',
};

const thStyle: CSSProperties = {
  textAlign: 'left', padding: '8px 10px', fontSize: 10, fontWeight: 700,
  letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8892a4',
  borderBottom: '1px solid var(--border)', borderRight: '1px solid var(--border)', whiteSpace: 'nowrap',
};
const tdStyle: CSSProperties = {
  padding: '7px 10px', fontSize: 12, color: '#c9cadb', borderBottom: '1px solid var(--border-hover)',
  borderRight: '1px solid var(--border-hover)', verticalAlign: 'top',
};
// HITL text is genuinely long (a full sentence per zone) — word-wrap keeps
// it scannable. Governance/Zero Trust are now short per-row status labels
// (the full explanation is a one-time callout above the table, not
// repeated per row — see the "notes" block below), but share the same
// wrap style for consistent column rendering.
// Generated names like "Agn2ExceptionResolutionAgentOrchestrator" run
// 35-45 chars — 140px clipped them with no truncation cue, just a silently
// cut-off value. Wide enough for the longest generated names to sit unclipped.
const nameInputStyle: CSSProperties = {
  background: 'transparent', border: '1px solid transparent', borderRadius: 4,
  color: '#c9cadb', fontSize: 12, padding: '3px 5px', width: '100%', minWidth: 260,
};
const secondaryBtnStyle: CSSProperties = {
  padding: '7px 13px', fontSize: 12, fontWeight: 600, letterSpacing: '0.2px',
  background: 'rgba(99,102,241,0.08)', border: '1px solid var(--border)', borderRadius: 6,
  color: '#c9cadb', cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
};
// Was truncated with an ellipsis + hover tooltip — Ravi: "people would not
// understand ... can't read the rest." A hover-only affordance isn't
// legible enough for text people need to actually read, not guess at.
// Word-wrap instead, with a wider column so it wraps to a readable few
// lines rather than the original untruncated version's 8-10.
const wrapCellStyle = (width: number): CSSProperties => ({
  ...tdStyle, fontSize: 11, color: '#8892a4', width, minWidth: width,
  whiteSpace: 'normal', wordBreak: 'break-word',
});
// Element is the same long free-text problem as HITL above, but it's
// primary content (not a muted status note) — same word-wrap + fixed-width
// fix, kept at tdStyle's normal size/color instead of wrapCellStyle's dimmer
// secondary-note styling.
const elementCellStyle: CSSProperties = {
  ...tdStyle, width: 340, minWidth: 340, whiteSpace: 'normal', wordBreak: 'break-word',
};

export function MappingDocumentPanel({ onConfirm }: { onConfirm?: () => void }) {
  const { pendingMappingDocument, mappingDocumentConfirmed, setMappingDocumentConfirmed, setPendingCanvasSuggestion, addLog, nodes } = useStore();
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    const baseRows = (pendingMappingDocument?.mapping_document?.rows ?? []) as Row[];
    const needsHil = baseRows.some((r) => ['AMBER', 'RED'].includes(String(r.zone ?? '').toUpperCase()));
    setRows(needsHil ? [...baseRows, HIL_SYNTHETIC_ROW] : baseRows);
  }, [pendingMappingDocument]);

  if (!pendingMappingDocument) {
    // Two different situations that must not look the same: nothing has
    // been generated yet, vs. a canvas already exists but came from a path
    // (manual entry, or a generic non-EAEF spec doc) that never builds a
    // mapping document in the first place — that's not a bug, this feature
    // needs a real process_id to anchor each row to, which only a BPMN
    // diagram or an EAEF blueprint carries.
    const hasCanvasWithoutTraceability = nodes.length > 0;
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 36 }}>
        <div style={{ maxWidth: 480, textAlign: 'center', color: '#5b5b78', fontSize: 13, lineHeight: 1.7 }}>
          {hasCanvasWithoutTraceability ? (
            <>
              This project was built from a manual entry or a generic spec doc, which doesn't carry the
              structured process data (BPMN task IDs, blueprint sections) this matrix needs to anchor to.
              <br /><br />
              Traceability is only available for a project built from a BPMN diagram and/or a structured
              process spec or blueprint — upload one on the Intake tab to enable it.
            </>
          ) : (
            <>
              This tab shows the Process → Implementation Traceability Matrix — built from a BPMN diagram
              and/or a structured process spec or blueprint (for example from IBM Process Studio) uploaded on the Intake tab.
              <br /><br />
              Upload one to see it here.
            </>
          )}
        </div>
      </div>
    );
  }

  const counts = pendingMappingDocument.mapping_document?.counts ?? {};
  // Full Governance/Zero Trust explanation lives once on the document, not
  // once per row — see MEMORY / bpmn_service._GOVERNANCE_SHORT for why.
  const notes: { governance?: string; zero_trust?: string } = pendingMappingDocument.mapping_document?.notes ?? {};

  const updateRow = (idx: number, patch: Partial<Row>) => {
    setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };

  // Ravi: "have similar bar wherever possible... like from traceability to
  // canvas... gives that cool look like it is doing it." The actual rename/
  // rebuild work below is synchronous and near-instant — the delay here is
  // deliberate, purely so the K9Meter has something to visibly climb
  // through. Matched to K9Meter's own climb rate (CAP 94 / STEP 1.5 per
  // 200ms tick ≈ 12.5s) so the full square-by-square sequence plays out —
  // Ravi: "the bars at the bottom was very nice this time. a bit slow is
  // nicer to admire" (praising this screen specifically, before the
  // shared rate was slowed further for Intake's Generate to match).
  const [building, setBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useClimbingProgress(building);
  const CONFIRM_MIN_DISPLAY_MS = 12500;

  const handleConfirm = () => {
    if (building) return;
    setBuilding(true);
    setTimeout(() => {
      doConfirm();
      setBuildProgress(100);
      setTimeout(() => setBuilding(false), 400);
    }, CONFIRM_MIN_DISPLAY_MS);
  };

  const doConfirm = () => {
    // Diff current `rows` against the pristine baseline (matched by
    // process_id — the one thing that never changes, whether the edit came
    // from typing in the table or from an uploaded CSV) to find zone/type
    // edits AND any renames, then apply all of it to a copy of the
    // suggestion before it becomes the canvas source. One code path for
    // both inline edits and CSV import — neither duplicates this logic.
    const suggestion = pendingMappingDocument.suggestion;
    const baseline = (pendingMappingDocument.mapping_document?.rows ?? []) as Row[];
    const baselineById = new Map(baseline.map((r) => [r.process_id, r]));

    const orchRenames = new Map<string, string>();
    const squadRenames = new Map<string, string>();
    const componentRenames = new Map<string, string>();
    const editByComponent = new Map<string, Row>(); // keyed by the CURRENT (possibly renamed) component name

    for (const r of rows) {
      const base = r.process_id != null ? baselineById.get(r.process_id) : undefined;
      if (base) {
        if (base.orchestrator && r.orchestrator && base.orchestrator !== r.orchestrator) orchRenames.set(base.orchestrator, r.orchestrator);
        if (base.squad && r.squad && base.squad !== r.squad) squadRenames.set(base.squad, r.squad);
        if (base.component && r.component && base.component !== r.component) componentRenames.set(base.component, r.component);
      }
      editByComponent.set(r.component, r);
    }
    const renamed = (name: string | null | undefined, map: Map<string, string>) =>
      name != null && map.has(name) ? map.get(name)! : name;

    const editedOrchestrators = (suggestion.orchestrators ?? []).map((o: any) => ({
      ...o,
      name: renamed(o.name, orchRenames),
      squads: (o.squads ?? []).map((s: string) => renamed(s, squadRenames)),
    }));
    const editedSquads = (suggestion.squads ?? []).map((sq: any) => ({
      ...sq,
      name: renamed(sq.name, squadRenames),
      agents: (sq.agents ?? []).map((a: string) => renamed(a, componentRenames)),
    }));
    const editedAgents = (suggestion.agents ?? []).map((a: any) => {
      const newName = renamed(a.name, componentRenames)!;
      const edit = editByComponent.get(newName);
      return { ...a, name: newName, zone: edit?.zone ?? a.zone, type: edit?.agent_base_type ?? a.type };
    });
    const editedAdapters = (suggestion.adapters ?? []).map((ad: any) => ({
      ...ad,
      name: renamed(ad.name, componentRenames),
      orchestrator: renamed(ad.orchestrator, orchRenames),
    }));
    const editedSuggestion = {
      ...suggestion,
      orchestrators: editedOrchestrators,
      squads: editedSquads,
      agents: editedAgents,
      adapters: editedAdapters,
    };

    setPendingCanvasSuggestion(editedSuggestion);
    // Deliberately NOT clearing pendingMappingDocument here — the matrix
    // stays visible in this tab as a record of what's on canvas, it doesn't
    // disappear once used. Only the confirmed flag changes.
    setMappingDocumentConfirmed(true);
    addLog(`Mapping document confirmed · ${counts.orchestrators ?? '?'} orchestrators · ${counts.squads ?? '?'} squads · ${counts.agents ?? '?'} agents · ${counts.adapters ?? '?'} adapters`);
    onConfirm?.();
  };

  const handleExportCsv = () => {
    const fname = `k9x_traceability-matrix-${Date.now()}.csv`;
    downloadText(fname, rowsToCsv(rows), 'text/csv;charset=utf-8');
    addLog(`Exported traceability matrix — ${fname}`);
  };

  const handleImportCsv = (file: File) => {
    file.text().then((text) => {
      const parsed = parseCsv(text);
      if (parsed.length === 0) { addLog('CSV import: no rows found', 'warn'); return; }
      // Match uploaded rows back to the current set by process_id, so a
      // row a human deleted/reordered/added by hand doesn't silently break
      // things — anything without a recognizable process_id from the
      // current matrix is dropped with a warning rather than guessed at.
      const currentById = new Map(rows.map((r) => [r.process_id, r]));
      const next: Row[] = [];
      let unmatched = 0;
      for (const p of parsed) {
        const pid = p.process_id || null;
        const existing = pid != null ? currentById.get(pid) : undefined;
        if (!existing) { unmatched++; continue; }
        const newZone = p.zone || existing.zone;
        next.push({
          ...existing,
          zone: newZone,
          orchestrator: p.orchestrator || existing.orchestrator,
          squad: p.squad || existing.squad,
          component: p.component || existing.component,
          // Derived from zone here too, same as the inline Zone dropdown —
          // never taken from the CSV's own agent_base_type column, which
          // would let an offline-edited zone/type mismatch (e.g. RED +
          // BaseAgent) slip in through a different door than the one just
          // closed in the UI.
          agent_base_type: existing.component_kind === 'agent' ? (ZONE_TO_AGENT_TYPE[newZone as string] ?? existing.agent_base_type) : existing.agent_base_type,
        });
      }
      if (unmatched > 0) addLog(`CSV import: ${unmatched} row(s) had no matching process_id in the current matrix, skipped`, 'warn');
      setRows(next);
      addLog(`Imported traceability matrix — ${next.length} row(s) applied`);
    }).catch(() => addLog('CSV import failed — could not read the file', 'error'));
  };

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#e2e2f0', marginBottom: 4 }}>
            Process → Implementation Traceability Matrix
          </div>
          <div style={{ fontSize: 12, color: '#8892a4' }}>
            {mappingDocumentConfirmed
              ? 'Confirmed — this is what the current canvas was built from. Edit and re-confirm to rebuild it.'
              : 'Review or edit below — inline, or edit offline: export to CSV, edit in a spreadsheet, re-upload — then confirm to build the canvas. Nothing downstream is generated until you confirm.'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          <button onClick={handleExportCsv} style={secondaryBtnStyle} title="Download this matrix as a CSV">
            ⬇ Export CSV
          </button>
          <label style={{ ...secondaryBtnStyle, cursor: 'pointer' }} title="Upload an edited CSV — matched back by Process ID">
            ⬆ Import CSV
            <input
              type="file" accept=".csv" style={{ display: 'none' }}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImportCsv(f); e.target.value = ''; }}
            />
          </label>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {(['orchestrators', 'squads', 'agents', 'adapters'] as const).map((k) => (
          <div key={k} style={{
            background: 'rgba(99,102,241,0.06)', border: '1px solid var(--border)', borderRadius: 6,
            padding: '6px 12px', fontSize: 12, color: '#c9cadb',
          }}>
            <span style={{ fontWeight: 700, color: '#e2e2f0' }}>{counts[k] ?? 0}</span>{' '}
            <span style={{ color: '#8892a4', textTransform: 'capitalize' }}>{k}</span>
          </div>
        ))}
      </div>

      {(notes.governance || notes.zero_trust) && (
        <div style={{
          background: 'rgba(99,102,241,0.05)', border: '1px solid var(--border)', borderRadius: 8,
          padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8892a4' }}>
            Governance &amp; Zero Trust — applies to every row below, stated once here
          </div>
          {notes.zero_trust && (
            <div style={{ fontSize: 12, color: '#c9cadb', lineHeight: 1.5 }}>
              <span style={{ fontWeight: 700, color: '#e2e2f0' }}>Zero Trust: </span>{notes.zero_trust}
            </div>
          )}
          {notes.governance && (
            <div style={{ fontSize: 12, color: '#c9cadb', lineHeight: 1.5 }}>
              <span style={{ fontWeight: 700, color: '#e2e2f0' }}>Governance: </span>{notes.governance}
            </div>
          )}
        </div>
      )}

      <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: 8 }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 2150 }}>
          <thead>
            <tr>
              <th style={thStyle}>Process ID</th>
              <th style={thStyle}>Element</th>
              <th style={thStyle}>Zone</th>
              <th style={thStyle}>Orchestrator</th>
              <th style={thStyle}>Squad</th>
              <th style={thStyle}>Component</th>
              <th style={thStyle}>Agent Base Type</th>
              <th style={thStyle}>Governance</th>
              <th style={thStyle}>Zero Trust</th>
              <th style={thStyle}>HITL Touchpoint</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={`${r.process_id}-${r.component}`}>
                <td style={{ ...tdStyle, fontFamily: 'monospace', color: '#6b6b8a' }}>{r.process_id ?? '—'}</td>
                <td style={elementCellStyle}>{r.process_element}</td>
                <td style={tdStyle}>
                  {r.zone ? (
                    <select
                      value={r.zone}
                      onChange={(e) => {
                        const newZone = e.target.value;
                        // Base Type follows Zone automatically — see the
                        // ZONE_TO_AGENT_TYPE comment above. Only for agent
                        // rows; adapter rows' agent_base_type is
                        // descriptive text ("No code generated..."), not a
                        // real class name, left untouched.
                        const patch: Partial<Row> = { zone: newZone };
                        if (r.component_kind === 'agent') patch.agent_base_type = ZONE_TO_AGENT_TYPE[newZone] ?? r.agent_base_type;
                        updateRow(idx, patch);
                      }}
                      style={{
                        background: '#1e1e2e', color: ZONE_COLORS[r.zone] ?? '#c9cadb',
                        border: `1px solid ${ZONE_COLORS[r.zone] ?? 'var(--border)'}66`,
                        borderRadius: 4, fontSize: 11, padding: '2px 4px', fontWeight: 600,
                      }}
                    >
                      {ZONE_OPTIONS.map((z) => <option key={z} value={z}>{z}</option>)}
                    </select>
                  ) : <span style={{ color: '#5b5b78' }}>—</span>}
                </td>
                <td style={tdStyle}>
                  {r.orchestrator != null ? (
                    <input value={r.orchestrator} onChange={(e) => updateRow(idx, { orchestrator: e.target.value })} style={nameInputStyle} />
                  ) : <span style={{ color: '#5b5b78' }}>—</span>}
                </td>
                <td style={tdStyle}>
                  {r.squad != null ? (
                    <input value={r.squad} onChange={(e) => updateRow(idx, { squad: e.target.value })} style={nameInputStyle} />
                  ) : <span style={{ color: '#5b5b78' }}>—</span>}
                </td>
                <td style={tdStyle}>
                  <input
                    value={r.component}
                    onChange={(e) => updateRow(idx, { component: e.target.value })}
                    style={{ ...nameInputStyle, fontWeight: 600, color: '#e2e2f0' }}
                  />
                </td>
                <td style={wrapCellStyle(200)} title="Derived from Zone — change Zone to change this, it isn't an independent choice.">
                  <span style={{
                    color: r.component_kind === 'agent' ? '#c9cadb'
                      : r.component_kind === 'hil_orchestrator' ? '#14b8a6' : '#5b5b78',
                    fontSize: 11,
                  }}>
                    {r.agent_base_type}
                  </span>
                </td>
                <td style={wrapCellStyle(190)}>{r.governance}</td>
                <td style={wrapCellStyle(190)}>{r.zero_trust ?? '—'}</td>
                <td style={wrapCellStyle(260)}>{r.hitl_touchpoint}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8, paddingBottom: 12 }}>
        <button
          onClick={handleConfirm}
          disabled={building}
          style={{
            padding: '9px 18px', fontSize: 13, fontWeight: 700, letterSpacing: '0.3px',
            background: '#6366f1', border: 'none', borderRadius: 6, color: '#fff',
            cursor: building ? 'default' : 'pointer', opacity: building ? 0.7 : 1,
          }}
        >
          {building ? '⟳ Building Canvas…' : mappingDocumentConfirmed ? '↻ Rebuild Canvas' : '✓ Confirm & Build Canvas'}
        </button>
        {building && (
          <div style={{ width: '100%' }}>
            <K9Meter progress={buildProgress} label={buildProgress < 99 ? 'Building…' : 'Done!'} />
          </div>
        )}
      </div>
    </div>
  );
}
