/**
 * Key Info Store (핵심정보)
 *
 * State management for the Key Info system in the viewer.
 */

import { writable, derived, get } from 'svelte/store';
import type {
    ProjectKeyInfoData,
    KeyInfoInstance,
    KeyInfoCategoryDefinition,
    KeyInfoSettings,
    KeyInfoCaptureValue,
} from '$lib/types/keyInfo';
import {
    createEmptyKeyInfoData,
    createKeyInfoInstance,
    generateKeyInfoCaptureId,
    getInstanceByItem,
    isCategoryComplete,
    areAllCategoriesComplete,
} from '$lib/types/keyInfo';

// ========== State Interface ==========

export interface KeyInfoState {
    data: ProjectKeyInfoData;
    settings: KeyInfoSettings;
    saving: boolean;
    captureMode: boolean;
    captureTargetInstanceId: string | null;
}

// ========== Store Creation ==========

function createKeyInfoStore() {
    const { subscribe, set, update } = writable<KeyInfoState>({
        data: createEmptyKeyInfoData(),
        settings: { categories: [] },
        saving: false,
        captureMode: false,
        captureTargetInstanceId: null,
    });

    return {
        subscribe,
        set,
        update,

        /**
         * Initialize the store with project data and settings
         */
        init(data: ProjectKeyInfoData, settings: KeyInfoSettings) {
            update(state => ({
                ...state,
                data: data || createEmptyKeyInfoData(),
                settings: settings || { categories: [] },
            }));
        },

        /**
         * Set the key info data
         */
        setData(data: ProjectKeyInfoData) {
            update(state => ({
                ...state,
                data,
            }));
        },

        /**
         * Set the key info settings
         */
        setSettings(settings: KeyInfoSettings) {
            update(state => ({
                ...state,
                settings,
            }));
        },

        /**
         * Set saving state
         */
        setSaving(saving: boolean) {
            update(state => ({
                ...state,
                saving,
            }));
        },

        /**
         * Add or update an instance for a category/item
         */
        upsertInstance(
            categoryId: string,
            itemId: string,
        ): KeyInfoInstance {
            let newInstance: KeyInfoInstance | null = null;

            update(state => {
                const existing = getInstanceByItem(state.data.instances, categoryId, itemId);

                if (existing) {
                    // Return existing instance (no changes needed)
                    newInstance = existing;
                    return state;
                } else {
                    // Create new instance
                    newInstance = createKeyInfoInstance(
                        categoryId,
                        itemId,
                        state.data.instances.length
                    );
                    return {
                        ...state,
                        data: {
                            ...state.data,
                            instances: [...state.data.instances, newInstance],
                            updatedAt: new Date().toISOString(),
                        },
                    };
                }
            });

            return newInstance!;
        },

        /**
         * Update instance with capture value
         */
        updateInstanceCapture(
            instanceId: string,
            captureValue: Omit<KeyInfoCaptureValue, 'id'>,
        ) {
            update(state => ({
                ...state,
                data: {
                    ...state.data,
                    instances: state.data.instances.map(inst =>
                        inst.id === instanceId
                            ? {
                                ...inst,
                                captureValue: {
                                    ...captureValue,
                                    id: inst.captureValue?.id || generateKeyInfoCaptureId(),
                                },
                                updatedAt: new Date().toISOString(),
                            }
                            : inst
                    ),
                    updatedAt: new Date().toISOString(),
                },
            }));
        },

        /**
         * Update instance with text value
         */
        updateInstanceText(instanceId: string, textValue: string) {
            update(state => ({
                ...state,
                data: {
                    ...state.data,
                    instances: state.data.instances.map(inst =>
                        inst.id === instanceId
                            ? {
                                ...inst,
                                textValue,
                                updatedAt: new Date().toISOString(),
                            }
                            : inst
                    ),
                    updatedAt: new Date().toISOString(),
                },
            }));
        },

        /**
         * Update instance with image value
         */
        updateInstanceImage(instanceId: string, imageId: string, imageCaption?: string) {
            update(state => ({
                ...state,
                data: {
                    ...state.data,
                    instances: state.data.instances.map(inst =>
                        inst.id === instanceId
                            ? {
                                ...inst,
                                imageId,
                                imageCaption,
                                updatedAt: new Date().toISOString(),
                            }
                            : inst
                    ),
                    updatedAt: new Date().toISOString(),
                },
            }));
        },

        /**
         * Update instance image caption
         */
        updateInstanceImageCaption(instanceId: string, imageCaption: string) {
            update(state => ({
                ...state,
                data: {
                    ...state.data,
                    instances: state.data.instances.map(inst =>
                        inst.id === instanceId
                            ? {
                                ...inst,
                                imageCaption,
                                updatedAt: new Date().toISOString(),
                            }
                            : inst
                    ),
                    updatedAt: new Date().toISOString(),
                },
            }));
        },

        /**
         * Remove an instance
         */
        removeInstance(instanceId: string) {
            update(state => ({
                ...state,
                data: {
                    ...state.data,
                    instances: state.data.instances.filter(inst => inst.id !== instanceId),
                    updatedAt: new Date().toISOString(),
                },
            }));
        },

        /**
         * Clear all data from a specific instance
         */
        clearInstanceData(instanceId: string) {
            update(state => ({
                ...state,
                data: {
                    ...state.data,
                    instances: state.data.instances.map(inst =>
                        inst.id === instanceId
                            ? {
                                ...inst,
                                captureValue: undefined,
                                textValue: undefined,
                                imageId: undefined,
                                imageCaption: undefined,
                                updatedAt: new Date().toISOString(),
                            }
                            : inst
                    ),
                    updatedAt: new Date().toISOString(),
                },
            }));
        },

        /**
         * Start capture mode for an instance
         */
        startCaptureMode(instanceId: string) {
            update(state => ({
                ...state,
                captureMode: true,
                captureTargetInstanceId: instanceId,
            }));
        },

        /**
         * End capture mode
         */
        endCaptureMode() {
            update(state => ({
                ...state,
                captureMode: false,
                captureTargetInstanceId: null,
            }));
        },

        /**
         * Reset the store
         */
        reset() {
            set({
                data: createEmptyKeyInfoData(),
                settings: { categories: [] },
                saving: false,
                captureMode: false,
                captureTargetInstanceId: null,
            });
        },
    };
}

export const keyInfoStore = createKeyInfoStore();

// ========== Derived Stores ==========

/**
 * Instances grouped by category ID
 */
export const instancesByCategory = derived(keyInfoStore, ($store) => {
    const map = new Map<string, KeyInfoInstance[]>();
    for (const instance of $store.data.instances) {
        const list = map.get(instance.categoryId) || [];
        list.push(instance);
        map.set(instance.categoryId, list);
    }
    return map;
});

/**
 * Category completion status
 */
export const categoryCompletionStatus = derived(keyInfoStore, ($store) => {
    const status = new Map<string, boolean>();
    for (const category of $store.settings.categories) {
        status.set(category.id, isCategoryComplete(category, $store.data.instances));
    }
    return status;
});

/**
 * Check if all categories are complete
 */
export const allCategoriesComplete = derived(keyInfoStore, ($store) => {
    return areAllCategoriesComplete($store.settings.categories, $store.data.instances);
});

/**
 * Get capture overlays for the viewer canvas
 */
export const captureOverlays = derived(keyInfoStore, ($store) => {
    const overlays: Array<{
        instanceId: string;
        label: string;
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
        color: string;
    }> = [];

    for (const instance of $store.data.instances) {
        if (instance.captureValue) {
            const category = $store.settings.categories.find(c => c.id === instance.categoryId);
            const item = category?.items.find(i => i.id === instance.itemId);

            overlays.push({
                instanceId: instance.id,
                label: item?.title || 'Capture',
                slideIndex: instance.captureValue.slideIndex,
                x: instance.captureValue.x,
                y: instance.captureValue.y,
                width: instance.captureValue.width,
                height: instance.captureValue.height,
                color: '#3b82f6', // Blue color for key info captures
            });
        }
    }

    return overlays;
});
