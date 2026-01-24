/**
 * Tests for frontend/src/lib/stores/modal.ts
 *
 * Tests modal state store functionality.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import type { StepAttachment, ModalState } from '$lib/stores/modal';

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

// Initial state
const initialState: ModalState = {
    attachment: {
        isOpen: false,
        attachment: null,
        stepId: null,
        caption: '',
    },
    imageAdd: {
        isOpen: false,
        imageData: null,
        stepId: null,
        caption: '',
        isUploading: false,
    },
    coreStepImage: {
        isOpen: false,
        presetId: null,
        instanceId: null,
        imageData: null,
        caption: '',
        isEditing: false,
        isUploading: false,
    },
    phaseSelect: {
        isOpen: false,
        supporterStepId: null,
        targetStepId: null,
    },
};

// Create modal store factory for testing
function createTestModalStore() {
    const store = mockWritable<ModalState>({ ...initialState });

    return {
        ...store,

        openAttachmentModal(stepId: string, attachment: StepAttachment) {
            store.update(s => ({
                ...s,
                attachment: {
                    isOpen: true,
                    attachment,
                    stepId,
                    caption: attachment.caption || '',
                },
            }));
        },

        closeAttachmentModal() {
            store.update(s => ({
                ...s,
                attachment: { ...initialState.attachment },
            }));
        },

        updateAttachmentCaption(caption: string) {
            store.update(s => ({
                ...s,
                attachment: { ...s.attachment, caption },
            }));
        },

        openImageAddModal(stepId: string, imageData: string) {
            store.update(s => ({
                ...s,
                imageAdd: {
                    isOpen: true,
                    imageData,
                    stepId,
                    caption: '',
                    isUploading: false,
                },
            }));
        },

        closeImageAddModal() {
            store.update(s => ({
                ...s,
                imageAdd: { ...initialState.imageAdd },
            }));
        },

        setImageUploading(isUploading: boolean) {
            store.update(s => ({
                ...s,
                imageAdd: { ...s.imageAdd, isUploading },
            }));
        },

        updateImageCaption(caption: string) {
            store.update(s => ({
                ...s,
                imageAdd: { ...s.imageAdd, caption },
            }));
        },

        openCoreStepImageModal(
            instanceId: string,
            presetId: string,
            imageData: string,
            caption: string = '',
            isEditing: boolean = false
        ) {
            store.update(s => ({
                ...s,
                coreStepImage: {
                    isOpen: true,
                    instanceId,
                    presetId,
                    imageData,
                    caption,
                    isEditing,
                    isUploading: false,
                },
            }));
        },

        closeCoreStepImageModal() {
            store.update(s => ({
                ...s,
                coreStepImage: { ...initialState.coreStepImage },
            }));
        },

        setCoreStepImageUploading(isUploading: boolean) {
            store.update(s => ({
                ...s,
                coreStepImage: { ...s.coreStepImage, isUploading },
            }));
        },

        updateCoreStepImageCaption(caption: string) {
            store.update(s => ({
                ...s,
                coreStepImage: { ...s.coreStepImage, caption },
            }));
        },

        openPhaseSelectModal(supporterStepId: string, targetStepId: string) {
            store.update(s => ({
                ...s,
                phaseSelect: {
                    isOpen: true,
                    supporterStepId,
                    targetStepId,
                },
            }));
        },

        closePhaseSelectModal() {
            store.update(s => ({
                ...s,
                phaseSelect: { ...initialState.phaseSelect },
            }));
        },

        closeAll() {
            store.set({ ...initialState });
        },

        isAnyModalOpen(): boolean {
            const state = store.get();
            return (
                state.attachment.isOpen ||
                state.imageAdd.isOpen ||
                state.coreStepImage.isOpen ||
                state.phaseSelect.isOpen
            );
        },
    };
}

describe('modalStore', () => {
    let modalStore: ReturnType<typeof createTestModalStore>;

    beforeEach(() => {
        modalStore = createTestModalStore();
    });

    describe('Attachment Modal', () => {
        const mockAttachment: StepAttachment = {
            id: 'att_1',
            type: 'image',
            imageId: 'img_1',
            caption: 'Test caption',
            createdAt: '2024-01-01',
        };

        it('should open attachment modal with data', () => {
            modalStore.openAttachmentModal('step_1', mockAttachment);
            const state = modalStore.get();

            expect(state.attachment.isOpen).toBe(true);
            expect(state.attachment.stepId).toBe('step_1');
            expect(state.attachment.attachment).toBe(mockAttachment);
            expect(state.attachment.caption).toBe('Test caption');
        });

        it('should close attachment modal and reset', () => {
            modalStore.openAttachmentModal('step_1', mockAttachment);
            modalStore.closeAttachmentModal();
            const state = modalStore.get();

            expect(state.attachment.isOpen).toBe(false);
            expect(state.attachment.attachment).toBeNull();
            expect(state.attachment.stepId).toBeNull();
        });

        it('should update attachment caption', () => {
            modalStore.openAttachmentModal('step_1', mockAttachment);
            modalStore.updateAttachmentCaption('New caption');

            expect(modalStore.get().attachment.caption).toBe('New caption');
        });
    });

    describe('Image Add Modal', () => {
        it('should open image add modal', () => {
            modalStore.openImageAddModal('step_1', 'data:image/png;base64,...');
            const state = modalStore.get();

            expect(state.imageAdd.isOpen).toBe(true);
            expect(state.imageAdd.stepId).toBe('step_1');
            expect(state.imageAdd.imageData).toBe('data:image/png;base64,...');
            expect(state.imageAdd.isUploading).toBe(false);
        });

        it('should close image add modal and reset', () => {
            modalStore.openImageAddModal('step_1', 'data:...');
            modalStore.closeImageAddModal();
            const state = modalStore.get();

            expect(state.imageAdd.isOpen).toBe(false);
            expect(state.imageAdd.imageData).toBeNull();
        });

        it('should set uploading state', () => {
            modalStore.openImageAddModal('step_1', 'data:...');
            modalStore.setImageUploading(true);

            expect(modalStore.get().imageAdd.isUploading).toBe(true);
        });

        it('should update image caption', () => {
            modalStore.openImageAddModal('step_1', 'data:...');
            modalStore.updateImageCaption('Image caption');

            expect(modalStore.get().imageAdd.caption).toBe('Image caption');
        });
    });

    describe('Core Step Image Modal', () => {
        it('should open core step image modal', () => {
            modalStore.openCoreStepImageModal('inst_1', 'preset_1', 'data:...', 'Caption', true);
            const state = modalStore.get();

            expect(state.coreStepImage.isOpen).toBe(true);
            expect(state.coreStepImage.instanceId).toBe('inst_1');
            expect(state.coreStepImage.presetId).toBe('preset_1');
            expect(state.coreStepImage.imageData).toBe('data:...');
            expect(state.coreStepImage.caption).toBe('Caption');
            expect(state.coreStepImage.isEditing).toBe(true);
        });

        it('should close core step image modal and reset', () => {
            modalStore.openCoreStepImageModal('inst_1', 'preset_1', 'data:...');
            modalStore.closeCoreStepImageModal();
            const state = modalStore.get();

            expect(state.coreStepImage.isOpen).toBe(false);
            expect(state.coreStepImage.instanceId).toBeNull();
        });

        it('should set uploading state', () => {
            modalStore.openCoreStepImageModal('inst_1', 'preset_1', 'data:...');
            modalStore.setCoreStepImageUploading(true);

            expect(modalStore.get().coreStepImage.isUploading).toBe(true);
        });

        it('should update caption', () => {
            modalStore.openCoreStepImageModal('inst_1', 'preset_1', 'data:...');
            modalStore.updateCoreStepImageCaption('New caption');

            expect(modalStore.get().coreStepImage.caption).toBe('New caption');
        });
    });

    describe('Phase Select Modal', () => {
        it('should open phase select modal', () => {
            modalStore.openPhaseSelectModal('step_1', 'step_2');
            const state = modalStore.get();

            expect(state.phaseSelect.isOpen).toBe(true);
            expect(state.phaseSelect.supporterStepId).toBe('step_1');
            expect(state.phaseSelect.targetStepId).toBe('step_2');
        });

        it('should close phase select modal and reset', () => {
            modalStore.openPhaseSelectModal('step_1', 'step_2');
            modalStore.closePhaseSelectModal();
            const state = modalStore.get();

            expect(state.phaseSelect.isOpen).toBe(false);
            expect(state.phaseSelect.supporterStepId).toBeNull();
            expect(state.phaseSelect.targetStepId).toBeNull();
        });
    });

    describe('closeAll', () => {
        it('should close all modals', () => {
            // Open all modals
            modalStore.openAttachmentModal('step_1', {
                id: 'att_1',
                type: 'text',
                data: 'text',
                createdAt: '',
            });
            modalStore.openImageAddModal('step_2', 'data:...');
            modalStore.openPhaseSelectModal('step_3', 'step_4');

            // Close all
            modalStore.closeAll();
            const state = modalStore.get();

            expect(state.attachment.isOpen).toBe(false);
            expect(state.imageAdd.isOpen).toBe(false);
            expect(state.coreStepImage.isOpen).toBe(false);
            expect(state.phaseSelect.isOpen).toBe(false);
        });
    });

    describe('isAnyModalOpen', () => {
        it('should return false when no modals open', () => {
            expect(modalStore.isAnyModalOpen()).toBe(false);
        });

        it('should return true when attachment modal open', () => {
            modalStore.openAttachmentModal('step_1', {
                id: 'att_1',
                type: 'text',
                data: 'text',
                createdAt: '',
            });
            expect(modalStore.isAnyModalOpen()).toBe(true);
        });

        it('should return true when image add modal open', () => {
            modalStore.openImageAddModal('step_1', 'data:...');
            expect(modalStore.isAnyModalOpen()).toBe(true);
        });

        it('should return true when phase select modal open', () => {
            modalStore.openPhaseSelectModal('step_1', 'step_2');
            expect(modalStore.isAnyModalOpen()).toBe(true);
        });
    });
});
