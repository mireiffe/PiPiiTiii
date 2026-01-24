/**
 * UI State Store
 *
 * Centralized UI state management for viewer-related states.
 * Handles selection, capture mode, expanded states, drag-drop, etc.
 */

import { writable, derived } from 'svelte/store';

// ========== Types ==========

export type DragMode = 'reorder' | 'support' | null;

export interface DragDropState {
    draggedIndex: number | null;
    dropTargetIndex: number | null;
    mode: DragMode;
    supportGuideTargetStepId: string | null;
}

export interface SelectionState {
    selectedStepIds: Set<string>;
    lastClickedStepId: string | null;
    isSelectionModeActive: boolean;
}

export interface CaptureState {
    isActive: boolean;
    targetStepId: string | null;
    targetPresetId: string | null; // For core step captures
    targetInstanceId: string | null; // For core step captures
}

export interface ExpandedState {
    expandedStepId: string | null;
    expandedCoreStepId: string | null;
    addingAttachmentToStepId: string | null;
}

export interface PopupState {
    showAddStepPopup: boolean;
    showCoreStepSelector: boolean;
    showPhaseListPopup: boolean;
    showKeyStepLinkingWizard: boolean;
}

export interface UIState {
    dragDrop: DragDropState;
    selection: SelectionState;
    capture: CaptureState;
    expanded: ExpandedState;
    popup: PopupState;
    viewMode: 'list' | 'graph';
}

// ========== Initial State ==========

const initialDragDrop: DragDropState = {
    draggedIndex: null,
    dropTargetIndex: null,
    mode: null,
    supportGuideTargetStepId: null,
};

const initialSelection: SelectionState = {
    selectedStepIds: new Set(),
    lastClickedStepId: null,
    isSelectionModeActive: false,
};

const initialCapture: CaptureState = {
    isActive: false,
    targetStepId: null,
    targetPresetId: null,
    targetInstanceId: null,
};

const initialExpanded: ExpandedState = {
    expandedStepId: null,
    expandedCoreStepId: null,
    addingAttachmentToStepId: null,
};

const initialPopup: PopupState = {
    showAddStepPopup: false,
    showCoreStepSelector: false,
    showPhaseListPopup: false,
    showKeyStepLinkingWizard: false,
};

const initialState: UIState = {
    dragDrop: initialDragDrop,
    selection: initialSelection,
    capture: initialCapture,
    expanded: initialExpanded,
    popup: initialPopup,
    viewMode: 'list',
};

// ========== Store Factory ==========

function createUIStore() {
    const { subscribe, set, update } = writable<UIState>(initialState);

    return {
        subscribe,
        set,
        update,

        // ========== View Mode ==========
        setViewMode(mode: 'list' | 'graph') {
            update(s => ({ ...s, viewMode: mode }));
        },

        // ========== Drag & Drop ==========
        startDrag(index: number) {
            update(s => ({
                ...s,
                dragDrop: { ...s.dragDrop, draggedIndex: index },
            }));
        },

        setDropTarget(index: number | null) {
            update(s => ({
                ...s,
                dragDrop: { ...s.dragDrop, dropTargetIndex: index },
            }));
        },

        setDragMode(mode: DragMode) {
            update(s => ({
                ...s,
                dragDrop: { ...s.dragDrop, mode },
            }));
        },

        setSupportGuideTarget(stepId: string | null) {
            update(s => ({
                ...s,
                dragDrop: { ...s.dragDrop, supportGuideTargetStepId: stepId },
            }));
        },

        endDrag() {
            update(s => ({
                ...s,
                dragDrop: initialDragDrop,
            }));
        },

        // ========== Selection ==========
        toggleSelection(stepId: string, isCtrlKey: boolean = false, isShiftKey: boolean = false) {
            update(s => {
                const newSelectedIds = new Set(s.selection.selectedStepIds);

                if (isCtrlKey) {
                    if (newSelectedIds.has(stepId)) {
                        newSelectedIds.delete(stepId);
                    } else {
                        newSelectedIds.add(stepId);
                    }
                } else {
                    newSelectedIds.clear();
                    newSelectedIds.add(stepId);
                }

                return {
                    ...s,
                    selection: {
                        ...s.selection,
                        selectedStepIds: newSelectedIds,
                        lastClickedStepId: stepId,
                        isSelectionModeActive: newSelectedIds.size > 0,
                    },
                };
            });
        },

        selectRange(stepIds: string[], fromId: string, toId: string) {
            update(s => {
                const fromIndex = stepIds.indexOf(fromId);
                const toIndex = stepIds.indexOf(toId);
                if (fromIndex === -1 || toIndex === -1) return s;

                const start = Math.min(fromIndex, toIndex);
                const end = Math.max(fromIndex, toIndex);
                const newSelectedIds = new Set(s.selection.selectedStepIds);

                for (let i = start; i <= end; i++) {
                    newSelectedIds.add(stepIds[i]);
                }

                return {
                    ...s,
                    selection: {
                        ...s.selection,
                        selectedStepIds: newSelectedIds,
                        isSelectionModeActive: true,
                    },
                };
            });
        },

        selectAll(stepIds: string[]) {
            update(s => ({
                ...s,
                selection: {
                    ...s.selection,
                    selectedStepIds: new Set(stepIds),
                    isSelectionModeActive: true,
                },
            }));
        },

        clearSelection() {
            update(s => ({
                ...s,
                selection: initialSelection,
            }));
        },

        // ========== Capture ==========
        startCapture(stepId: string, presetId?: string, instanceId?: string) {
            update(s => ({
                ...s,
                capture: {
                    isActive: true,
                    targetStepId: stepId,
                    targetPresetId: presetId || null,
                    targetInstanceId: instanceId || null,
                },
            }));
        },

        stopCapture() {
            update(s => ({
                ...s,
                capture: initialCapture,
            }));
        },

        // ========== Expanded ==========
        toggleStepExpand(stepId: string) {
            update(s => ({
                ...s,
                expanded: {
                    ...s.expanded,
                    expandedStepId: s.expanded.expandedStepId === stepId ? null : stepId,
                    addingAttachmentToStepId: null,
                },
                capture: s.capture.isActive ? initialCapture : s.capture,
            }));
        },

        toggleCoreStepExpand(instanceId: string) {
            update(s => ({
                ...s,
                expanded: {
                    ...s.expanded,
                    expandedCoreStepId: s.expanded.expandedCoreStepId === instanceId ? null : instanceId,
                },
            }));
        },

        toggleAttachmentSection(stepId: string) {
            update(s => ({
                ...s,
                expanded: {
                    ...s.expanded,
                    addingAttachmentToStepId: s.expanded.addingAttachmentToStepId === stepId ? null : stepId,
                },
                capture: s.capture.isActive ? initialCapture : s.capture,
            }));
        },

        // ========== Popups ==========
        toggleAddStepPopup() {
            update(s => ({
                ...s,
                popup: {
                    ...s.popup,
                    showAddStepPopup: !s.popup.showAddStepPopup,
                    showCoreStepSelector: false,
                },
            }));
        },

        toggleCoreStepSelector() {
            update(s => ({
                ...s,
                popup: {
                    ...s.popup,
                    showCoreStepSelector: !s.popup.showCoreStepSelector,
                    showAddStepPopup: false,
                },
            }));
        },

        togglePhaseListPopup() {
            update(s => ({
                ...s,
                popup: {
                    ...s.popup,
                    showPhaseListPopup: !s.popup.showPhaseListPopup,
                },
            }));
        },

        closeAllPopups() {
            update(s => ({
                ...s,
                popup: initialPopup,
            }));
        },

        toggleKeyStepLinkingWizard(show?: boolean) {
            update(s => ({
                ...s,
                popup: {
                    ...s.popup,
                    showKeyStepLinkingWizard: show !== undefined ? show : !s.popup.showKeyStepLinkingWizard,
                },
            }));
        },

        // ========== Reset ==========
        reset() {
            set(initialState);
        },
    };
}

// ========== Singleton Instance ==========

export const uiStore = createUIStore();

// ========== Derived Stores ==========

export const isCapturing = derived(uiStore, ($ui) => $ui.capture.isActive);
export const selectedCount = derived(uiStore, ($ui) => $ui.selection.selectedStepIds.size);
export const isDragging = derived(uiStore, ($ui) => $ui.dragDrop.draggedIndex !== null);
