const TZ = 'America/New_York';

// Event dates are stored as calendar dates; format them in UTC so they never shift a day.
export const fmt = (d: Date, opts: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', ...opts }).format(d);

export function dateRange(start: Date, end?: Date) {
  const s = fmt(start, { weekday: 'short', month: 'short', day: 'numeric' });
  if (!end || end.getTime() === start.getTime()) return s;
  return `${s} – ${fmt(end, { weekday: 'short', month: 'short', day: 'numeric' })}`;
}

// "Today" in Saratoga, as a UTC-midnight date comparable with event dates.
export function todayInSaratoga() {
  const iso = new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date());
  return new Date(`${iso}T00:00:00Z`);
}
