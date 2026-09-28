interface Props {
  visible: boolean;
  zipName: string;
  onClose: () => void;
  onViewScaffold: () => void;
  onViewGeneratedDocs: () => void;
}

// Ravi: "I think we have to just mention scaffold generated, download from
// 'generated docs' tab, click and so on... so the user can download anytime
// they want from the tab. this would be clean" — given the download-
// reliability saga (stuck .crdownload files, browser-specific quirks), this
// no longer assumes the auto-download definitely landed on disk, or walks
// through unzip/setup.sh/run.sh here (that's the scaffold's own README.md's
// job). It just confirms generation succeeded and points at the one place
// the file is always available on demand: the Generated Docs tab (server-
// side archive, see routes.py's /api/generated-archive), independent of
// whether any one browser download attempt worked.
export function ScaffoldDoneOverlay({ visible, zipName, onClose, onViewScaffold, onViewGeneratedDocs }: Props) {
  if (!visible) return null;

  return (
    <div className="scaffold-done-overlay" onClick={onClose}>
      <div className="scaffold-done-card" onClick={(e) => e.stopPropagation()}>
        <div className="scaffold-done-icon">✓</div>
        <div className="scaffold-done-title">Scaffold generated</div>
        <div className="scaffold-done-path">{zipName}</div>
        <div className="scaffold-done-body">
          Download it anytime from the <strong>Generated Docs</strong> tab.
        </div>
        <div className="scaffold-done-actions">
          <button className="scaffold-done-btn" onClick={onViewScaffold}>View Scaffold</button>
          <button className="scaffold-done-btn" onClick={onViewGeneratedDocs}>Generated Docs</button>
          <button className="scaffold-done-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
