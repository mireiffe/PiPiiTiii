/**
 * Modal State Store
 *
 * Centralized modal state management.
 * Handles all modal visibility and data across the application.
 */

import { writable, derived } from 'svelte/store';
import type { StepAttachment } from '$lib/types/workflow';

// ========== Types ==========

export interface AttachmentModalState {
    isOpen: boolean;
    attachment: StepAttachment | null;
    stepId: string | null;
    caption: string;
}

export interface ImageAddModalState {
    isOpen: boolean;
    imageData: string | null;
    stepId: string | null;
    caption: string;
    isUploading: boolean;
}

export interface CoreStepImageModalState {
    isOpen: boolean;
    presetId: string | null;
    instanceId: string | null;
    imageData: string | null;
    caption: string;
    isEditing: boolean;
    isUploading: boolean;
}

export interface PhaseSelectModalState {
    isOpen: boolean;
    supporterStepId: string | null;
    targetStepId: string | null;
}

export interface ModalState {
    attachment: AttachmentModalState;
    imageAdd: ImageAddModalState;
    coreStepImage: CoreStepImageModalState;
    phaseSelect: PhaseSelectModalState;
}

// ========== Initial State ==========

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

// ========== Store Factory ==========

function createModalStore() {
    const { subscribe, set, update } = writable<ModalState>(initialState);

    return {
        subscribe,
        set,
        update,

        // ========== Attachment Modal ==========
        openAttachmentModal(stepId: string, attachment: StepAttachment) {
            update(s => ({
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
            update(s => ({
                ...s,
                attachment: initialState.attachment,
            }));
        },

        updateAttachmentCaption(caption: string) {
            update(s => ({
                ...s,
                attachment: { ...s.attachment, caption },
            }));
        },

        // ========== Image Add Modal ==========
        openImageAddModal(stepId: string, imageData: string) {
            update(s => ({
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
            update(s => ({
                ...s,
                imageAdd: initialState.imageAdd,
            }));
        },

        setImageUploading(isUploading: boolean) {
            update(s => ({
                ...s,
                imageAdd: { ...s.imageAdd, isUploading },
            }));
        },

        updateImageCaption(caption: string) {
            update(s => ({
                ...s,
                imageAdd: { ...s.imageAdd, caption },
            }));
        },

        // ========== Core Step Image Modal ==========
        openCoreStepImageModal(
            instanceId: string,
            presetId: string,
            imageData: string,
            caption: string = '',
            isEditing: boolean = false
        ) {
            update(s => ({
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
            update(s => ({
                ...s,
                coreStepImage: initialState.coreStepImage,
            }));
        },

        setCoreStepImageUploading(isUploading: boolean) {
            update(s => ({
                ...s,
                coreStepImage: { ...s.coreStepImage, isUploading },
            }));
        },

        updateCoreStepImageCaption(caption: string) {
            update(s => ({
                ...s,
                coreStepImage: { ...s.coreStepImage, caption },
            }));
        },

        // ========== Phase Select Modal ==========
        openPhaseSelectModal(supporterStepId: string, targetStepId: string) {
            update(s => ({
                ...s,
                phaseSelect: {
                    isOpen: true,
                    supporterStepId,
                    targetStepId,
                },
            }));
        },

        closePhaseSelectModal() {
            update(s => ({
                ...s,
                phaseSelect: initialState.phaseSelect,
            }));
        },

        // ========== Close All ==========
        closeAll() {
            set(initialState);
        },
    };
}

// ========== Singleton Instance ==========

export const modalStore = createModalStore();

// ========== Derived Stores ==========

export const isAnyModalOpen = derived(
    modalStore,
    ($modal) =>
        $modal.attachment.isOpen ||
        $modal.imageAdd.isOpen ||
        $modal.coreStepImage.isOpen ||
        $modal.phaseSelect.isOpen
);
