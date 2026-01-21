/**
 * Toast notification store
 * Provides a simple way to show temporary notification messages
 */

import { writable } from 'svelte/store';

export type ToastType = 'error' | 'warning' | 'info' | 'success';

export interface ToastMessage {
    id: string;
    type: ToastType;
    message: string;
    duration: number;
    createdAt: number;
}

function createToastStore() {
    const { subscribe, update } = writable<ToastMessage[]>([]);

    return {
        subscribe,

        /**
         * Show a toast notification
         * @param message The message to display
         * @param type The type of toast (error, warning, info, success)
         * @param duration How long to show the toast in milliseconds (default: 3000)
         * @returns The toast ID (can be used to dismiss early)
         */
        show(message: string, type: ToastType = 'info', duration: number = 3000): string {
            const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

            const toast: ToastMessage = {
                id,
                type,
                message,
                duration,
                createdAt: Date.now(),
            };

            update(toasts => [...toasts, toast]);

            // Auto-remove after duration
            setTimeout(() => {
                update(toasts => toasts.filter(t => t.id !== id));
            }, duration);

            return id;
        },

        /**
         * Dismiss a specific toast by ID
         */
        dismiss(id: string) {
            update(toasts => toasts.filter(t => t.id !== id));
        },

        /**
         * Clear all toasts
         */
        clear() {
            update(() => []);
        },

        // Convenience methods
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

export const toastStore = createToastStore();
