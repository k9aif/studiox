import { useState } from 'react';
import { useStore } from '../store';
import { marked } from 'marked';

// Folder display order to match K9-AIF framework convention
const FOLDER_ORDER = ['config', 'orchestrators', 'squads', 'agents', 'utils', 'tests', 'deploy', 'docs', 'data', 'api'];

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: TreeNode[];
  content?: string;
}

function buildTree(files: { path: string; content: string }[]): TreeNode[] {
  const root: TreeNode[] = [];
  const map: Record<string, TreeNode> = {};

  // Strip leading app folder name
  const prefix = files[0]?.path.split('/')[0] ?? '';

  const sorted = [...files].sort((a, b) => {
    const aParts = a.path.split('/');
    const bParts = b.path.split('/');
    // Sort folders before files, then by FOLDER_ORDER
    const aFolder = aParts[1] ?? '';
    const bFolder = bParts[1] ?? '';
    const aIdx = FOLDER_ORDER.indexOf(aFolder);
    const bIdx = FOLDER_ORDER.indexOf(bFolder);
    if (aIdx !== bIdx) return (aIdx === -1 ? 99 : aIdx) - (bIdx === -1 ? 99 : bIdx);
    return a.path.localeCompare(b.path);
  });

  sorted.forEach((file) => {
    const parts = file.path.split('/').slice(1); // remove app folder prefix
    let current = root;
    let pathSoFar = prefix;

    parts.forEach((part, i) => {
      pathSoFar += '/' + part;
      const isLast = i === parts.length - 1;
      let node = map[pathSoFar];
      if (!node) {
        node = { name: part, path: pathSoFar, isDir: !isLast, children: [], content: isLast ? file.content : undefined };
        map[pathSoFar] = node;
        current.push(node);
      }
      current = node.children;
    });
  });

  return root;
}

function FileIcon({ name }: { name: string }) {
  if (name.endsWith('.py')) return <span style={{ color: '#3b82f6' }}>🐍</span>;
  if (name.endsWith('.yaml') || name.endsWith('.yml')) return <span style={{ color: '#f59e0b' }}>📋</span>;
  if (name.endsWith('.md')) return <span style={{ color: '#94a3b8' }}>📄</span>;
  if (name.endsWith('.sh')) return <span style={{ color: '#10b981' }}>⚙</span>;
  if (name.endsWith('.env') || name === '.env.example') return <span style={{ color: '#f87171' }}>🔑</span>;
  if (name.endsWith('.py') && name.startsWith('test_')) return <span style={{ color: '#a78bfa' }}>🧪</span>;
  return <span style={{ color: '#64748b' }}>📄</span>;
}

function TreeItem({ node, depth, selected, onSelect, expanded, onToggle }: {
  node: TreeNode; depth: number; selected: string | null;
  onSelect: (path: string) => void;
  expanded: Set<string>; onToggle: (path: string) => void;
}) {
  const isExpanded = expanded.has(node.path);
  const isSelected = selected === node.path;
  const indent = depth * 14;

  return (
    <>
      <div
        onClick={() => node.isDir ? onToggle(node.path) : onSelect(node.path)}
        style={{
          padding: `2px 8px 2px ${8 + indent}px`,
          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
          color: isSelected ? '#a5b4fc' : node.isDir ? '#c8d0de' : '#8892a4',
          background: isSelected ? 'rgba(99,102,241,0.1)' : 'transparent',
          borderLeft: isSelected ? '2px solid #6366f1' : '2px solid transparent',
          fontSize: 12, userSelect: 'none',
        }}
      >
        {node.isDir ? (
          <span style={{ fontSize: 9, color: '#475569', minWidth: 8 }}>{isExpanded ? '▼' : '▶'}</span>
        ) : (
          <span style={{ minWidth: 8 }} />
        )}
        {node.isDir ? (
          <span style={{ color: isExpanded ? '#f59e0b' : '#94a3b8' }}>📁</span>
        ) : (
          <FileIcon name={node.name} />
        )}
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{node.name}</span>
      </div>
      {node.isDir && isExpanded && node.children.map((child) => (
        <TreeItem key={child.path} node={child} depth={depth + 1}
          selected={selected} onSelect={onSelect} expanded={expanded} onToggle={onToggle} />
      ))}
    </>
  );
}

export function ScaffoldView() {
  const { scaffoldFiles } = useStore();
  const [selected, setSelected] = useState<string | null>(null);
  const [treeWidth, setTreeWidth] = useState(280);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggleFolder = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path); else next.add(path);
      return next;
    });
  };

  const expandAll = () => {
    const allDirs = scaffoldFiles.reduce((acc, f) => {
      const parts = f.path.split('/');
      for (let i = 1; i < parts.length; i++) acc.add(parts.slice(0, i).join('/'));
      return acc;
    }, new Set<string>());
    setExpanded(allDirs);
  };

  if (scaffoldFiles.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
        Generate a scaffold first — then browse the files here.
      </div>
    );
  }

  const tree = buildTree(scaffoldFiles);
  const selectedFile = scaffoldFiles.find((f) => f.path === selected || f.path.endsWith('/' + selected?.split('/').pop()));

  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden', height: '100%' }}>
      {/* File tree */}
      <div style={{
        width: treeWidth, minWidth: treeWidth, borderRight: '1px solid var(--border)',
        overflowY: 'auto', fontFamily: "'SF Mono', monospace",
        background: 'var(--panel)', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: '#475569', fontWeight: 600, flex: 1 }}>FILES ({scaffoldFiles.length})</span>
          <button onClick={expandAll} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 10 }} title="Expand all">⊞</button>
          <button onClick={() => setExpanded(new Set())} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 10 }} title="Collapse all">⊟</button>
          <button onClick={() => setTreeWidth(v => v === 280 ? 380 : 280)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 10 }} title="Toggle width">◧</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
          {tree.map((node) => (
            <TreeItem key={node.path} node={node} depth={0}
              selected={selected} onSelect={setSelected}
              expanded={expanded} onToggle={toggleFolder} />
          ))}
        </div>
      </div>

      {/* File content */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {selectedFile ? (
          <>
            <div style={{
              padding: '8px 16px', borderBottom: '1px solid var(--border)',
              fontSize: 11, color: '#64748b', fontFamily: "'SF Mono', monospace",
              background: 'var(--surface)', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span>{selectedFile.path}</span>
              <button onClick={() => {
                const blob = new Blob([selectedFile.content], { type: 'text/plain' });
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
                a.download = selectedFile.path.split('/').pop() ?? 'file'; a.click();
              }} style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', fontSize: 11 }}>
                ⬇ download
              </button>
            </div>
            {selectedFile.path.endsWith('.md') ? (
              <div style={{ padding: '24px 32px', overflow: 'auto', color: '#c8d0de', lineHeight: 1.7, fontSize: 13 }}
                dangerouslySetInnerHTML={{ __html: marked.parse(selectedFile.content) as string }} />
            ) : (
              <pre style={{
                margin: 0, padding: '16px', fontSize: 12, lineHeight: 1.7,
                color: '#c8d0de', background: 'var(--bg)', overflow: 'auto',
                fontFamily: "'SF Mono', 'Fira Code', monospace", whiteSpace: 'pre-wrap',
              }}>
                {selectedFile.content}
              </pre>
            )}
          </>
        ) : (
          <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 12 }}>
            Click a file to view its content.
          </div>
        )}
      </div>
    </div>
  );
}
