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
  const PAD = 4;

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

  function buildPath(
    points: DataPoint[],
    cutoff: number,
    yMin: number,
    yMax: number,
  ): string {
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
</script>

{#if showSkeleton}
  <div class="chart-skeleton skeleton-pulse" style="height: {H}px; border-radius: 8px;"></div>
{:else}
  <svg
    viewBox="0 0 {W} {H}"
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
        />
      {/if}
    {/each}
  </svg>
{/if}

<style>
  .line-chart {
    width: 100%;
    height: auto;
    display: block;
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
