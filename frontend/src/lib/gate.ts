import type { DeviceResponse } from './api/types.js';

// Routes that belong to the commissioning wizard. A commissioned user hitting
// any of these must be bounced to `/running`, including direct URL hits that
// would otherwise let them re-fire commissioning. (Story 2.3 Review P1, Story
// 2.3a AC 7.)
const WIZARD_ROUTES = new Set<string>([
  '/',
  '/disclaimer',
  '/activate',
  '/functional-test',
  '/config',
]);

export type GateDecision =
  | { kind: 'stay' }
  | { kind: 'redirect'; hash: `#${string}` };

export interface GateInput {
  currentRoute: string;
  devices: DeviceResponse[] | null;
  preAccepted: boolean;
  // true on the initial device-fetch resolve; false on subsequent hashchange
  // evaluations so a user who deliberately navigates back to `/` is not
  // yanked forward against their intent.
  allowAutoForward: boolean;
}

export function evaluateGate(input: GateInput): GateDecision {
  const { currentRoute, devices, preAccepted, allowAutoForward } = input;
  if (devices === null) return { kind: 'stay' };

  const allCommissioned =
    devices.length > 0 && devices.every((d) => d.commissioned_at !== null);
  if (allCommissioned) {
    if (WIZARD_ROUTES.has(currentRoute)) {
      return { kind: 'redirect', hash: '#/running' };
    }
    return { kind: 'stay' };
  }

  if (!preAccepted && currentRoute !== '/disclaimer') {
    return { kind: 'redirect', hash: '#/disclaimer' };
  }
  if (!preAccepted) return { kind: 'stay' };
  if (devices.length === 0) return { kind: 'stay' };
  if (!allowAutoForward) return { kind: 'stay' };
  if (currentRoute !== '/') return { kind: 'stay' };
  return { kind: 'redirect', hash: '#/functional-test' };
}
