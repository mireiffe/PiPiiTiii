/**
 * Vitest setup file
 * Runs before all tests
 */

import { expect, vi } from 'vitest';

// Mock fetch globally
global.fetch = vi.fn();

// Reset mocks between tests
beforeEach(() => {
    vi.clearAllMocks();
});
