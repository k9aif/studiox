import { useEffect, useState } from 'react';

// Ravi: "it would be nice to show a bar like Generating.... square box
// like a amp vol.... and then within 15secs full. that is more
// satisfying." Then: "left side our trademark K9X and have similar bar...
// wherever possible... like from traceability to canvas... givves that
// cool look like it is doing it." A branded VU-meter-style segmented bar,
// shared across every "this is doing real work" moment in the app instead
// of each screen inventing its own spinner/text-cycle.
//
// Ravi: "the bar appeared but was way too fast. I has to be nice, slow,
// square by square... to the end." The original easing curve moved fastest
// right at the start (when p is smallest, (CAP-p)*RATE is largest) — the
// opposite of "slow and nice." A steady linear step reads as one square
// lighting up roughly every ~650ms, ~12-13s to reach CAP — matches the
// original "within 15secs full" ask, evenly paced start to finish instead
// of a fast flash. useClimbingProgress's caller snaps progress to 100 the
// moment the real (or simulated, for near-instant actions — see
// MappingDocumentPanel's Confirm & Build Canvas) work resolves.
const SEGMENTS = 20;
const CAP = 94;
const TICK_MS = 200;
const STEP = 1.5;

export function useClimbingProgress(active: boolean): [number, (v: number) => void] {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    if (!active) {
      setProgress(0);
      return;
    }
    const t = setInterval(() => setProgress((p) => Math.min(p + STEP, CAP)), TICK_MS);
    return () => clearInterval(t);
  }, [active]);
  return [progress, setProgress];
}

export function K9Meter({ progress, label }: { progress: number; label?: string }) {
  const lit = Math.round((progress / 100) * SEGMENTS);
  return (
    <div className="k9-meter">
      <span className="k9-meter-brand">K9X</span>
      <div className="k9-meter-row">
        {Array.from({ length: SEGMENTS }).map((_, i) => (
          <span key={i} className={`k9-meter-seg ${i < lit ? 'k9-meter-seg-lit' : ''}`} />
        ))}
      </div>
      {label && <span className="k9-meter-label">{label}</span>}
    </div>
  );
}
