/** One half-circle gauge split into coloured segments that add up to the whole (plain SVG, no chart library). */
export interface Segment { value: number; color: string; label: string }

const ARC = "M 20 120 A 100 100 0 0 1 220 120";
const GAP = 0.8; // small visual gap between segments, in % of the arc

export function SegmentedGauge({ segments, total, centreLabel }: { segments: Segment[]; total: number; centreLabel: string }) {
  let offset = 0;
  const visible = segments.filter((s) => s.value > 0);
  return (
    <figure className="gauge" aria-label={`${total} ${centreLabel}: ` + segments.map((s) => `${s.value} ${s.label}`).join(", ")}>
      <svg viewBox="0 0 240 132" role="img" aria-hidden="true">
        <path d={ARC} fill="none" stroke="#eef0f3" strokeWidth="22" />
        {total > 0 && visible.map((s, i) => {
          const share = (s.value / total) * 100;
          const len = Math.max(0, share - (visible.length > 1 ? GAP : 0));
          const el = (
            <path key={s.label} d={ARC} fill="none" stroke={s.color} strokeWidth="22" pathLength={100}
              strokeDasharray={`${len} 100`} strokeDashoffset={-offset - (i > 0 ? GAP / 2 : 0)} />
          );
          offset += share;
          return el;
        })}
      </svg>
      {/* Centre text is HTML (not SVG text) so it selects and highlights like normal text. */}
      <figcaption className="gauge-centre">
        <div className="gauge-number">{total}</div>
        <div className="gauge-centre-label">{centreLabel}</div>
      </figcaption>
    </figure>
  );
}
