import { useStore } from './store';

// Opening an imported K9-AIF application (k9aif_project_service.py's record),
// shared by Intake's "Import K9-AIF Project" tile and the left pane's list of
// imported applications, so both open it the same way: a fresh project whose
// canvas is drawn from the record, rule-based, with no scaffold to generate.

export const SHARED_CHANGED_EVENT = 'k9aif-shared-changed';

export function openImportedRecord(record: any) {
  const st = useStore.getState();
  const src = record.source ?? {};
  const pm = record.process_model;
  st.clearProject();
  st.setLastTemplateId(null);
  st.setLastTemplateSuggestion(null);
  st.setProject({
    ...useStore.getState().project,
    project_name: record.process_name,
    description: `Existing K9-AIF application imported from ${src.repo ?? src.filename}` +
      (src.commit_short ? ` @ ${src.commit_short}` : '') + '.',
    imported_from: {
      kind: src.kind, repo: src.repo, url: src.url, filename: src.filename,
      commit_short: src.commit_short, commit_date: src.commit_date,
      process_model: pm ? `${pm.id}${pm.as_of ? ` (as of ${pm.as_of})` : ''}` : undefined,
      live_url: record.live_url || undefined,
      record,
    },
  });
  st.setCanvasIsRuleBased(true);
  st.setPendingCanvasSuggestion(record.suggestion);
  const c = record.counts ?? {};
  st.addLog(`✓ Opened K9-AIF application ${record.process_name}` + (src.commit_short ? ` @ ${src.commit_short}` : '') +
    ` · ${c.orchestrators} orchestrators · ${c.squads} squads · ${c.agents} agents · ${c.gates} gates`);
  (record.warnings ?? []).forEach((w: string) => st.addLog(`⚠ ${w}`, 'warn'));
  st.setCenterTab('canvas');
}

export async function downloadArchitectureDocument(record: any) {
  const res = await fetch('/api/k9aif-project/document', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record),
  });
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  const blob = await res.blob();
  const name = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') ?? '')?.[1] ?? 'architecture.md';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}
