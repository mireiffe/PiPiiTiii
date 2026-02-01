import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

export default defineConfig({
    plugins: [
        svelte({
            hot: false,
            compilerOptions: {
                // Svelte 5 requires this for testing
                hmr: false,
            },
        }),
    ],
    test: {
        include: ['src/**/*.{test,spec}.{js,ts}'],
        environment: 'jsdom',
        globals: true,
        setupFiles: ['src/setupTest.ts'],
        alias: {
            '$lib': new URL('./src/lib', import.meta.url).pathname,
            '$app/environment': new URL('./src/mocks/app/environment.ts', import.meta.url).pathname,
            '$app/navigation': new URL('./src/mocks/app/navigation.ts', import.meta.url).pathname,
            '$app/stores': new URL('./src/mocks/app/stores.ts', import.meta.url).pathname,
        },
    },
    resolve: {
        conditions: ['browser'],
    },
});
