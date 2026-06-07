import { useMemo } from 'react';
import type { Node, Edge } from '@xyflow/react';
import { useStore } from '../store';
import type { NodeData, ProjectMeta } from '../types';

function buildYaml(
  project: ProjectMeta,
  nodes: Node<NodeData>[],
  edges: Edge[]
): string {
  const agents = nodes.filter((n) =>
    ['agent', 'validation_loop', 'critic_actor'].includes(n.data.componentType)
  );
  const squads = nodes.filter((n) => n.data.componentType === 'squad');
  const orchestrators = nodes.filter((n) => n.data.componentType === 'orchestrator');

  const lines: string[] = [];

  lines.push(`# k9x_studio — ${project.project_name}`);
  lines.push(`# Author: ${project.author}  |  Domain: ${project.domain}`);
  lines.push('');

  if (squads.length > 0) {
    lines.push('squads:');
    squads.forEach((sq) => {
      const agentIds = edges
        .filter((e) => e.source === sq.id)
        .map((e) => e.target);
      const squadAgents = agents.filter((a) => agentIds.includes(a.id));

      lines.push(`  ${sq.data.label}:`);
      lines.push(`    description: "${sq.data.description ?? sq.data.label + ' pipeline'}"`);
      lines.push('    agents:');
      squadAgents.forEach((a) => lines.push(`      - ${a.data.label}`));
      lines.push('    flow:');
      squadAgents.forEach((a) => {
        lines.push(`      - agent: ${a.data.label}`);
        lines.push(`        result_key: ${a.data.label.toLowerCase()}`);
      });
      lines.push('');
    });
  }

  if (agents.length > 0) {
    lines.push('# Agent definitions (agents/yaml/*.yaml)');
    agents.forEach((a) => {
      lines.push(`# ${a.data.label}:`);
      lines.push(`#   class: ${a.data.agentType ?? 'BaseAgent'}`);
      lines.push(`#   model: ${a.data.model ?? 'general'}`);
      lines.push(`#   pattern: ${a.data.pattern ?? 'reasoning'}`);
    });
    lines.push('');
  }

  if (orchestrators.length > 0) {
    lines.push('# Orchestrators');
    orchestrators.forEach((o) => {
      lines.push(`# ${o.data.label}: extends BaseOrchestrator`);
    });
  }

  return lines.join('\n');
}

export function YamlPreview() {
  const { project, nodes, edges } = useStore();
  const yaml = useMemo(
    () => buildYaml(project, nodes as Node<NodeData>[], edges),
    [project, nodes, edges]
  );

  return (
    <div className="yaml-panel">
      <div className="yaml-header">YAML Preview</div>
      <pre className="yaml-content">
        {yaml || '# Add components to the canvas to see YAML preview'}
      </pre>
    </div>
  );
}
