/**
 * Tests for frontend/src/lib/types/workflow.ts
 *
 * Tests workflow type definitions and utility functions.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
    // ID generators
    generateCoreStepId,
    generateCoreStepPresetId,
    generateCoreStepInstanceId,
    generatePhaseId,
    generateSupportId,
    generateWorkflowId,
    generateUnifiedStepId,
    generateStepInstanceId,
    generateStepCaptureId,
    generateAttachmentId,
    generateKeyStepLinkId,
    // Factory functions
    createCoreStepDefinition,
    createCoreStepPreset,
    createCoreStepInstance,
    createPhaseType,
    createSupportRelation,
    createWorkflowDefinition,
    createEmptyWorkflowData,
    createStepInstance,
    createStepCapture,
    createAttachment,
    createUnifiedCoreStep,
    createUnifiedRegularStep,
    // Validation functions
    checkCoreStepCompletion,
    validateFirstLastCore,
    validateReorder,
    validateDeletion,
    validateSupportCreation,
    // Support/Phase functions
    getSupportSteps,
    isStepSupporter,
    getSupportInfo,
    getMainFlowSteps,
    addSupportRelation,
    removeSupportRelation,
    removeSupportByStepId,
    cleanupOrphanedSupports,
    addPhaseType,
    removePhaseType,
    updatePhaseType,
    getLayoutRows,
    getAllPhaseTypes,
    getPhaseById,
    // Migration functions
    migrateToUnifiedSteps,
    syncUnifiedToLegacy,
    // Key step linking functions
    checkKeyStepLinkingComplete,
    getAvailableStepsForLinking,
    getKeyStepLinksForCoreStep,
    saveKeyStepLinks,
    confirmWorkflow,
    unconfirmWorkflow,
    // Utility
    getInputTypeDisplayName,
    DEFAULT_WORKFLOW_COLUMNS,
} from '$lib/types/workflow';
import type {
    UnifiedStepItem,
    CoreStepDefinition,
    WorkflowStepInstance,
    SupportRelation,
    ProjectWorkflowData,
    PhaseType,
} from '$lib/types/workflow';

// ========== ID Generation Tests ==========

describe('ID Generators', () => {
    describe('generateCoreStepId', () => {
        it('should generate id with cs_ prefix', () => {
            const id = generateCoreStepId();
            expect(id).toMatch(/^cs_\d+_[a-z0-9]+$/);
        });

        it('should generate unique ids', () => {
            const ids = new Set([...Array(100)].map(() => generateCoreStepId()));
            expect(ids.size).toBe(100);
        });
    });

    describe('generateCoreStepPresetId', () => {
        it('should generate id with csp_ prefix', () => {
            const id = generateCoreStepPresetId();
            expect(id).toMatch(/^csp_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateCoreStepInstanceId', () => {
        it('should generate id with csi_ prefix', () => {
            const id = generateCoreStepInstanceId();
            expect(id).toMatch(/^csi_\d+_[a-z0-9]+$/);
        });
    });

    describe('generatePhaseId', () => {
        it('should generate id with phase_ prefix', () => {
            const id = generatePhaseId();
            expect(id).toMatch(/^phase_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateSupportId', () => {
        it('should generate id with support_ prefix', () => {
            const id = generateSupportId();
            expect(id).toMatch(/^support_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateWorkflowId', () => {
        it('should generate id with wf_ prefix', () => {
            const id = generateWorkflowId();
            expect(id).toMatch(/^wf_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateUnifiedStepId', () => {
        it('should generate id with us_ prefix', () => {
            const id = generateUnifiedStepId();
            expect(id).toMatch(/^us_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateStepInstanceId', () => {
        it('should generate id with step_ prefix', () => {
            const id = generateStepInstanceId();
            expect(id).toMatch(/^step_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateStepCaptureId', () => {
        it('should generate id with scap_ prefix', () => {
            const id = generateStepCaptureId();
            expect(id).toMatch(/^scap_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateAttachmentId', () => {
        it('should generate id with att_ prefix', () => {
            const id = generateAttachmentId();
            expect(id).toMatch(/^att_\d+_[a-z0-9]+$/);
        });
    });

    describe('generateKeyStepLinkId', () => {
        it('should generate id with ksl_ prefix', () => {
            const id = generateKeyStepLinkId();
            expect(id).toMatch(/^ksl_\d+_[a-z0-9]+$/);
        });
    });
});

// ========== Factory Function Tests ==========

describe('Factory Functions', () => {
    describe('createCoreStepDefinition', () => {
        it('should create definition with required fields', () => {
            const def = createCoreStepDefinition('Test Step');
            expect(def.name).toBe('Test Step');
            expect(def.id).toMatch(/^cs_/);
            expect(def.presets).toEqual([]);
            expect(def.requiresKeyStepLinking).toBe(false);
            expect(def.createdAt).toBeDefined();
        });

        it('should respect requiresKeyStepLinking flag', () => {
            const def = createCoreStepDefinition('Test', true);
            expect(def.requiresKeyStepLinking).toBe(true);
        });
    });

    describe('createCoreStepPreset', () => {
        it('should create preset with required fields', () => {
            const preset = createCoreStepPreset('Preset', ['capture', 'text'], 0);
            expect(preset.name).toBe('Preset');
            expect(preset.allowedTypes).toEqual(['capture', 'text']);
            expect(preset.order).toBe(0);
            expect(preset.id).toMatch(/^csp_/);
        });
    });

    describe('createCoreStepInstance', () => {
        it('should create instance with required fields', () => {
            const instance = createCoreStepInstance('cs_123', [], 0);
            expect(instance.coreStepId).toBe('cs_123');
            expect(instance.presetValues).toEqual([]);
            expect(instance.order).toBe(0);
            expect(instance.id).toMatch(/^csi_/);
        });
    });

    describe('createPhaseType', () => {
        it('should create phase type', () => {
            const phase = createPhaseType('Testing', '#FF0000', 0);
            expect(phase.name).toBe('Testing');
            expect(phase.color).toBe('#FF0000');
            expect(phase.order).toBe(0);
            expect(phase.id).toMatch(/^phase_/);
        });
    });

    describe('createSupportRelation', () => {
        it('should create support relation', () => {
            const rel = createSupportRelation('step1', 'step2', 'phase1');
            expect(rel.supporterStepId).toBe('step1');
            expect(rel.targetStepId).toBe('step2');
            expect(rel.phaseId).toBe('phase1');
            expect(rel.id).toMatch(/^support_/);
        });
    });

    describe('createWorkflowDefinition', () => {
        it('should create workflow definition with default columns', () => {
            const def = createWorkflowDefinition('Workflow 1', 0);
            expect(def.name).toBe('Workflow 1');
            expect(def.order).toBe(0);
            expect(def.steps.columns).toEqual(DEFAULT_WORKFLOW_COLUMNS);
            expect(def.steps.rows).toEqual([]);
        });
    });

    describe('createEmptyWorkflowData', () => {
        it('should create empty workflow data', () => {
            const data = createEmptyWorkflowData();
            expect(data.steps).toEqual([]);
            expect(data.createdAt).toBeDefined();
        });
    });

    describe('createStepInstance', () => {
        it('should create step instance', () => {
            const step = createStepInstance('step_def_1', 0);
            expect(step.stepId).toBe('step_def_1');
            expect(step.order).toBe(0);
            expect(step.captures).toEqual([]);
            expect(step.attachments).toEqual([]);
        });
    });

    describe('createStepCapture', () => {
        it('should create capture', () => {
            const capture = createStepCapture(0, 10, 20, 100, 50, 'Label');
            expect(capture.slideIndex).toBe(0);
            expect(capture.x).toBe(10);
            expect(capture.y).toBe(20);
            expect(capture.width).toBe(100);
            expect(capture.height).toBe(50);
            expect(capture.label).toBe('Label');
        });
    });

    describe('createAttachment', () => {
        it('should create image attachment', () => {
            const att = createAttachment('image', 'img_123', 'Caption');
            expect(att.type).toBe('image');
            expect(att.imageId).toBe('img_123');
            expect(att.caption).toBe('Caption');
            expect(att.data).toBeUndefined();
        });

        it('should create text attachment', () => {
            const att = createAttachment('text', 'Some text content', 'Note');
            expect(att.type).toBe('text');
            expect(att.data).toBe('Some text content');
            expect(att.imageId).toBeUndefined();
        });
    });

    describe('createUnifiedCoreStep', () => {
        it('should create unified core step', () => {
            const step = createUnifiedCoreStep('cs_123', [], 0);
            expect(step.type).toBe('core');
            expect(step.coreStepId).toBe('cs_123');
            expect(step.order).toBe(0);
        });
    });

    describe('createUnifiedRegularStep', () => {
        it('should create unified regular step', () => {
            const step = createUnifiedRegularStep('step_123', 1);
            expect(step.type).toBe('regular');
            expect(step.stepId).toBe('step_123');
            expect(step.order).toBe(1);
            expect(step.captures).toEqual([]);
            expect(step.attachments).toEqual([]);
        });
    });
});

// ========== Validation Function Tests ==========

describe('Validation Functions', () => {
    describe('checkCoreStepCompletion', () => {
        it('should return complete when all definitions added', () => {
            const definitions: CoreStepDefinition[] = [
                { id: 'cs_1', name: 'Step 1', presets: [], requiresKeyStepLinking: false, createdAt: '' },
                { id: 'cs_2', name: 'Step 2', presets: [], requiresKeyStepLinking: false, createdAt: '' },
            ];
            const unifiedSteps: UnifiedStepItem[] = [
                { id: 'us_1', type: 'core', order: 0, createdAt: '', coreStepId: 'cs_1' },
                { id: 'us_2', type: 'core', order: 1, createdAt: '', coreStepId: 'cs_2' },
            ];

            const result = checkCoreStepCompletion(unifiedSteps, definitions);
            expect(result.isComplete).toBe(true);
            expect(result.missingDefinitions).toHaveLength(0);
        });

        it('should return incomplete when definitions missing', () => {
            const definitions: CoreStepDefinition[] = [
                { id: 'cs_1', name: 'Step 1', presets: [], requiresKeyStepLinking: false, createdAt: '' },
                { id: 'cs_2', name: 'Step 2', presets: [], requiresKeyStepLinking: false, createdAt: '' },
            ];
            const unifiedSteps: UnifiedStepItem[] = [
                { id: 'us_1', type: 'core', order: 0, createdAt: '', coreStepId: 'cs_1' },
            ];

            const result = checkCoreStepCompletion(unifiedSteps, definitions);
            expect(result.isComplete).toBe(false);
            expect(result.missingDefinitions).toHaveLength(1);
            expect(result.missingDefinitions[0].id).toBe('cs_2');
        });
    });

    describe('validateFirstLastCore', () => {
        it('should return valid for empty array', () => {
            const result = validateFirstLastCore([]);
            expect(result.isValid).toBe(true);
        });

        it('should return valid when first and last are core', () => {
            const steps: UnifiedStepItem[] = [
                { id: '1', type: 'core', order: 0, createdAt: '' },
                { id: '2', type: 'regular', order: 1, createdAt: '' },
                { id: '3', type: 'core', order: 2, createdAt: '' },
            ];
            const result = validateFirstLastCore(steps);
            expect(result.isValid).toBe(true);
        });

        it('should return invalid when first is not core', () => {
            const steps: UnifiedStepItem[] = [
                { id: '1', type: 'regular', order: 0, createdAt: '' },
                { id: '2', type: 'core', order: 1, createdAt: '' },
            ];
            const result = validateFirstLastCore(steps);
            expect(result.isValid).toBe(false);
            expect(result.errorMessage).toContain('첫 번째');
        });

        it('should return invalid when last is not core', () => {
            const steps: UnifiedStepItem[] = [
                { id: '1', type: 'core', order: 0, createdAt: '' },
                { id: '2', type: 'regular', order: 1, createdAt: '' },
            ];
            const result = validateFirstLastCore(steps);
            expect(result.isValid).toBe(false);
            expect(result.errorMessage).toContain('마지막');
        });
    });

    describe('validateReorder', () => {
        it('should return valid for same index', () => {
            const steps: UnifiedStepItem[] = [
                { id: '1', type: 'core', order: 0, createdAt: '' },
            ];
            const result = validateReorder(steps, 0, 0);
            expect(result.isValid).toBe(true);
        });

        it('should validate simulated reorder result', () => {
            const steps: UnifiedStepItem[] = [
                { id: '1', type: 'core', order: 0, createdAt: '' },
                { id: '2', type: 'regular', order: 1, createdAt: '' },
                { id: '3', type: 'core', order: 2, createdAt: '' },
            ];
            // Moving core to middle would leave regular at end
            const result = validateReorder(steps, 2, 1);
            expect(result.isValid).toBe(false);
        });
    });

    describe('validateDeletion', () => {
        it('should return valid for single item', () => {
            const steps: UnifiedStepItem[] = [
                { id: '1', type: 'core', order: 0, createdAt: '' },
            ];
            const result = validateDeletion(steps, 0);
            expect(result.isValid).toBe(true);
        });

        it('should validate that deletion keeps first/last as core', () => {
            const steps: UnifiedStepItem[] = [
                { id: '1', type: 'core', order: 0, createdAt: '' },
                { id: '2', type: 'core', order: 1, createdAt: '' },
            ];
            // Deleting first core would leave second core at start - valid
            const result = validateDeletion(steps, 0);
            expect(result.isValid).toBe(true);
        });
    });

    describe('validateSupportCreation', () => {
        it('should reject self-support', () => {
            const steps: WorkflowStepInstance[] = [
                { id: 'step1', stepId: 's1', captures: [], attachments: [], order: 0, createdAt: '' },
            ];
            const result = validateSupportCreation('step1', 'step1', steps, []);
            expect(result).toContain('자기 자신');
        });

        it('should reject if steps not found', () => {
            const result = validateSupportCreation('step1', 'step2', [], []);
            expect(result).toContain('찾을 수 없습니다');
        });

        it('should return null for valid support creation', () => {
            const steps: WorkflowStepInstance[] = [
                { id: 'step1', stepId: 's1', captures: [], attachments: [], order: 0, createdAt: '' },
                { id: 'step2', stepId: 's2', captures: [], attachments: [], order: 1, createdAt: '' },
            ];
            const result = validateSupportCreation('step1', 'step2', steps, []);
            expect(result).toBeNull();
        });
    });
});

// ========== Support/Phase Function Tests ==========

describe('Support/Phase Functions', () => {
    const mockSteps: WorkflowStepInstance[] = [
        { id: 'step1', stepId: 's1', captures: [], attachments: [], order: 0, createdAt: '' },
        { id: 'step2', stepId: 's2', captures: [], attachments: [], order: 1, createdAt: '' },
        { id: 'step3', stepId: 's3', captures: [], attachments: [], order: 2, createdAt: '' },
    ];

    const mockRelations: SupportRelation[] = [
        { id: 'rel1', supporterStepId: 'step2', targetStepId: 'step1', phaseId: 'phase1', createdAt: '' },
    ];

    describe('getSupportSteps', () => {
        it('should return supporters for a target', () => {
            const result = getSupportSteps('step1', mockRelations);
            expect(result).toHaveLength(1);
            expect(result[0].supporterStepId).toBe('step2');
        });

        it('should return empty array for no supporters', () => {
            const result = getSupportSteps('step3', mockRelations);
            expect(result).toHaveLength(0);
        });

        it('should handle undefined relations', () => {
            const result = getSupportSteps('step1', undefined);
            expect(result).toHaveLength(0);
        });
    });

    describe('isStepSupporter', () => {
        it('should return true for supporter step', () => {
            expect(isStepSupporter('step2', mockRelations)).toBe(true);
        });

        it('should return false for non-supporter step', () => {
            expect(isStepSupporter('step1', mockRelations)).toBe(false);
        });
    });

    describe('getSupportInfo', () => {
        it('should return support info for supporter', () => {
            const info = getSupportInfo('step2', mockRelations);
            expect(info?.targetStepId).toBe('step1');
        });

        it('should return undefined for non-supporter', () => {
            const info = getSupportInfo('step1', mockRelations);
            expect(info).toBeUndefined();
        });
    });

    describe('getMainFlowSteps', () => {
        it('should exclude supporter steps', () => {
            const mainSteps = getMainFlowSteps(mockSteps, mockRelations);
            expect(mainSteps).toHaveLength(2);
            expect(mainSteps.find(s => s.id === 'step2')).toBeUndefined();
        });
    });

    describe('addSupportRelation', () => {
        it('should add new support relation', () => {
            const data: ProjectWorkflowData = { steps: mockSteps };
            const result = addSupportRelation(data, 'step3', 'step1', 'phase1');
            expect(result.supportRelations).toHaveLength(1);
            expect(result.supportRelations![0].supporterStepId).toBe('step3');
        });
    });

    describe('removeSupportRelation', () => {
        it('should remove support relation by id', () => {
            const data: ProjectWorkflowData = { steps: [], supportRelations: mockRelations };
            const result = removeSupportRelation(data, 'rel1');
            expect(result.supportRelations).toHaveLength(0);
        });
    });

    describe('removeSupportByStepId', () => {
        it('should remove relation by supporter step id', () => {
            const data: ProjectWorkflowData = { steps: [], supportRelations: mockRelations };
            const result = removeSupportByStepId(data, 'step2');
            expect(result.supportRelations).toHaveLength(0);
        });
    });

    describe('cleanupOrphanedSupports', () => {
        it('should remove relations with missing steps', () => {
            const data: ProjectWorkflowData = {
                steps: [mockSteps[0]], // Only step1
                supportRelations: mockRelations, // Relation references step2
            };
            const result = cleanupOrphanedSupports(data);
            expect(result.supportRelations).toHaveLength(0);
        });
    });

    describe('addPhaseType', () => {
        it('should add new phase type', () => {
            const data: ProjectWorkflowData = { steps: [] };
            const result = addPhaseType(data, 'New Phase', '#00FF00');
            expect(result.phaseTypes).toHaveLength(1);
            expect(result.phaseTypes![0].name).toBe('New Phase');
        });
    });

    describe('removePhaseType', () => {
        it('should remove phase and related support relations', () => {
            const phases: PhaseType[] = [{ id: 'phase1', name: 'P1', color: '#FF0000', order: 0 }];
            const data: ProjectWorkflowData = {
                steps: mockSteps,
                phaseTypes: phases,
                supportRelations: mockRelations,
            };
            const result = removePhaseType(data, 'phase1');
            expect(result.phaseTypes).toHaveLength(0);
            expect(result.supportRelations).toHaveLength(0);
        });
    });

    describe('updatePhaseType', () => {
        it('should update phase properties', () => {
            const phases: PhaseType[] = [{ id: 'phase1', name: 'Old', color: '#000', order: 0 }];
            const data: ProjectWorkflowData = { steps: [], phaseTypes: phases };
            const result = updatePhaseType(data, 'phase1', { name: 'New', color: '#FFF' });
            expect(result.phaseTypes![0].name).toBe('New');
            expect(result.phaseTypes![0].color).toBe('#FFF');
        });
    });

    describe('getAllPhaseTypes', () => {
        it('should return phase types', () => {
            const phases: PhaseType[] = [{ id: 'p1', name: 'P1', color: '#F00', order: 0 }];
            const data: ProjectWorkflowData = { steps: [], phaseTypes: phases };
            expect(getAllPhaseTypes(data)).toEqual(phases);
        });

        it('should return empty array if no phases', () => {
            const data: ProjectWorkflowData = { steps: [] };
            expect(getAllPhaseTypes(data)).toEqual([]);
        });
    });

    describe('getPhaseById', () => {
        it('should find phase by id', () => {
            const phases: PhaseType[] = [
                { id: 'p1', name: 'P1', color: '#F00', order: 0 },
                { id: 'p2', name: 'P2', color: '#0F0', order: 1 },
            ];
            expect(getPhaseById('p2', phases)?.name).toBe('P2');
        });

        it('should return undefined for not found', () => {
            expect(getPhaseById('unknown', [])).toBeUndefined();
        });
    });

    describe('getLayoutRows', () => {
        it('should create layout with main steps and supporters', () => {
            const phases: PhaseType[] = [{ id: 'phase1', name: 'P1', color: '#F00', order: 0 }];
            const rows = getLayoutRows(mockSteps, mockRelations, phases);

            // step1 and step3 are main flow (step2 is supporter)
            expect(rows).toHaveLength(2);

            // step1 should have step2 as supporter
            const step1Row = rows.find(r => r.mainStep.id === 'step1');
            expect(step1Row?.supporters).toHaveLength(1);
        });
    });
});

// ========== Migration Function Tests ==========

describe('Migration Functions', () => {
    describe('migrateToUnifiedSteps', () => {
        it('should skip migration if unifiedSteps already exist', () => {
            const data: ProjectWorkflowData = {
                steps: [],
                unifiedSteps: [{ id: 'us_1', type: 'core', order: 0, createdAt: '' }],
            };
            const result = migrateToUnifiedSteps(data);
            expect(result.unifiedSteps).toHaveLength(1);
        });

        it('should migrate legacy data to unified steps', () => {
            const data: ProjectWorkflowData = {
                steps: [
                    { id: 's1', stepId: 'step1', captures: [], attachments: [], order: 0, createdAt: '2024-01-01' },
                ],
                coreStepInstances: [
                    { id: 'csi_1', coreStepId: 'cs_1', presetValues: [], order: 0, createdAt: '2024-01-01' },
                ],
            };
            const result = migrateToUnifiedSteps(data);

            expect(result.unifiedSteps).toHaveLength(2);
            expect(result.unifiedSteps![0].type).toBe('core');
            expect(result.unifiedSteps![1].type).toBe('regular');
        });
    });

    describe('syncUnifiedToLegacy', () => {
        it('should convert unified steps to legacy format', () => {
            const data: ProjectWorkflowData = {
                steps: [],
                unifiedSteps: [
                    { id: 'us_1', type: 'core', order: 0, createdAt: '', coreStepId: 'cs_1', presetValues: [] },
                    { id: 'us_2', type: 'regular', order: 1, createdAt: '', stepId: 'step_1', captures: [], attachments: [] },
                ],
            };
            const result = syncUnifiedToLegacy(data);

            expect(result.coreStepInstances).toHaveLength(1);
            expect(result.steps).toHaveLength(1);
        });
    });
});

// ========== Key Step Linking Tests ==========

describe('Key Step Linking Functions', () => {
    describe('checkKeyStepLinkingComplete', () => {
        it('should return complete when no linking required', () => {
            const definitions: CoreStepDefinition[] = [
                { id: 'cs_1', name: 'Step', presets: [], requiresKeyStepLinking: false, createdAt: '' },
            ];
            const steps: UnifiedStepItem[] = [
                { id: 'us_1', type: 'core', order: 0, createdAt: '', coreStepId: 'cs_1' },
            ];
            const result = checkKeyStepLinkingComplete(steps, definitions, []);
            expect(result.isComplete).toBe(true);
        });

        it('should return incomplete when linking required but not done', () => {
            const definitions: CoreStepDefinition[] = [
                { id: 'cs_1', name: 'Step', presets: [], requiresKeyStepLinking: true, createdAt: '' },
            ];
            const steps: UnifiedStepItem[] = [
                { id: 'us_1', type: 'core', order: 0, createdAt: '', coreStepId: 'cs_1' },
            ];
            const result = checkKeyStepLinkingComplete(steps, definitions, []);
            expect(result.isComplete).toBe(false);
            expect(result.pendingCoreSteps).toHaveLength(1);
        });
    });

    describe('getAvailableStepsForLinking', () => {
        it('should return steps before target', () => {
            const steps: UnifiedStepItem[] = [
                { id: 'us_1', type: 'core', order: 0, createdAt: '' },
                { id: 'us_2', type: 'regular', order: 1, createdAt: '' },
                { id: 'us_3', type: 'core', order: 2, createdAt: '' },
            ];
            const result = getAvailableStepsForLinking(steps, 'us_3');
            expect(result).toHaveLength(2);
        });

        it('should return empty for first step', () => {
            const steps: UnifiedStepItem[] = [
                { id: 'us_1', type: 'core', order: 0, createdAt: '' },
            ];
            const result = getAvailableStepsForLinking(steps, 'us_1');
            expect(result).toHaveLength(0);
        });
    });

    describe('getKeyStepLinksForCoreStep', () => {
        it('should find links for core step', () => {
            const links = [
                { coreStepInstanceId: 'us_1', linkedSteps: [{ stepId: 's1', priority: 1 }], confirmedAt: '' },
            ];
            const result = getKeyStepLinksForCoreStep('us_1', links);
            expect(result?.linkedSteps).toHaveLength(1);
        });

        it('should return undefined if not found', () => {
            const result = getKeyStepLinksForCoreStep('us_999', []);
            expect(result).toBeUndefined();
        });
    });

    describe('saveKeyStepLinks', () => {
        it('should save new links', () => {
            const data: ProjectWorkflowData = { steps: [] };
            const result = saveKeyStepLinks(data, 'us_1', [{ stepId: 's1', priority: 1 }]);
            expect(result.keyStepLinks).toHaveLength(1);
        });

        it('should replace existing links', () => {
            const data: ProjectWorkflowData = {
                steps: [],
                keyStepLinks: [{ coreStepInstanceId: 'us_1', linkedSteps: [], confirmedAt: '' }],
            };
            const result = saveKeyStepLinks(data, 'us_1', [{ stepId: 's2', priority: 1 }]);
            expect(result.keyStepLinks).toHaveLength(1);
            expect(result.keyStepLinks![0].linkedSteps[0].stepId).toBe('s2');
        });
    });

    describe('confirmWorkflow / unconfirmWorkflow', () => {
        it('should mark workflow as confirmed', () => {
            const data: ProjectWorkflowData = { steps: [] };
            const result = confirmWorkflow(data);
            expect(result.isConfirmed).toBe(true);
            expect(result.confirmedAt).toBeDefined();
        });

        it('should unconfirm workflow', () => {
            const data: ProjectWorkflowData = { steps: [], isConfirmed: true, confirmedAt: '2024-01-01' };
            const result = unconfirmWorkflow(data);
            expect(result.isConfirmed).toBe(false);
            expect(result.confirmedAt).toBeUndefined();
        });
    });
});

// ========== Utility Function Tests ==========

describe('Utility Functions', () => {
    describe('getInputTypeDisplayName', () => {
        it('should return Korean display names', () => {
            expect(getInputTypeDisplayName('capture')).toBe('캡처');
            expect(getInputTypeDisplayName('text')).toBe('텍스트');
            expect(getInputTypeDisplayName('image_clipboard')).toBe('이미지 붙여넣기');
        });

        it('should return type itself for unknown types', () => {
            expect(getInputTypeDisplayName('unknown' as any)).toBe('unknown');
        });
    });
});
