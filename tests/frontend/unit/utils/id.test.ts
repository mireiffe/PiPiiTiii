/**
 * Tests for frontend/src/lib/utils/id.ts
 *
 * Tests ID generation utilities.
 */

import { describe, it, expect } from 'vitest';
import { generateId, createId } from '$lib/utils/id';

describe('generateId', () => {
    it('should generate id with given prefix', () => {
        const id = generateId('test');
        expect(id).toMatch(/^test_\d+_[a-z0-9]+$/);
    });

    it('should generate unique ids', () => {
        const ids = new Set<string>();
        for (let i = 0; i < 100; i++) {
            ids.add(generateId('unique'));
        }
        expect(ids.size).toBe(100);
    });

    it('should include timestamp in id', () => {
        const before = Date.now();
        const id = generateId('time');
        const after = Date.now();

        const parts = id.split('_');
        const timestamp = parseInt(parts[1], 10);

        expect(timestamp).toBeGreaterThanOrEqual(before);
        expect(timestamp).toBeLessThanOrEqual(after);
    });

    it('should include random suffix', () => {
        const id = generateId('rand');
        const parts = id.split('_');

        // Random part should be 7 characters of alphanumeric
        expect(parts[2]).toMatch(/^[a-z0-9]{7}$/);
    });
});

describe('createId', () => {
    describe('evidence', () => {
        it('should generate evidence id', () => {
            const id = createId.evidence();
            expect(id).toMatch(/^ev_\d+_[a-z0-9]+$/);
        });
    });

    describe('causeImage', () => {
        it('should generate cause image id', () => {
            const id = createId.causeImage();
            expect(id).toMatch(/^cimg_\d+_[a-z0-9]+$/);
        });
    });

    describe('actionCapture', () => {
        it('should generate action capture id', () => {
            const id = createId.actionCapture();
            expect(id).toMatch(/^acap_\d+_[a-z0-9]+$/);
        });
    });

    describe('coreStep', () => {
        it('should generate core step id', () => {
            const id = createId.coreStep();
            expect(id).toMatch(/^cs_\d+_[a-z0-9]+$/);
        });
    });

    describe('coreStepPreset', () => {
        it('should generate core step preset id', () => {
            const id = createId.coreStepPreset();
            expect(id).toMatch(/^csp_\d+_[a-z0-9]+$/);
        });
    });

    describe('coreStepInstance', () => {
        it('should generate core step instance id', () => {
            const id = createId.coreStepInstance();
            expect(id).toMatch(/^csi_\d+_[a-z0-9]+$/);
        });
    });

    describe('phase', () => {
        it('should generate phase id', () => {
            const id = createId.phase();
            expect(id).toMatch(/^phase_\d+_[a-z0-9]+$/);
        });
    });

    describe('support', () => {
        it('should generate support id', () => {
            const id = createId.support();
            expect(id).toMatch(/^support_\d+_[a-z0-9]+$/);
        });
    });

    describe('stepInstance', () => {
        it('should generate step instance id', () => {
            const id = createId.stepInstance();
            expect(id).toMatch(/^step_\d+_[a-z0-9]+$/);
        });
    });

    describe('stepCapture', () => {
        it('should generate step capture id', () => {
            const id = createId.stepCapture();
            expect(id).toMatch(/^scap_\d+_[a-z0-9]+$/);
        });
    });

    describe('attachment', () => {
        it('should generate attachment id', () => {
            const id = createId.attachment();
            expect(id).toMatch(/^att_\d+_[a-z0-9]+$/);
        });
    });

    describe('workflow', () => {
        it('should generate workflow id', () => {
            const id = createId.workflow();
            expect(id).toMatch(/^wf_\d+_[a-z0-9]+$/);
        });
    });

    describe('row', () => {
        it('should generate row id', () => {
            const id = createId.row();
            expect(id).toMatch(/^row_\d+_[a-z0-9]+$/);
        });
    });
});
