// The backend stores and returns UTC timestamps WITHOUT a "Z" (e.g. "2026-10-02T09:15:00").
// Browsers read such strings as local time, so every clock time looked hours off (5 h in Pakistan).
// These helpers treat them as UTC and show them in the viewer's own time zone.

const HAS_ZONE = /(Z|[+-]\d{2}:?\d{2})$/i;
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

export function parseUtc(value?: string | null): Date | null {
  if (!value) return null;
  const v = String(value).trim();
  const d = new Date(DATE_ONLY.test(v) || HAS_ZONE.test(v) ? v : `${v}Z`);
  return isNaN(d.getTime()) ? null : d;
}

export function fmtDateTime(value?: string | null, options?: Intl.DateTimeFormatOptions): string {
  const d = parseUtc(value);
  return d ? d.toLocaleString([], options) : '';
}

export function fmtTime(value?: string | null): string {
  const d = parseUtc(value);
  return d ? d.toLocaleTimeString() : '';
}

export function fmtDate(value?: string | null): string {
  const d = parseUtc(value);
  return d ? d.toLocaleDateString() : '';
}

export function timeValue(value?: string | null): number {
  const d = parseUtc(value);
  return d ? d.getTime() : 0;
}
