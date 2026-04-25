import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import LineChart from './LineChart.svelte';
import type { ChartSeries } from './LineChart.svelte';

const now = 5000;
const windowMs = 5000;

function makeSeries(label: string, color: string, count: number): ChartSeries {
  const data = Array.from({ length: count }, (_, i) => ({
    t: now - (count - i) * 800,
    v: 10 + i * 5,
  }));
  return { label, color, data };
}

describe('LineChart', () => {
  it('renders one <path> per series that has enough data', () => {
    const series: ChartSeries[] = [makeSeries('A', 'teal', 5), makeSeries('B', 'red', 5)];
    const { html } = render(LineChart, { props: { series, windowMs, now } });
    const pathCount = (html.match(/<path/g) ?? []).length;
    expect(pathCount).toBe(2);
  });

  it('renders skeleton when series array is empty', () => {
    const { html } = render(LineChart, { props: { series: [], windowMs, now } });
    expect(html).toContain('skeleton-pulse');
    expect((html.match(/<path/g) ?? []).length).toBe(0);
  });

  it('renders skeleton when all series have fewer than 2 points', () => {
    const series: ChartSeries[] = [{ label: 'A', color: 'teal', data: [{ t: now, v: 10 }] }];
    const { html } = render(LineChart, { props: { series, windowMs, now } });
    expect(html).toContain('skeleton-pulse');
  });

  it('includes viewBox in SVG output', () => {
    const series: ChartSeries[] = [makeSeries('A', 'teal', 3)];
    const { html } = render(LineChart, { props: { series, windowMs, now } });
    expect(html).toContain('viewBox');
  });

  it('only renders paths with d attribute containing coordinates', () => {
    const series: ChartSeries[] = [
      makeSeries('good', 'teal', 5),
      { label: 'empty', color: 'red', data: [] },
    ];
    const { html } = render(LineChart, { props: { series, windowMs, now } });
    // Only the series with sufficient data should have a rendered path with coordinates
    const pathsWithCoords = (html.match(/<path[^>]+d="[ML][^"]+"/g) ?? []).length;
    expect(pathsWithCoords).toBe(1);
  });

  // Story 5.1c (scope-erweitert 2026-04-25): X-Achsen-Beschriftung
  it('renders the relative-time x-axis labels', () => {
    const series: ChartSeries[] = [makeSeries('A', 'teal', 5)];
    const { html } = render(LineChart, { props: { series, windowMs, now } });
    // Three ticks: oldest = "−5 s", middle = "−2.5 s", right = "jetzt".
    // Uses U+2212 (mathematical minus), not an ASCII hyphen.
    expect(html).toContain('−5 s');
    expect(html).toContain('−2.5 s');
    expect(html).toContain('jetzt');
  });

  it('formats integer time offsets without a decimal point', () => {
    const series: ChartSeries[] = [makeSeries('A', 'teal', 5)];
    const { html } = render(LineChart, { props: { series, windowMs: 10_000, now } });
    expect(html).toContain('−10 s');
    expect(html).toContain('−5 s');
    expect(html).not.toContain('−10.0 s');
  });
});
