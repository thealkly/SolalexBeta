// @vitest-environment happy-dom
import { describe, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import Config from './routes/Config.svelte';
import * as client from './lib/api/client.js';

describe('debug', () => {
  it('check select bind via change-bubbles', async () => {
    vi.spyOn(client, 'getEntities').mockResolvedValue({
      wr_limit_entities: [{ entity_id: 'input_number.x', friendly_name: 'X' }],
      power_entities: [{ entity_id: 'sensor.foo', friendly_name: 'F' }],
      soc_entities: [],
    });
    vi.spyOn(client, 'fetchControlMode').mockRejectedValue(new Error('no'));
    vi.spyOn(client, 'getEntityState').mockResolvedValue({ entity_id: 'sensor.foo', value_w: 100, ts: null });
    const { container } = render(Config);
    await new Promise(r => setTimeout(r, 800));
    const tiles = container.querySelectorAll('button.type-tile');
    await fireEvent.click(tiles[0]!);
    await new Promise(r => setTimeout(r, 100));
    const wrSel = container.querySelectorAll('select')[0]! as HTMLSelectElement;
    
    // Try simulating user select via the option element
    const option = Array.from(wrSel.options).find(o => o.value === 'input_number.x')!;
    option.selected = true;
    wrSel.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(r => setTimeout(r, 100));
    console.log('AFTER OPTION-CLICK PATH wrSel.value:', wrSel.value);
    
    // Check if WR-Limit-Bereich field sees the update
    const limitInputs = container.querySelectorAll('input[type=number]');
    console.log('NUMBER INPUTS:', limitInputs.length);
    
    // Click smart meter
    const cbs = container.querySelectorAll('input[type=checkbox]');
    await fireEvent.click(cbs[0]!);
    await new Promise(r => setTimeout(r, 100));
    
    const meterSel = container.querySelectorAll('select')[1]! as HTMLSelectElement;
    const meterOpt = Array.from(meterSel.options).find(o => o.value === 'sensor.foo')!;
    meterOpt.selected = true;
    meterSel.dispatchEvent(new Event('change', { bubbles: true }));
    await new Promise(r => setTimeout(r, 100));
    
    const lpc = container.querySelector('[data-testid="live-preview-card"]');
    console.log('LIVE-PREVIEW-CARD:', lpc ? 'FOUND' : 'MISSING');
  });
});
