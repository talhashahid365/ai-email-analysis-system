import React from 'react';

/** Shared look & feel for every Recharts chart in the app. */
export const AXIS_TICK = { fontSize: 11, fill: '#94a3b8' };
export const GRID_PROPS = { strokeDasharray: '3 6', stroke: '#cbd5e1', strokeOpacity: 0.35, vertical: false } as const;
export const CURSOR_LINE = { stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '4 4' };
export const LEGEND_PROPS = { iconType: 'circle' as const, iconSize: 8, wrapperStyle: { fontSize: 12, paddingTop: 10 } };

/** Soft top-to-bottom fade for area fills. Call as a function inside <AreaChart>, e.g. {gradientDefs({ a: '#4f46e5' })}. */
export function gradientDefs(colors: Record<string, string>, topOpacity = 0.35) {
  return (
    <defs>
      {Object.entries(colors).map(([id, color]) => (
        <linearGradient key={id} id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={topOpacity} />
          <stop offset="100%" stopColor={color} stopOpacity={0.02} />
        </linearGradient>
      ))}
    </defs>
  );
}

interface TooltipEntry { name?: string | number; value?: number | string; color?: string; payload?: any; dataKey?: string | number }

export function ChartTooltip({ active, payload, label, unit = '' }: {
  active?: boolean; payload?: TooltipEntry[]; label?: string | number; unit?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const title = label ?? payload[0]?.payload?.name ?? payload[0]?.name;
  return (
    <div className="min-w-[150px] rounded-xl border border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 px-3.5 py-2.5 shadow-xl backdrop-blur">
      {title !== undefined && title !== '' && (
        <div className="mb-1.5 text-xs font-bold text-slate-900 dark:text-white">{title}</div>
      )}
      <ul className="space-y-1">
        {payload.map((p, i) => (
          <li key={`${p.dataKey ?? p.name}-${i}`} className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color || p.payload?.fill }} />
              {p.name}
            </span>
            <span className="font-mono font-bold text-slate-900 dark:text-white">{p.value}{unit}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
