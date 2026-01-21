/**
 * Workflow State Store
 *
 * Centralized state management for workflow-related data.
 * Reduces prop drilling and simplifies component communication.
 */

import { writable, derived, type Readable } from 'svelte/store';
import type {
    ProjectWorkflowData,
    WorkflowStepInstance,
    CoreStepInstance,
    SupportRelation,
    PhaseType,
    LayoutRow,
} from '$lib/types/workflow';
import {
    createEmptyWorkflowData,
    getLayoutRows,
    isStepSupporter,
    addSupportRelation as addSupportRelationFn,
    removeSupportByStepId as removeSupportByStepIdFn,
    cleanupOrphanedSupports,
} from '$lib/types/workflow';

// ========== Types ==========

export interface WorkflowState {
    data: ProjectWorkflowData;
    activeWorkflowId: string | null;
    allWorkflowsData: Record<string, ProjectWorkflowData>;
    globalPhases: PhaseType[];
    saving: boolean;
}

// ========== Store Factory ==========

function createWorkflowStore() {
    const { subscribe, set, update } = writable<WorkflowState>({
        data: createEmptyWorkflowData(),
        activeWorkflowId: null,
        allWorkflowsData: {},
        globalPhases: [],
        saving: false,
    });

    return {
        subscribe,
        set,
        update,

        // Initialize with data
        init(state: Partial<WorkflowState>) {
            update(s => ({ ...s, ...state }));
        },

        // Set current workflow data
        setData(data: ProjectWorkflowData) {
            update(s => ({
                ...s,
                data,
                allWorkflowsData: s.activeWorkflowId
                    ? { ...s.allWorkflowsData, [s.activeWorkflowId]: data }
                    : s.allWorkflowsData,
            }));
        },

        // Switch active workflow
        setActiveWorkflow(workflowId: string) {
            update(s => ({
                ...s,
                activeWorkflowId: workflowId,
                data: s.allWorkflowsData[workflowId] || createEmptyWorkflowData(),
            }));
        },

        // Set saving state
        setSaving(saving: boolean) {
            update(s => ({ ...s, saving }));
        },

        // Set global phases
        setGlobalPhases(phases: PhaseType[]) {
            update(s => ({ ...s, globalPhases: phases }));
        },

        // Add support relation
        addSupport(supporterStepId: string, targetStepId: string, phaseId: string) {
            update(s => {
                const newData = addSupportRelationFn(s.data, supporterStepId, targetStepId, phaseId);
                return {
                    ...s,
                    data: newData,
                    allWorkflowsData: s.activeWorkflowId
                        ? { ...s.allWorkflowsData, [s.activeWorkflowId]: newData }
                        : s.allWorkflowsData,
                };
            });
        },

        // Remove support relation
        removeSupport(stepId: string) {
            update(s => {
                const newData = removeSupportByStepIdFn(s.data, stepId);
                return {
                    ...s,
                    data: newData,
                    allWorkflowsData: s.activeWorkflowId
                        ? { ...s.allWorkflowsData, [s.activeWorkflowId]: newData }
                        : s.allWorkflowsData,
                };
            });
        },

        // Update steps
        updateSteps(steps: WorkflowStepInstance[]) {
            update(s => {
                const updatedData: ProjectWorkflowData = { ...s.data, steps, updatedAt: new Date().toISOString() };
                const newData = cleanupOrphanedSupports(updatedData);
                return {
                    ...s,
                    data: newData,
                    allWorkflowsData: s.activeWorkflowId
                        ? { ...s.allWorkflowsData, [s.activeWorkflowId]: newData }
                        : s.allWorkflowsData,
                };
            });
        },

        // Update core step instances
        updateCoreStepInstances(instances: CoreStepInstance[]) {
            update(s => {
                const newData = { ...s.data, coreStepInstances: instances, updatedAt: new Date().toISOString() };
                return {
                    ...s,
                    data: newData,
                    allWorkflowsData: s.activeWorkflowId
                        ? { ...s.allWorkflowsData, [s.activeWorkflowId]: newData }
                        : s.allWorkflowsData,
                };
            });
        },

        // Reset workflow
        reset() {
            const emptyData = createEmptyWorkflowData();
            update(s => ({
                ...s,
                data: emptyData,
                allWorkflowsData: s.activeWorkflowId
                    ? { ...s.allWorkflowsData, [s.activeWorkflowId]: emptyData }
                    : s.allWorkflowsData,
            }));
        },
    };
}

// ========== Singleton Instance ==========

export const workflowStore = createWorkflowStore();

// ========== Derived Stores ==========

/**
 * Layout rows for rendering (main steps with their supporters)
 */
export const layoutRows: Readable<LayoutRow[]> = derived(
    workflowStore,
    ($store) => getLayoutRows(
        $store.data.steps,
        $store.data.supportRelations,
        $store.globalPhases
    )
);

/**
 * Core step instances sorted by order
 */
export const sortedCoreStepInstances: Readable<CoreStepInstance[]> = derived(
    workflowStore,
    ($store) => [...($store.data.coreStepInstances || [])].sort((a, b) => a.order - b.order)
);

/**
 * Check if workflow has any data
 */
export const hasWorkflowData: Readable<boolean> = derived(
    workflowStore,
    ($store) => $store.data.steps.length > 0 || ($store.data.coreStepInstances?.length ?? 0) > 0
);
