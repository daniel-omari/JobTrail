/** Half-circle gauge drawn in plain SVG (no chart library). `value / of` sets how full the arc is. */
export function Gauge({ value, of, color, label, caption }: {
  value: number; of: number; color: string; label: string; caption: string;
}) {
  const fraction = of > 0 ? Math.min(1, value / of) : 0;
  const arc = "M 20 110 A 90 90 0 0 1 200 110";
  return (
    <figure className="gauge" aria-label={`${label}: ${value}`}>
      <svg viewBox="0 0 220 124" role="img" aria-hidden="true">
        <path d={arc} fill="none" stroke="#eef0f3" strokeWidth="16" strokeLinecap="round" />
        {fraction > 0 && (
          <path d={arc} fill="none" stroke={color} strokeWidth="16" strokeLinecap="round"
            pathLength={100} strokeDasharray={`${fraction * 100} 100`} />
        )}
        <text x="110" y="100" textAnchor="middle" className="gauge-number" fill={color}>{value}</text>
      </svg>
      <figcaption>
        <div className="gauge-label">{label}</div>
        <div className="gauge-caption">{caption}</div>
      </figcaption>
    </figure>
  );
}
