import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
    test: {
        environment: 'jsdom',
        globals: true,
        include: ['**/*.test.ts'],
        setupFiles: ['./setup.ts'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            include: ['../frontend/src/lib/**/*.ts'],
            exclude: ['**/*.test.ts', '**/*.d.ts'],
        },
    },
    resolve: {
        alias: {
            '$lib': resolve(__dirname, '../frontend/src/lib'),
        },
    },
});
