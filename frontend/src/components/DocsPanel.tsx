import { useEffect, useState } from 'react';
import { useStore } from '../store';

function downloadDoc(name: string, content: string) {
  if (content.startsWith('blob:')) {
    const a = document.createElement('a');
    a.href = content; a.download = name; a.click();
  } else {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name; a.click();
    URL.revokeObjectURL(url);
  }
}

interface DocFile {
  name: string;
  path: string;
  size: number;
}

export function DocsPanel() {
  const { project, generatedDocs, removeGeneratedDoc } = useStore();
  const [docs, setDocs] = useState<DocFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDelete = async (path: string) => {
    try {
      await fetch(`/api/delete-file?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      setDocs((prev) => prev.filter((f) => f.path !== path));
    } catch { /* silent */ }
  };

  useEffect(() => {
    if (!project.project_folder || !project.project_name) return;
    setLoading(true);
    fetch(`/api/docs?folder=${encodeURIComponent(project.project_folder)}`)
      .then((r) => r.json())
      .then((d) => { setDocs(d.files ?? []); setError(''); })
      .catch(() => setError('Could not load docs'))
      .finally(() => setLoading(false));
  }, [project.project_folder]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="docs-panel">
      <div className="docs-header">
        <div className="docs-title">Generated Docs</div>
        <div className="docs-sub">
          {project.project_folder
            ? <code className="docs-path">{project.project_folder}</code>
            : 'No project folder set — configure in Intake'}
        </div>
      </div>

      {/* In-memory generated docs */}
      {generatedDocs.length > 0 && (
        <div className="docs-list" style={{ marginBottom: 16 }}>
          {generatedDocs.map((d) => (
            <div key={d.name} className="docs-item">
              <span className="docs-icon">📄</span>
              <span className="docs-name">{d.name}</span>
              <span className="docs-size" style={{ color: '#4a7ab5' }}>{d.ts}</span>
              <button className="docs-download-btn" onClick={() => downloadDoc(d.name, d.content)} title="Download">⬇</button>
              <button className="docs-delete-btn" onClick={() => removeGeneratedDoc(d.name)} title="Remove">🗑</button>
            </div>
          ))}
        </div>
      )}

      {loading && <div className="docs-state">Loading…</div>}
      {error && generatedDocs.length === 0 && <div className="docs-state docs-error">{error}</div>}
      {!loading && !error && docs.length === 0 && (
        <div className="docs-state">
          No generated files yet.<br />
          Generate a scaffold first.
        </div>
      )}

      {docs.length > 0 && (
        <div className="docs-list">
          {docs.map((f) => (
            <div key={f.path} className="docs-item">
              <span className="docs-icon">{f.name.endsWith('.zip') ? '📦' : f.name.endsWith('.md') ? '📄' : '📁'}</span>
              <span className="docs-name">{f.name}</span>
              <span className="docs-size">{formatSize(f.size)}</span>
              <a
                className="docs-download-btn"
                href={`/api/download?path=${encodeURIComponent(f.path)}`}
                download={f.name}
                title="Download"
              >⬇</a>
              <button
                className="docs-delete-btn"
                onClick={() => handleDelete(f.path)}
                title="Delete"
              >🗑</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
