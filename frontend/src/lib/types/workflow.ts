/**
 * Workflow step type definitions
 */

// ========== Core Step Definitions ==========

// Allowed input types for Core Step presets
export type CoreStepInputType = 'capture' | 'text' | 'image_clipboard';

// Core Step Preset Field Definition
export interface CoreStepPreset {
    id: string;
    name: string;
    allowedTypes: CoreStepInputType[];  // Which input types are allowed for this preset
    order: number;
}

// Core Step Definition (defined in settings)
export interface CoreStepDefinition {
    id: string;
    name: string;
    presets: CoreStepPreset[];
    createdAt: string;
}

// Core Step Preset Value (the actual input for a preset)
export interface CoreStepPresetValue {
    presetId: string;
    type: CoreStepInputType;
    // Value depends on type:
    // - capture: StepCapture object
    // - text: string
    // - image_clipboard: imageId reference
    captureValue?: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
        label?: string;
    };
    textValue?: string;
    imageId?: string;  // Reference to image in attachments.db
}

// Core Step Instance (added to a project's workflow)
export interface CoreStepInstance {
    id: string;
    coreStepId: string;  // Reference to CoreStepDefinition.id
    presetValues: CoreStepPresetValue[];
    order: number;
    createdAt: string;
}

// Core Steps Settings Container
export interface CoreStepsSettings {
    definitions: CoreStepDefinition[];
}

// Generate unique ID for core step definitions
export function generateCoreStepId(): string {
    return `cs_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Generate unique ID for core step presets
export function generateCoreStepPresetId(): string {
    return `csp_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Generate unique ID for core step instances
export function generateCoreStepInstanceId(): string {
    return `csi_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Create a new core step definition
export function createCoreStepDefinition(name: string): CoreStepDefinition {
    return {
        id: generateCoreStepId(),
        name,
        presets: [],
        createdAt: new Date().toISOString(),
    };
}

// Create a new core step preset
export function createCoreStepPreset(
    name: string,
    allowedTypes: CoreStepInputType[],
    order: number
): CoreStepPreset {
    return {
        id: generateCoreStepPresetId(),
        name,
        allowedTypes,
        order,
    };
}

// Create a new core step instance
export function createCoreStepInstance(
    coreStepId: string,
    presetValues: CoreStepPresetValue[],
    order: number
): CoreStepInstance {
    return {
        id: generateCoreStepInstanceId(),
        coreStepId,
        presetValues,
        order,
        createdAt: new Date().toISOString(),
    };
}

// Get input type display name (Korean)
export function getInputTypeDisplayName(type: CoreStepInputType): string {
    switch (type) {
        case 'capture': return '캡처';
        case 'text': return '텍스트';
        case 'image_clipboard': return '이미지 붙여넣기';
        default: return type;
    }
}

// ========== End Core Step Definitions ==========

// Workflow Step Column Definition
export interface WorkflowStepColumn {
    id: string;
    name: string;
    isDefault: boolean;  // Default columns cannot be deleted, only renamed
}

// Workflow Step Row (a single step definition)
export interface WorkflowStepRow {
    id: string;
    values: Record<string, string>;  // column_id -> value
}

// Workflow Steps Container (settings)
export interface WorkflowSteps {
    columns: WorkflowStepColumn[];
    rows: WorkflowStepRow[];
}

// ========== Workflow Definition (Multiple Workflows) ==========

// A single workflow definition with its own steps
export interface WorkflowDefinition {
    id: string;
    name: string;
    order: number;
    useGlobalSteps: boolean;  // If true, uses global workflow_steps; if false, uses its own steps
    steps: WorkflowSteps | null;  // Own step definitions (only used when useGlobalSteps is false)
    createdAt: string;
}

// Workflow Settings Container
export interface WorkflowSettings {
    workflows: WorkflowDefinition[];
    phaseTypes: PhaseType[];
    globalStepsLabel: string;  // Label for global steps (e.g., "발생현상")
}

// Generate unique ID for workflow definitions
export function generateWorkflowId(): string {
    return `wf_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Create a new workflow definition
export function createWorkflowDefinition(
    name: string,
    order: number,
    useGlobalSteps: boolean = true
): WorkflowDefinition {
    return {
        id: generateWorkflowId(),
        name,
        order,
        useGlobalSteps,
        steps: useGlobalSteps ? null : { columns: [], rows: [] },
        createdAt: new Date().toISOString(),
    };
}

// Default columns for workflow steps
export const DEFAULT_WORKFLOW_COLUMNS: WorkflowStepColumn[] = [
    { id: "step_category", name: "스텝 구분", isDefault: true },
    { id: "system", name: "System", isDefault: true },
    { id: "access_target", name: "접근 Target", isDefault: true },
    { id: "purpose", name: "목적", isDefault: true },
    { id: "related_db_table", name: "연관 DB Table", isDefault: true },
];

// ========== Phase System (Support Steps) ==========

// Phase type definition - defines types of phases (main is always implicit)
export interface PhaseType {
    id: string;
    name: string;
    color: string;  // CSS color for visual distinction
    order: number;  // Display order
}

// Support relation - when a step supports another step in a specific phase
export interface SupportRelation {
    id: string;
    supporterStepId: string;  // The step that provides support
    targetStepId: string;     // The step being supported
    phaseId: string;          // Which phase this support belongs to
    createdAt: string;
}

// Generate unique ID for phases
export function generatePhaseId(): string {
    return `phase_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Generate unique ID for support relations
export function generateSupportId(): string {
    return `support_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Create a new phase type
export function createPhaseType(
    name: string,
    color: string,
    order: number
): PhaseType {
    return {
        id: generatePhaseId(),
        name,
        color,
        order,
    };
}

// Create a new support relation
export function createSupportRelation(
    supporterStepId: string,
    targetStepId: string,
    phaseId: string
): SupportRelation {
    return {
        id: generateSupportId(),
        supporterStepId,
        targetStepId,
        phaseId,
        createdAt: new Date().toISOString(),
    };
}

// ========== Project Workflow Data ==========

// Capture for a workflow step instance
export interface StepCapture {
    id: string;
    slideIndex: number;
    x: number;
    y: number;
    width: number;
    height: number;
    label?: string;
}

// Attachment (image or text) for a workflow step instance
export interface StepAttachment {
    id: string;
    type: 'image' | 'text';
    data?: string;  // Plain text for text type (image data is stored separately in attachments.db)
    imageId?: string;  // Reference to image in attachments.db (for image type)
    caption?: string;
    createdAt: string;
}

// Workflow Step Instance (added to a project's workflow)
export interface WorkflowStepInstance {
    id: string;
    stepId: string;  // Reference to WorkflowStepRow.id in settings
    captures: StepCapture[];
    attachments: StepAttachment[];
    order: number;
    createdAt: string;
}

// Project's Workflow Data
export interface ProjectWorkflowData {
    steps: WorkflowStepInstance[];
    // Core step instances - independent from regular workflow steps
    coreStepInstances?: CoreStepInstance[];
    // Phase types (user-defined phases, 'main' phase is implicit)
    phaseTypes?: PhaseType[];
    // Support relations - steps that support other steps in specific phases
    supportRelations?: SupportRelation[];
    createdAt?: string;
    updatedAt?: string;
}

// Helper function to create empty workflow data
export function createEmptyWorkflowData(): ProjectWorkflowData {
    return {
        steps: [],
        createdAt: new Date().toISOString(),
    };
}

// Generate unique ID for step instances
export function generateStepInstanceId(): string {
    return `step_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Generate unique ID for captures
export function generateStepCaptureId(): string {
    return `scap_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Generate unique ID for attachments
export function generateAttachmentId(): string {
    return `att_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Create a new step instance from a step definition
export function createStepInstance(
    stepId: string,
    order: number
): WorkflowStepInstance {
    return {
        id: generateStepInstanceId(),
        stepId,
        captures: [],
        attachments: [],
        order,
        createdAt: new Date().toISOString(),
    };
}

// Create a capture for a step
export function createStepCapture(
    slideIndex: number,
    x: number,
    y: number,
    width: number,
    height: number,
    label?: string
): StepCapture {
    return {
        id: generateStepCaptureId(),
        slideIndex,
        x,
        y,
        width,
        height,
        label,
    };
}

// Create an attachment
export function createAttachment(
    type: 'image' | 'text',
    dataOrImageId: string,
    caption?: string
): StepAttachment {
    const attachment: StepAttachment = {
        id: generateAttachmentId(),
        type,
        caption,
        createdAt: new Date().toISOString(),
    };

    if (type === 'image') {
        // For images, dataOrImageId is the imageId reference
        attachment.imageId = dataOrImageId;
    } else {
        // For text, dataOrImageId is the actual text content
        attachment.data = dataOrImageId;
    }

    return attachment;
}

// ========== Phase/Support Utility Functions ==========

/**
 * Get all support steps for a given target step
 */
export function getSupportSteps(
    targetStepId: string,
    supportRelations: SupportRelation[] | undefined
): SupportRelation[] {
    return (supportRelations ?? []).filter(r => r.targetStepId === targetStepId);
}

/**
 * Check if a step is a supporter (not in main flow, supports another step)
 */
export function isStepSupporter(
    stepId: string,
    supportRelations: SupportRelation[] | undefined
): boolean {
    return (supportRelations ?? []).some(r => r.supporterStepId === stepId);
}

/**
 * Get the support relation info for a supporter step
 */
export function getSupportInfo(
    stepId: string,
    supportRelations: SupportRelation[] | undefined
): SupportRelation | undefined {
    return (supportRelations ?? []).find(r => r.supporterStepId === stepId);
}

/**
 * Get main flow steps (steps that are not supporting other steps)
 */
export function getMainFlowSteps(
    steps: WorkflowStepInstance[],
    supportRelations: SupportRelation[] | undefined
): WorkflowStepInstance[] {
    const supporterIds = new Set((supportRelations ?? []).map(r => r.supporterStepId));
    return steps.filter(s => !supporterIds.has(s.id));
}

/**
 * Validate if a support relation can be created
 * Returns null if valid, or an error message if invalid
 */
export function validateSupportCreation(
    supporterStepId: string,
    targetStepId: string,
    steps: WorkflowStepInstance[],
    supportRelations: SupportRelation[] | undefined
): string | null {
    // Can't support yourself
    if (supporterStepId === targetStepId) {
        return "자기 자신을 지원할 수 없습니다.";
    }

    // Both steps must exist
    const supporter = steps.find(s => s.id === supporterStepId);
    const target = steps.find(s => s.id === targetStepId);

    if (!supporter || !target) {
        return "스텝을 찾을 수 없습니다.";
    }

    // Target can't be a supporter (no chaining)
    if (isStepSupporter(targetStepId, supportRelations)) {
        return "이미 지원 중인 스텝은 대상이 될 수 없습니다.";
    }

    // Supporter can't already be supporting
    if (isStepSupporter(supporterStepId, supportRelations)) {
        return "이미 다른 스텝을 지원 중입니다.";
    }

    return null;
}

/**
 * Add a support relation to workflow data
 * NOTE: If the supporter step was previously a target (had other steps supporting it),
 * those relations are automatically removed to prevent nested phase structures.
 */
export function addSupportRelation(
    workflowData: ProjectWorkflowData,
    supporterStepId: string,
    targetStepId: string,
    phaseId: string
): ProjectWorkflowData {
    const newRelation = createSupportRelation(supporterStepId, targetStepId, phaseId);

    // Remove any relations where the new supporter was previously a target
    // This prevents nested phase structures (e.g., if 5 supports 4, and 4 becomes supporter of 3,
    // we must release 5 because we don't allow nested phases)
    const cleanedRelations = (workflowData.supportRelations ?? []).filter(
        r => r.targetStepId !== supporterStepId
    );

    return {
        ...workflowData,
        supportRelations: [...cleanedRelations, newRelation],
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Remove a support relation from workflow data
 */
export function removeSupportRelation(
    workflowData: ProjectWorkflowData,
    supportRelationId: string
): ProjectWorkflowData {
    return {
        ...workflowData,
        supportRelations: (workflowData.supportRelations ?? []).filter(r => r.id !== supportRelationId),
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Remove support relation by supporter step ID
 */
export function removeSupportByStepId(
    workflowData: ProjectWorkflowData,
    supporterStepId: string
): ProjectWorkflowData {
    return {
        ...workflowData,
        supportRelations: (workflowData.supportRelations ?? []).filter(r => r.supporterStepId !== supporterStepId),
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Clean up orphaned support relations (when steps are deleted)
 */
export function cleanupOrphanedSupports(
    workflowData: ProjectWorkflowData
): ProjectWorkflowData {
    if (!workflowData.supportRelations) return workflowData;

    const stepIds = new Set(workflowData.steps.map(s => s.id));

    return {
        ...workflowData,
        supportRelations: workflowData.supportRelations.filter(r =>
            stepIds.has(r.supporterStepId) && stepIds.has(r.targetStepId)
        ),
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Add a phase type to workflow data
 */
export function addPhaseType(
    workflowData: ProjectWorkflowData,
    name: string,
    color: string
): ProjectWorkflowData {
    const existingPhases = workflowData.phaseTypes ?? [];
    const order = existingPhases.length;
    const newPhase = createPhaseType(name, color, order);

    return {
        ...workflowData,
        phaseTypes: [...existingPhases, newPhase],
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Remove a phase type from workflow data
 * Also removes all support relations using this phase
 */
export function removePhaseType(
    workflowData: ProjectWorkflowData,
    phaseId: string
): ProjectWorkflowData {
    return {
        ...workflowData,
        phaseTypes: (workflowData.phaseTypes ?? []).filter(p => p.id !== phaseId),
        supportRelations: (workflowData.supportRelations ?? []).filter(r => r.phaseId !== phaseId),
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Update a phase type
 */
export function updatePhaseType(
    workflowData: ProjectWorkflowData,
    phaseId: string,
    updates: Partial<Pick<PhaseType, 'name' | 'color'>>
): ProjectWorkflowData {
    return {
        ...workflowData,
        phaseTypes: (workflowData.phaseTypes ?? []).map(p =>
            p.id === phaseId ? { ...p, ...updates } : p
        ),
        updatedAt: new Date().toISOString(),
    };
}

// ========== Layout Functions (for Phase System) ==========

/**
 * Get steps grouped by target step
 * Returns main flow steps with their supporters
 */
export interface StepWithSupports {
    step: WorkflowStepInstance;
    supporters: {
        step: WorkflowStepInstance;
        relation: SupportRelation;
        phase: PhaseType | undefined;
    }[];
}

export function getStepsWithSupports(
    steps: WorkflowStepInstance[],
    supportRelations: SupportRelation[] | undefined,
    phaseTypes: PhaseType[] | undefined
): StepWithSupports[] {
    // Separate main flow from supporters
    const mainFlowSteps = getMainFlowSteps(steps, supportRelations);

    return mainFlowSteps.map(step => {
        const supports = getSupportSteps(step.id, supportRelations);
        return {
            step,
            supporters: supports.map(rel => ({
                step: steps.find(s => s.id === rel.supporterStepId)!,
                relation: rel,
                phase: (phaseTypes ?? []).find(p => p.id === rel.phaseId),
            })).filter(s => s.step !== undefined),
        };
    });
}

/**
 * Layout row for rendering with phase support
 */
export interface LayoutRow {
    mainStep: WorkflowStepInstance;
    supporters: {
        step: WorkflowStepInstance;
        relation: SupportRelation;
        phase: PhaseType | undefined;
    }[];
}

/**
 * Get layout rows for rendering (main steps with their supporters)
 */
export function getLayoutRows(
    steps: WorkflowStepInstance[],
    supportRelations: SupportRelation[] | undefined,
    phaseTypes: PhaseType[] | undefined
): LayoutRow[] {
    const stepsWithSupports = getStepsWithSupports(
        steps,
        supportRelations,
        phaseTypes
    );

    return stepsWithSupports.map(({ step, supporters }) => ({
        mainStep: step,
        supporters,
    }));
}

/**
 * Get all phase types from workflow data (including implicit 'main' phase info)
 */
export function getAllPhaseTypes(workflowData: ProjectWorkflowData): PhaseType[] {
    return workflowData.phaseTypes ?? [];
}

/**
 * Get phase by ID
 */
export function getPhaseById(
    phaseId: string,
    phaseTypes: PhaseType[] | undefined
): PhaseType | undefined {
    return (phaseTypes ?? []).find(p => p.id === phaseId);
}
