import { useState } from 'react';
import type { CSSProperties } from 'react';
import { useStore } from '../store';

// Pre-generation review surface for Process Studio's companion Agent
// Evaluation Plan (-evals.md) — Ravi: an IBM reviewer impressed by
// Traceability/Canvas would next ask "how is the eval file used, where are
// the test cases" — this answers that before scaffold generation, the same
// role Traceability plays for the BPMN/blueprint side.
//
// Reads project.source_evals_rows (persisted, set by IntakePanel.tsx's
// stageEvalsFile) rather than the ephemeral stagedEvals store slot, so this
// survives a refresh the same way Traceability's pendingMappingDocument does.

const CATEGORY_TITLES: Record<string, string> = {
  functional: 'Functional Evals',
  behavioral: 'Behavioral Evals',
  adversarial: 'Adversarial Evals',
  domain: 'Domain Evals',
  failure_mode: 'Failure Mode & Fallback Testing',
  hitl: 'Human-in-the-Loop Validation',
  observability: 'Observability Validation',
  regression: 'Regression Baseline Lock',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#da1e28', blocker: '#da1e28', major: '#f1c21b', minor: '#24a148',
};

// Same heuristic as scaffold_service.py's _gen_eval_test_files: an eval
// row's Step ("ATSn", Process Studio's own convention) resolves against the
// traceability matrix's process_id ("Task_n"/"Task_n_review") to name the
// real generated component — informational only, mirrored client-side so
// this panel shows the same resolution the scaffold will actually use.
function resolveComponent(step: string, mappingRows: any[]): string | null {
  const m = /^ATS(\d+)$/i.exec((step || '').trim());
  if (!m) return null;
  const candidates = new Set([`Task_${m[1]}`, `Task_${m[1]}_review`]);
  const row = mappingRows.find((r) => candidates.has(r.process_id));
  return row ? `${row.component} (${row.component_kind ?? 'agent'})` : null;
}

const thStyle: CSSProperties = {
  textAlign: 'left', padding: '6px 10px', fontSize: 10, fontWeight: 700,
  letterSpacing: '0.06em', textTransform: 'uppercase', color: '#8892a4',
  borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
};
const tdStyle: CSSProperties = {
  padding: '7px 10px', fontSize: 12, color: '#c9cadb',
  borderBottom: '1px solid var(--border-hover)', verticalAlign: 'top',
};

function CategorySection({ title, rows, mappingRows, defaultOpen }: { title: string; rows: any[]; mappingRows: any[]; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
      <button onClick={() => setOpen((v) => !v)} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(99,102,241,0.05)', border: 'none', padding: '10px 14px', cursor: 'pointer',
      }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#c9cadb' }}>{title}</span>
        <span style={{ fontSize: 11, color: '#8892a4' }}>{rows.length} case{rows.length === 1 ? '' : 's'} {open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div style={{ overflow: 'auto', maxHeight: 360 }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 1180 }}>
            <thead>
              <tr>
                <th style={{ ...thStyle, position: 'sticky', top: 0, background: '#121218', zIndex: 1 }}>ID</th>
                <th style={{ ...thStyle, width: 240, position: 'sticky', top: 0, background: '#121218', zIndex: 1 }}>Agent</th>
                <th style={{ ...thStyle, width: 300, position: 'sticky', top: 0, background: '#121218', zIndex: 1 }}>Scenario</th>
                <th style={{ ...thStyle, width: 260, position: 'sticky', top: 0, background: '#121218', zIndex: 1 }}>Pass Criteria</th>
                <th style={{ ...thStyle, position: 'sticky', top: 0, background: '#121218', zIndex: 1 }}>Severity</th>
                <th style={{ ...thStyle, width: 260, position: 'sticky', top: 0, background: '#121218', zIndex: 1 }}>Framework Coverage</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const component = resolveComponent(r.step, mappingRows);
                const coverage = r.framework_coverage;
                return (
                  <tr key={r.id}>
                    <td style={{ ...tdStyle, fontFamily: 'monospace', color: '#6b6b8a' }}>{r.id}</td>
                    <td style={{ ...tdStyle, whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      {r.agent}
                      {component && <div style={{ fontSize: 10, color: '#8892a4', marginTop: 2 }}>→ {component}</div>}
                    </td>
                    <td style={{ ...tdStyle, whiteSpace: 'normal', wordBreak: 'break-word' }}>{r.scenario}</td>
                    <td style={{ ...tdStyle, whiteSpace: 'normal', wordBreak: 'break-word', color: '#8892a4', fontSize: 11 }}>{r.pass_criteria}</td>
                    <td style={tdStyle}>
                      <span style={{ color: SEVERITY_COLORS[(r.severity || '').toLowerCase()] ?? '#8892a4', fontWeight: 600, fontSize: 11 }}>
                        {r.severity}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      {coverage && coverage.checks && coverage.checks.length > 0 ? (
                        <div title={coverage.note ?? undefined}>
                          {coverage.checks.map((name: string) => {
                            const partial = coverage.status === 'partial';
                            const color = partial ? '#f1c21b' : '#7ee8b8';
                            return (
                              <span key={name} style={{
                                display: 'inline-block', fontSize: 10, fontWeight: 600, color,
                                background: partial ? 'rgba(241,194,27,0.1)' : 'rgba(82,183,136,0.1)',
                                border: `1px solid ${partial ? 'rgba(241,194,27,0.35)' : 'rgba(82,183,136,0.3)'}`,
                                borderRadius: 4, padding: '2px 6px', marginRight: 4, marginBottom: 3,
                              }}>
                                {partial ? '⚠' : '🛡'} {name}
                              </span>
                            );
                          })}
                        </div>
                      ) : coverage && coverage.note ? (
                        <span style={{ fontSize: 10, color: '#8892a4', fontStyle: 'italic' }}>{coverage.note}</span>
                      ) : (
                        <span style={{ color: '#5b5b78', fontSize: 11 }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function EvalsPanel() {
  const { project, pendingMappingDocument } = useStore();
  const rows: any[] = (project as any).source_evals_rows ?? [];
  const mappingRows: any[] = pendingMappingDocument?.mapping_document?.rows ?? [];

  if (rows.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 36 }}>
        <div style={{ maxWidth: 460, textAlign: 'center', color: '#5b5b78', fontSize: 13, lineHeight: 1.7 }}>
          This tab shows staged test cases from an Agent Evaluation Plan — a Markdown file (usually
          ending in <code>-evals.md</code>) with Functional, Behavioral, Adversarial and other eval
          sections, such as the one IBM Process Studio generates alongside its BPMN and spec.
          <br /><br />
          Upload one on the Intake tab to see it here.
        </div>
      </div>
    );
  }

  const byCategory: Record<string, any[]> = {};
  for (const r of rows) {
    (byCategory[r.category] ??= []).push(r);
  }
  const categories = Object.entries(byCategory);

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#e2e2f0', marginBottom: 4 }}>
          Agent Evaluation Plan
        </div>
        <div style={{ fontSize: 12, color: '#8892a4' }}>
          {(project as any).source_evals_filename} — {rows.length} test cases staged. Generating the scaffold adds
          one pytest stub per case under <code>tests/evals/</code>, grouped the same way as below — every stub
          runs and passes out of the box; the SA replaces each placeholder with a real assertion against its own
          Pass Criteria.
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {categories.map(([cat, catRows]) => (
          <div key={cat} style={{
            background: 'rgba(99,102,241,0.06)', border: '1px solid var(--border)', borderRadius: 6,
            padding: '6px 12px', fontSize: 12, color: '#c9cadb',
          }}>
            <span style={{ fontWeight: 700, color: '#e2e2f0' }}>{catRows.length}</span>{' '}
            <span style={{ color: '#8892a4' }}>{CATEGORY_TITLES[cat] ?? cat}</span>
          </div>
        ))}
      </div>

      {categories.map(([cat, catRows], idx) => (
        <CategorySection
          key={cat}
          title={CATEGORY_TITLES[cat] ?? cat}
          rows={catRows}
          mappingRows={mappingRows}
          defaultOpen={idx === 0}
        />
      ))}
    </div>
  );
}
