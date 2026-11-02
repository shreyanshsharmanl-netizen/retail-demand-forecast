/** Scale a daily forecast into SVG coordinates. */
export function buildChart(days, width, height, pad = 34) {
  const top = Math.max(1, ...days.flatMap((d) => [d.upper, d.actual, d.forecast]));
  const x = (i) => pad + (i * (width - 2 * pad)) / Math.max(days.length - 1, 1);
  const y = (v) => height - pad - (v / top) * (height - 2 * pad);
  const line = (key) => days.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(d[key]).toFixed(1)}`).join(" ");
  return { top, x, y, forecast: line("forecast"), actual: line("actual"), upper: line("upper") };
}
