interface Props {
  visible: boolean;
  zipName: string;
  onClose: () => void;
  onViewScaffold: () => void;
}

export function ScaffoldDoneOverlay({ visible, zipName, onClose, onViewScaffold }: Props) {
  if (!visible) return null;

  return (
    <div className="scaffold-done-overlay" onClick={onClose}>
      <div className="scaffold-done-card" onClick={(e) => e.stopPropagation()}>
        <div className="scaffold-done-icon">✓</div>
        <div className="scaffold-done-title">Scaffold downloaded</div>
        <div className="scaffold-done-path">{zipName}</div>
        <div className="scaffold-done-body">
          Next steps:<br />
          1. Move <code>{zipName}</code> into a project folder<br />
          2. <code>unzip {zipName}</code> and <code>cd</code> into it<br />
          3. Run <code>./setup.sh</code> — one-time venv, framework path, deps, .env<br />
          4. Run <code>./run.sh</code>
        </div>
        <div className="scaffold-done-hint">
          See <code>README.md</code> inside the scaffold for the Ollama models
          (or other LLM provider) this project needs.
        </div>
        <div className="scaffold-done-actions">
          <button className="scaffold-done-btn" onClick={onViewScaffold}>View Scaffold</button>
          <button className="scaffold-done-btn" onClick={onClose}>Got it</button>
        </div>
      </div>
    </div>
  );
}
