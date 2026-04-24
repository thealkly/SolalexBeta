import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import PreSetupDisclaimer from './PreSetupDisclaimer.svelte';

// SSR renders multi-line prose with the template's indentation baked into the
// output. Collapse any whitespace run to a single space so assertions can
// match the verbatim spec copy regardless of line-break placement.
function normalize(html: string): string {
  return html.replace(/\s+/g, ' ');
}

describe('PreSetupDisclaimer — SSR initial state', () => {
  it('renders checkbox unchecked and no continue button in initial state', () => {
    const { html } = render(PreSetupDisclaimer, {});
    expect(html).toContain('type="checkbox"');
    // Button is gated behind `{#if checked}` — match distinctive class to avoid
    // colliding with future copy containing the word "Weiter".
    expect(html).not.toMatch(/<button[^>]*class="[^"]*continue-button/);
    expect(html).toContain('Bevor es losgeht');
  });

  it('contains all three required disclaimer paragraphs verbatim', () => {
    const { html } = render(PreSetupDisclaimer, {});
    const text = normalize(html);
    expect(text).toContain(
      'Solalex steuert deine PV-/Akku-/Verbraucherlogik über Home Assistant. Bitte aktiviere Solalex nur, wenn deine Anlage fachgerecht installiert ist und du sicher bist, dass die gewählten Entitäten, Grenzwerte und Geräte korrekt sind.',
    );
    expect(text).toContain(
      'Solalex ersetzt keine Elektrofachkraft, keine Anlagenprüfung und keinen Netzschutz. Die App darf nicht für sicherheitskritische Funktionen verwendet werden. Falsche Einstellungen, fehlerhafte Sensorwerte, instabile Verbindungen oder parallele Automationen können zu unerwünschtem Verhalten führen.',
    );
    expect(text).toContain(
      'Ich bestätige, dass ich für Installation, Konfiguration und Betrieb meiner Anlage selbst verantwortlich bin und Solalex nur innerhalb der zulässigen technischen und rechtlichen Grenzen verwende.',
    );
  });

  it('contains the checkbox label verbatim', () => {
    const { html } = render(PreSetupDisclaimer, {});
    const text = normalize(html);
    expect(text).toContain(
      'Ich habe die Sicherheitshinweise gelesen und verstanden. Ich bin für die korrekte Installation, Konfiguration und den sicheren Betrieb meiner Anlage selbst verantwortlich.',
    );
  });

  it('wires the checkbox to the disclaimer block via aria-describedby', () => {
    const { html } = render(PreSetupDisclaimer, {});
    expect(html).toMatch(/id="pre-disclaimer-text"/);
    expect(html).toMatch(/aria-describedby="pre-disclaimer-text"/);
  });

  it('does not render a disabled button (Anti-Pattern: disabled-state = ausblenden)', () => {
    const { html } = render(PreSetupDisclaimer, {});
    // No disabled attribute anywhere on a button — the component must hide
    // the button entirely instead of showing a greyed-out disabled variant.
    expect(html).not.toMatch(/<button[^>]*disabled/);
  });
});
