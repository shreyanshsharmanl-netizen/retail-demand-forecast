import { describe, expect, it } from "vitest";
import { buildChart } from "./chart";

const days = [
  { forecast: 5, upper: 10, actual: 2 },
  { forecast: 6, upper: 8, actual: 4 },
];

describe("buildChart", () => {
  it("scales to the largest value", () => {
    const chart = buildChart(days, 200, 100, 10);
    expect(chart.top).toBe(10);
    expect(chart.y(10)).toBe(10);
    expect(chart.y(0)).toBe(90);
  });

  it("starts each path with a move command", () => {
    expect(buildChart(days, 200, 100).forecast.startsWith("M")).toBe(true);
  });

  it("does not divide by zero on all-zero data", () => {
    const chart = buildChart([{ forecast: 0, upper: 0, actual: 0 }], 200, 100);
    expect(Number.isFinite(chart.y(0))).toBe(true);
    expect(chart.actual).not.toContain("NaN");
  });
});
