<script lang="ts" module>
  // Shared formatter — exported so the surrounding view (Running.svelte) can
  // render legend values in the same units the chart's Y-axis uses.
  export function formatWatts(v: number): string {
    if (!Number.isFinite(v)) return '—';
    const abs = Math.abs(v);
    if (abs >= 1000) {
      const kw = v / 1000;
      // One decimal up to 9.9 kW, then drop the decimal for readability.
      const rendered = Math.abs(kw) >= 10 ? kw.toFixed(0) : kw.toFixed(1);
      return `${rendered} kW`;
    }
    return `${Math.round(v)} W`;
  }
</script>

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

  // Plot-area + chrome geometry. LEFT_PAD reserves room for Y-axis labels,
  // AXIS_H for the bottom time-axis, RIGHT/TOP/BOTTOM keep the line from
  // touching the frame. Coordinates are SVG-internal viewBox units.
  const W = 400;
  const H = 160;
  const AXIS_H = 20;
  const LEFT_PAD = 44;
  const RIGHT_PAD = 8;
  const TOP_PAD = 8;
  const BOTTOM_PAD = 4;
  const TOTAL_H = H + AXIS_H;
  const PLOT_TOP = TOP_PAD;
  const PLOT_BOTTOM = H - BOTTOM_PAD;

  // U+2212 (mathematical minus) for typographic consistency with German UI.
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

  // Map a value in W to its Y coordinate inside the plot area.
  function yCoord(v: number, yMin: number, yMax: number): number {
    const span = yMax - yMin || 1;
    return PLOT_BOTTOM - ((v - yMin) / span) * (PLOT_BOTTOM - PLOT_TOP);
  }

  function buildPath(points: DataPoint[], cutoff: number, yMin: number, yMax: number): string {
    const visible = points.filter((p) => p.t >= cutoff && p.t <= now);
    if (visible.length < 2) return '';
    const xRange = windowMs || 1;
    const plotWidth = W - LEFT_PAD - RIGHT_PAD;
    return visible
      .map((p, i) => {
        const x = LEFT_PAD + ((p.t - cutoff) / xRange) * plotWidth;
        const y = yCoord(p.v, yMin, yMax);
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

  let xAxisTicks = $derived.by(() => {
    const totalSec = windowMs / 1000;
    return [
      { x: LEFT_PAD, label: formatTimeOffset(totalSec), anchor: 'start' as const },
      {
        x: LEFT_PAD + (W - LEFT_PAD - RIGHT_PAD) / 2,
        label: formatTimeOffset(totalSec / 2),
        anchor: 'middle' as const,
      },
      { x: W - RIGHT_PAD, label: formatTimeOffset(0), anchor: 'end' as const },
    ];
  });

  // Y-axis: three ticks at min / mid / max. Mid is the arithmetic average
  // of the visible value range so labels stay aligned with the plot edges
  // and grid lines never crowd the data.
  let yAxisTicks = $derived.by(() => {
    const { min, max } = range;
    const mid = (min + max) / 2;
    return [
      { v: max, y: yCoord(max, min, max) },
      { v: mid, y: yCoord(mid, min, max) },
      { v: min, y: yCoord(min, min, max) },
    ];
  });

  // Draw a dedicated zero-line whenever the visible range crosses zero —
  // it tells the user instantly when the grid swings between import (>0)
  // and export (<0). Suppressed when zero is already on a tick edge.
  let zeroLineY = $derived.by(() => {
    const { min, max } = range;
    if (min >= 0 || max <= 0) return null;
    return yCoord(0, min, max);
  });
</script>

{#if showSkeleton}
  <div class="chart-skeleton skeleton-pulse" style="height: {TOTAL_H}px; border-radius: 8px;"></div>
{:else}
  <svg viewBox="0 0 {W} {TOTAL_H}" class="line-chart" role="img" aria-label="Live-Daten Diagramm">
    <g class="grid" aria-hidden="true">
      {#each yAxisTicks as tick (tick.v)}
        <line x1={LEFT_PAD} y1={tick.y} x2={W - RIGHT_PAD} y2={tick.y} class="grid-line"></line>
      {/each}
      {#if zeroLineY !== null}
        <line x1={LEFT_PAD} y1={zeroLineY} x2={W - RIGHT_PAD} y2={zeroLineY} class="zero-line"
        ></line>
      {/if}
    </g>
    <g class="y-axis" aria-hidden="true">
      {#each yAxisTicks as tick (tick.v)}
        <text x={LEFT_PAD - 6} y={tick.y + 3} text-anchor="end" class="axis-label">
          {formatWatts(tick.v)}
        </text>
      {/each}
    </g>
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
      <line x1={LEFT_PAD} y1={H} x2={W - RIGHT_PAD} y2={H} class="axis-baseline"></line>
      {#each xAxisTicks as tick (tick.label)}
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

  .grid-line {
    stroke: color-mix(in srgb, var(--color-text) 6%, transparent);
    stroke-width: 1;
    stroke-dasharray: 2 3;
  }

  .zero-line {
    stroke: color-mix(in srgb, var(--color-text) 24%, transparent);
    stroke-width: 1;
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
