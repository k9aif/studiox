import { useEffect, useMemo, useState } from 'react';
import type { Node } from '@xyflow/react';
import { useStore } from '../store';
import { buildProjectPayload } from './Studio';
import { buildClassDiagramPuml, plantUmlSvgUrl, toSnake } from '../classDiagram';
import type { NodeData } from '../types';

export function ClassDiagramView() {
  const { project, nodes, edges, llmConfig, lastTemplateId } = useStore();
  const [imgError, setImgError] = useState(false);
  const [liveSvgUrl, setLiveSvgUrl] = useState<string | null>(null);

  const isTemplate = Boolean(lastTemplateId);

  const puml = useMemo(() => {
    if (isTemplate) return null;
    const payload = buildProjectPayload(project, nodes as Node<NodeData>[], edges, llmConfig);
    return buildClassDiagramPuml(payload);
  }, [isTemplate, project, nodes, edges, llmConfig]);

  useEffect(() => {
    if (isTemplate || !puml) { setLiveSvgUrl(null); return; }
    let cancelled = false;
    setImgError(false);
    plantUmlSvgUrl(puml).then((url) => { if (!cancelled) setLiveSvgUrl(url); });
    return () => { cancelled = true; };
  }, [isTemplate, puml]);

  const svgUrl = isTemplate ? `/class-diagrams/${lastTemplateId}.svg` : liveSvgUrl;
  const pumlHref = isTemplate
    ? `/class-diagrams/${lastTemplateId}.puml`
    : `data:text/plain;charset=utf-8,${encodeURIComponent(puml ?? '')}`;
  const fileBase = isTemplate ? lastTemplateId! : (toSnake(project.project_name || 'project'));

  useEffect(() => {
    setImgError(false);
  }, [svgUrl]);

  if (nodes.length === 0) {
    return (
      <div className="center-placeholder">
        Add agents, squads, and an orchestrator to the canvas to see the class diagram.
      </div>
    );
  }

  return (
    <div className="classdiagram-view">
      <div className="classdiagram-toolbar">
        <div className="classdiagram-title">
          Class Diagram
          {isTemplate && (
            <span className="classdiagram-badge" title="This diagram was pre-generated for the template and doesn't regenerate as you tweak the canvas.">
              Pre-generated for this template
            </span>
          )}
        </div>
        <div className="classdiagram-actions">
          {svgUrl && (
            <a className="btn-secondary" href={svgUrl} target="_blank" rel="noopener noreferrer">
              Open full size
            </a>
          )}
          <a className="btn-secondary" href={pumlHref} download={`${fileBase}_class_diagram.puml`}>
            Download .puml
          </a>
        </div>
      </div>
      <div className="classdiagram-canvas">
        {!svgUrl ? (
          <div className="classdiagram-error">Rendering diagram…</div>
        ) : imgError ? (
          <div className="classdiagram-error">
            Couldn't reach the diagram renderer (plantuml.com) — check your network connection,
            or download the <code>.puml</code> and render locally with <code>plantuml -tsvg</code>.
          </div>
        ) : (
          <img src={svgUrl} alt="Class diagram" onError={() => setImgError(true)} />
        )}
      </div>
    </div>
  );
}
