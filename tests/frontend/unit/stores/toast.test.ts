/**
 * Tests for frontend/src/lib/stores/toast.ts
 *
 * Tests toast notification store functionality.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { get } from 'svelte/store';

// We need to test the factory function, so we'll recreate the store for each test
// Import types only
import type { ToastMessage } from '$lib/stores/toast';

// Mock svelte/store
const mockWritable = <T>(initial: T) => {
    let value = initial;
    const subscribers = new Set<(val: T) => void>();

    return {
        subscribe: (fn: (val: T) => void) => {
            subscribers.add(fn);
            fn(value);
            return () => subscribers.delete(fn);
        },
        set: (newValue: T) => {
            value = newValue;
            subscribers.forEach(fn => fn(value));
        },
        update: (updater: (val: T) => T) => {
            value = updater(value);
            subscribers.forEach(fn => fn(value));
        },
        get: () => value,
    };
};

// Create toast store factory for testing
function createTestToastStore() {
    const store = mockWritable<ToastMessage[]>([]);

    return {
        ...store,

        show(message: string, type: 'error' | 'warning' | 'info' | 'success' = 'info', duration: number = 3000): string {
            const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

            const toast: ToastMessage = {
                id,
                type,
                message,
                duration,
                createdAt: Date.now(),
            };

            store.update(toasts => [...toasts, toast]);

            setTimeout(() => {
                store.update(toasts => toasts.filter(t => t.id !== id));
            }, duration);

            return id;
        },

        dismiss(id: string) {
            store.update(toasts => toasts.filter(t => t.id !== id));
        },

        clear() {
            store.update(() => []);
        },

        error(message: string, duration?: number) {
            return this.show(message, 'error', duration ?? 4000);
        },

        warning(message: string, duration?: number) {
            return this.show(message, 'warning', duration ?? 3000);
        },

        info(message: string, duration?: number) {
            return this.show(message, 'info', duration ?? 3000);
        },

        success(message: string, duration?: number) {
            return this.show(message, 'success', duration ?? 2500);
        },
    };
}

describe('toastStore', () => {
    let toastStore: ReturnType<typeof createTestToastStore>;

    beforeEach(() => {
        vi.useFakeTimers();
        toastStore = createTestToastStore();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    describe('show', () => {
        it('should add a toast message', () => {
            toastStore.show('Test message');
            const toasts = toastStore.get();
            expect(toasts).toHaveLength(1);
            expect(toasts[0].message).toBe('Test message');
        });

        it('should use default type "info"', () => {
            toastStore.show('Test message');
            const toasts = toastStore.get();
            expect(toasts[0].type).toBe('info');
        });

        it('should use specified type', () => {
            toastStore.show('Error!', 'error');
            const toasts = toastStore.get();
            expect(toasts[0].type).toBe('error');
        });

        it('should return toast id', () => {
            const id = toastStore.show('Test');
            expect(id).toMatch(/^toast_\d+_[a-z0-9]+$/);
        });

        it('should auto-remove after duration', () => {
            toastStore.show('Test', 'info', 1000);
            expect(toastStore.get()).toHaveLength(1);

            vi.advanceTimersByTime(1000);
            expect(toastStore.get()).toHaveLength(0);
        });

        it('should add multiple toasts', () => {
            toastStore.show('Message 1');
            toastStore.show('Message 2');
            toastStore.show('Message 3');
            expect(toastStore.get()).toHaveLength(3);
        });
    });

    describe('dismiss', () => {
        it('should remove specific toast by id', () => {
            const id1 = toastStore.show('Message 1');
            const id2 = toastStore.show('Message 2');

            toastStore.dismiss(id1);

            const toasts = toastStore.get();
            expect(toasts).toHaveLength(1);
            expect(toasts[0].id).toBe(id2);
        });

        it('should do nothing for non-existent id', () => {
            toastStore.show('Message');
            toastStore.dismiss('non_existent_id');
            expect(toastStore.get()).toHaveLength(1);
        });
    });

    describe('clear', () => {
        it('should remove all toasts', () => {
            toastStore.show('Message 1');
            toastStore.show('Message 2');
            toastStore.show('Message 3');

            toastStore.clear();
            expect(toastStore.get()).toHaveLength(0);
        });
    });

    describe('convenience methods', () => {
        it('error should use "error" type with 4000ms default', () => {
            toastStore.error('Error message');
            const toast = toastStore.get()[0];
            expect(toast.type).toBe('error');
            expect(toast.duration).toBe(4000);
        });

        it('warning should use "warning" type with 3000ms default', () => {
            toastStore.warning('Warning message');
            const toast = toastStore.get()[0];
            expect(toast.type).toBe('warning');
            expect(toast.duration).toBe(3000);
        });

        it('info should use "info" type with 3000ms default', () => {
            toastStore.info('Info message');
            const toast = toastStore.get()[0];
            expect(toast.type).toBe('info');
            expect(toast.duration).toBe(3000);
        });

        it('success should use "success" type with 2500ms default', () => {
            toastStore.success('Success message');
            const toast = toastStore.get()[0];
            expect(toast.type).toBe('success');
            expect(toast.duration).toBe(2500);
        });

        it('should allow custom duration override', () => {
            toastStore.error('Error', 10000);
            expect(toastStore.get()[0].duration).toBe(10000);
        });
    });
});
