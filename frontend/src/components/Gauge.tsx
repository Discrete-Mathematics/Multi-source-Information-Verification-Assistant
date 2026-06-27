import { credColor } from "../labels";

// Semicircular credibility gauge (0-100).
export function Gauge({ value, size = 180 }: { value: number; size?: number }) {
  const r = size / 2 - 14;
  const cx = size / 2;
  const cy = size / 2;
  const circ = Math.PI * r; // half circle
  const frac = Math.max(0, Math.min(100, value)) / 100;
  const color = credColor(value);

  return (
    <div className="gauge" style={{ width: size, height: size / 2 + 30 }}>
      <svg width={size} height={size / 2 + 16}>
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#1e293b"
          strokeWidth={14}
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={14}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - frac)}
          style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.4s" }}
        />
      </svg>
      <div className="gauge-value" style={{ color }}>
        {value.toFixed(0)}
        <span className="gauge-unit">/100</span>
      </div>
    </div>
  );
}
