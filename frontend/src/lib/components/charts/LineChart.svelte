<script lang="ts">
  export interface DataPoint {
    t: number;
    v: number;
  }

  export interface ChartSeries {
    label: string;
    data: DataPoint[];
    color: string;
  }

  interface Props {
    series: ChartSeries[];
    windowMs?: number;
    now: number;
  }

  let { series = [], windowMs = 5000, now }: Props = $props();

  const W = 400;
  const H = 160;
  const AXIS_H = 20;
  const TOTAL_H = H + AXIS_H;
  const PAD = 4;

  // Render the relative-time x-axis label. Uses U+2212 (mathematical minus)
  // for typographic consistency with the German UI strings.
  function formatTimeOffset(secondsAgo: number): string {
    if (secondsAgo <= 0) return 'jetzt';
    const rendered = Number.isInteger(secondsAgo) ? `${secondsAgo}` : secondsAgo.toFixed(1);
    return `−${rendered} s`;
  }

  function hasSufficientData(s: ChartSeries[]): boolean {
    return s.some((serie) => serie.data.length >= 2);
  }

  function yRange(s: ChartSeries[], cutoff: number): { min: number; max: number } {
    let min = Infinity;
    let max = -Infinity;
    for (const serie of s) {
      for (const p of serie.data) {
        if (p.t < cutoff) continue;
        if (p.v < min) min = p.v;
        if (p.v > max) max = p.v;
      }
    }
    if (!isFinite(min)) return { min: 0, max: 100 };
    if (min === max) return { min: min - 10, max: max + 10 };
    return { min, max };
  }

  function buildPath(points: DataPoint[], cutoff: number, yMin: number, yMax: number): string {
    const visible = points.filter((p) => p.t >= cutoff && p.t <= now);
    if (visible.length < 2) return '';
    const xRange = windowMs || 1;
    const ySpan = yMax - yMin || 1;
    return visible
      .map((p, i) => {
        const x = PAD + ((p.t - cutoff) / xRange) * (W - PAD * 2);
        const y = H - PAD - ((p.v - yMin) / ySpan) * (H - PAD * 2);
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  let showSkeleton = $derived(!hasSufficientData(series));
  let cutoff = $derived(now - windowMs);
  let range = $derived(yRange(series, cutoff));
  let paths = $derived(
    series.map((s) => ({
      d: buildPath(s.data, cutoff, range.min, range.max),
      color: s.color,
      label: s.label,
    })),
  );

  let axisTicks = $derived.by(() => {
    const totalSec = windowMs / 1000;
    return [
      { x: PAD, label: formatTimeOffset(totalSec), anchor: 'start' as const },
      {
        x: PAD + (W - PAD * 2) / 2,
        label: formatTimeOffset(totalSec / 2),
        anchor: 'middle' as const,
      },
      { x: W - PAD, label: formatTimeOffset(0), anchor: 'end' as const },
    ];
  });
</script>

{#if showSkeleton}
  <div class="chart-skeleton skeleton-pulse" style="height: {TOTAL_H}px; border-radius: 8px;"></div>
{:else}
  <svg
    viewBox="0 0 {W} {TOTAL_H}"
    class="line-chart"
    role="img"
    aria-label="Funktionstest Live-Daten"
  >
    {#each paths as p (p.label)}
      {#if p.d}
        <path
          d={p.d}
          fill="none"
          stroke={p.color}
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        ></path>
      {/if}
    {/each}
    <g class="x-axis" aria-hidden="true">
      <line x1={PAD} y1={H} x2={W - PAD} y2={H} class="axis-baseline"></line>
      {#each axisTicks as tick (tick.label)}
        <line x1={tick.x} y1={H} x2={tick.x} y2={H + 3} class="axis-tick"></line>
        <text x={tick.x} y={H + 13} text-anchor={tick.anchor} class="axis-label">
          {tick.label}
        </text>
      {/each}
    </g>
  </svg>
{/if}

<style>
  .line-chart {
    width: 100%;
    height: auto;
    display: block;
  }

  .axis-baseline {
    stroke: color-mix(in srgb, var(--color-text) 12%, transparent);
    stroke-width: 1;
  }

  .axis-tick {
    stroke: color-mix(in srgb, var(--color-text) 22%, transparent);
    stroke-width: 1;
  }

  .axis-label {
    font-size: 9px;
    fill: var(--color-text-secondary);
    font-family: inherit;
  }

  .chart-skeleton {
    width: 100%;
    background: linear-gradient(
      90deg,
      var(--color-surface) 25%,
      color-mix(in srgb, var(--color-surface) 70%, var(--color-text) 30%) 50%,
      var(--color-surface) 75%
    );
    background-size: 200% 100%;
    animation: chart-pulse 1.4s ease-in-out infinite;
  }

  @keyframes chart-pulse {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }
</style>
