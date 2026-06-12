// One-off script: pre-generate class diagram .puml + .svg for each entry in
// PROJECT_TEMPLATES so the "Class Diagram" tab can show a static asset for
// template-originated projects without hitting plantuml.com on every load.
//
// Run with: node scripts/generate-template-diagrams.mjs
// Output:   public/class-diagrams/<template-id>.puml + .svg

import { writeFile } from 'node:fs/promises';
import { deflateRawSync } from 'node:zlib';
import path from 'node:path';
import { PROJECT_TEMPLATES } from '../src/templates.ts';
import { buildClassDiagramPuml } from '../src/classDiagram.ts';

const outDir = path.join(import.meta.dirname, '..', 'public', 'class-diagrams');

// PlantUML's "deflate + custom base64" URL encoding — much more compact than
// the `~h<hex>` raw encoding used elsewhere, needed here because the larger
// templates (saving-grace, god-almighty) exceed the server's GET URL limit
// when hex-encoded.
const PLANTUML_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_';

function encode6bit(b) {
  return PLANTUML_ALPHABET[b & 0x3f];
}

function append3bytes(b1, b2, b3) {
  return (
    encode6bit(b1 >> 2) +
    encode6bit(((b1 & 0x3) << 4) | (b2 >> 4)) +
    encode6bit(((b2 & 0xf) << 2) | (b3 >> 6)) +
    encode6bit(b3 & 0x3f)
  );
}

function plantUmlDeflateUrl(puml) {
  const deflated = deflateRawSync(Buffer.from(puml, 'utf-8'), { level: 9 });
  let out = '';
  for (let i = 0; i < deflated.length; i += 3) {
    out += append3bytes(deflated[i], deflated[i + 1] ?? 0, deflated[i + 2] ?? 0);
  }
  return `https://www.plantuml.com/plantuml/svg/${out}`;
}

for (const t of PROJECT_TEMPLATES) {
  const orchestrators = (t.suggestion.orchestrators ?? []).map((o, i) => ({
    name: o.name,
    squad: t.suggestion.squads?.[i]?.name,
  }));

  const project = {
    project_name: t.name,
    agents: t.suggestion.agents ?? [],
    squads: t.suggestion.squads ?? [],
    orchestrators,
  };

  const puml = buildClassDiagramPuml(project);
  const pumlPath = path.join(outDir, `${t.id}.puml`);
  await writeFile(pumlPath, puml, 'utf-8');

  const svgUrl = plantUmlDeflateUrl(puml);
  const resp = await fetch(svgUrl);
  if (!resp.ok) {
    console.error(`✗ ${t.id}: SVG fetch failed (${resp.status})`);
    continue;
  }
  const svg = await resp.text();
  const svgPath = path.join(outDir, `${t.id}.svg`);
  await writeFile(svgPath, svg, 'utf-8');

  console.log(`✓ ${t.id}: ${puml.length}B puml, ${svg.length}B svg`);
}
