import { useState, useEffect } from 'react';
import { useStore } from '../store';

type CloneState = 'idle' | 'cloning' | 'done' | 'error';
type VerifyState = 'idle' | 'checking' | 'not_found' | 'cloning' | 'done' | 'error';

const FRAMEWORK_REPO = 'https://github.com/k9aif/k9-aif-framework.git';

function buildDefaultClonePath(projectsRoot: string): string {
  if (projectsRoot) {
    const base = projectsRoot.endsWith('/') ? projectsRoot : `${projectsRoot}/`;
    return `${base}k9-aif-framework`;
  }
  return `~/k9-aif-framework`;
}

export function SetupScreen() {
  const { setScreen, setProject, project } = useStore();

  // ── Fetch runtime config (projects_root from env) ─────────────
  const [projectsRoot, setProjectsRoot] = useState('');
  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((cfg) => {
        if (cfg.projects_root) setProjectsRoot(cfg.projects_root);
      })
      .catch(() => {});
  }, []);

  // ── Option A: already have it ─────────────────────────────────
  const [existingPath, setExistingPath] = useState('');
  const [pathError, setPathError] = useState('');
  const inContainer = Boolean(projectsRoot);
  const [verifyState, setVerifyState] = useState<VerifyState>('idle');
  const [verifyError, setVerifyError] = useState('');
  const [resolvedPath, setResolvedPath] = useState('');

  const applyPath = (p: string) => {
    const base = p.endsWith('/') ? p : `${p}/`;
    setProject({ ...project, framework_path: p, project_folder: `${base}k9_projects/` });
    setScreen('studio');
  };

  const handleUseExisting = async () => {
    const p = existingPath.trim();
    if (!p) { setPathError('Enter the path to your k9-aif-framework folder'); return; }
    setVerifyState('checking');
    setPathError('');
    try {
      const res = await fetch('/api/setup/verify-framework', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: p }),
      });
      const data = await res.json();
      setResolvedPath(data.path);
      if (data.valid) {
        applyPath(data.path);
      } else {
        setVerifyState('not_found');
      }
    } catch {
      setVerifyState('idle');
      setPathError('Could not verify path — check the server is running');
    }
  };

  const handleCloneInPlace = async () => {
    setVerifyState('cloning');
    setVerifyError('');
    try {
      const res = await fetch('/api/setup/clone-framework', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: resolvedPath, repo_url: FRAMEWORK_REPO }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Clone failed');
      setVerifyState('done');
      setTimeout(() => applyPath(data.path), 800);
    } catch (err: any) {
      setVerifyState('error');
      setVerifyError(err.message ?? 'Clone failed');
    }
  };

  // ── Option B: clone into a new folder ────────────────────────
  const [clonePath, setClonePath] = useState(() => buildDefaultClonePath(''));
  useEffect(() => {
    setClonePath((prev) => {
      // Only update if user hasn't typed anything custom
      const defaultNoRoot = buildDefaultClonePath('');
      if (prev === defaultNoRoot || prev === '') return buildDefaultClonePath(projectsRoot);
      return prev;
    });
  }, [projectsRoot]);

  const [cloneState, setCloneState] = useState<CloneState>('idle');
  const [cloneError, setCloneError] = useState('');
  const [clonedAt, setClonedAt] = useState('');

  const handleClone = async () => {
    const p = clonePath.trim();
    if (!p) return;
    setCloneState('cloning');
    setCloneError('');
    try {
      const res = await fetch('/api/setup/clone-framework', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: p, repo_url: FRAMEWORK_REPO }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Clone failed');
      const resolved = data.path as string;
      const base = resolved.endsWith('/') ? resolved : `${resolved}/`;
      setClonedAt(data.note === 'already_exists' ? `${resolved} (already exists — reusing)` : resolved);
      setProject({ ...project, framework_path: resolved, project_folder: `${base}k9_projects/` });
      setCloneState('done');
    } catch (err: any) {
      setCloneState('error');
      setCloneError(err.message ?? 'Clone failed');
    }
  };

  return (
    <div className="setup-screen">
      <div className="setup-card">

        <div className="setup-logo">
          <a className="logo-k9" href="https://k9x.ai" target="_blank" rel="noopener noreferrer">K9X</a>
          <span className="logo-studio">Studio</span>
        </div>
        <div className="setup-tagline">Architecture-First AI Builder · K9-AIF Framework</div>

        <div className="setup-prompt">
          K9X Studio needs the <strong>k9-aif-framework</strong> to generate project scaffolds.<br />
          Point me to it, or let me set it up for you.
        </div>

        {/* ── Option A ──────────────────────────────────────── */}
        <div className="setup-option">
          <div className="setup-option-label">I already have it</div>
          <div className="setup-option-sub">
            {inContainer
              ? <>Enter the path inside the container — your <code>~/k9x-projects</code> folder on the host is mounted at <code>{projectsRoot}</code></>
              : 'Enter the full path to your k9-aif-framework folder'}
          </div>
          <div className="setup-input-row">
            <input
              className="setup-input"
              placeholder={inContainer ? `${projectsRoot}/k9-aif-framework` : '~/path/to/k9-aif-framework'}
              value={existingPath}
              onChange={(e) => {
                setExistingPath(e.target.value);
                setPathError('');
                setVerifyState('idle');
              }}
              onKeyDown={(e) => e.key === 'Enter' && handleUseExisting()}
              disabled={verifyState === 'checking' || verifyState === 'cloning' || verifyState === 'done'}
              autoFocus
            />
            {!inContainer && (
              <button
                className="setup-browse-btn"
                title="Browse (returns folder name only — type full path for accuracy)"
                onClick={async () => {
                  try {
                    const dir = await (window as any).showDirectoryPicker({ mode: 'read' });
                    setExistingPath(dir.name);
                    setPathError('');
                    setVerifyState('idle');
                  } catch { /* cancelled */ }
                }}
              >⋯</button>
            )}
          </div>

          {pathError && <div className="setup-field-error">{pathError}</div>}

          {verifyState === 'idle' && (
            <button
              className="setup-btn-primary"
              onClick={handleUseExisting}
              disabled={!existingPath.trim()}
            >
              Use this folder →
            </button>
          )}

          {verifyState === 'checking' && (
            <div className="setup-checking">⟳ Checking framework…</div>
          )}

          {verifyState === 'not_found' && (
            <div className="setup-not-found">
              <div className="setup-not-found-msg">
                ⚠ k9-aif-framework not found at <code>{resolvedPath}</code>
              </div>
              <div className="setup-not-found-sub">Clone it there now?</div>
              <div className="setup-not-found-actions">
                <button className="setup-btn-primary" onClick={handleCloneInPlace}>
                  Clone framework here →
                </button>
                <button className="setup-btn-ghost" onClick={() => setVerifyState('idle')}>
                  Enter a different path
                </button>
              </div>
            </div>
          )}

          {verifyState === 'cloning' && (
            <div className="setup-checking">⟳ Cloning k9-aif-framework…</div>
          )}

          {verifyState === 'done' && (
            <div className="setup-clone-ok">✓ Framework ready — opening Studio…</div>
          )}

          {verifyState === 'error' && (
            <div className="setup-field-error">✕ {verifyError}</div>
          )}
        </div>

        <div className="setup-or"><span>or</span></div>

        {/* ── Option B ──────────────────────────────────────── */}
        <div className="setup-option">
          <div className="setup-option-label">Set it up for me</div>
          <div className="setup-option-sub">
            {inContainer
              ? <>Cloned files will be saved inside the container at <code>{projectsRoot}</code> — this maps to <code>~/k9x-projects</code> on your host</>
              : 'Point to a folder — K9X Studio will clone the framework from GitHub and prepare it for development'}
          </div>
          <div className="setup-input-row">
            <input
              className="setup-input"
              placeholder="~/k9-aif-framework"
              value={clonePath}
              onChange={(e) => { setClonePath(e.target.value); setCloneState('idle'); }}
              disabled={cloneState === 'cloning' || cloneState === 'done'}
            />
          </div>
          <div className="setup-repo-hint">↓ {FRAMEWORK_REPO}</div>

          {cloneState !== 'done' && (
            <button
              className="setup-btn-primary"
              onClick={handleClone}
              disabled={!clonePath.trim() || cloneState === 'cloning'}
            >
              {cloneState === 'cloning' ? '⟳  Cloning framework…' : 'Clone & Setup →'}
            </button>
          )}
          {cloneState === 'error' && (
            <div className="setup-field-error">✕ {cloneError}</div>
          )}
          {cloneState === 'done' && (
            <div className="setup-clone-success">
              <div className="setup-clone-ok">✓ Framework ready · {clonedAt}</div>
              <div className="setup-clone-hint">
                Scaffold projects will be generated into <code>{clonedAt}/k9_projects/</code>
              </div>
              <button className="setup-btn-primary" onClick={() => setScreen('studio')}>
                Open Studio →
              </button>
            </div>
          )}
        </div>

        <div className="setup-footer-skip">
          <button className="setup-skip-btn" onClick={() => setScreen('studio')}>
            Skip — I'll configure the framework path in Project Info
          </button>
        </div>

      </div>
    </div>
  );
}
