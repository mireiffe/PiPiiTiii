/**
 * Workflow step type definitions
 */

// ========== Core Step Definitions ==========

// Allowed input types for Core Step presets
export type CoreStepInputType = 'capture' | 'text' | 'image_clipboard';

// LLM Auto-Generation Config for Core Step Presets
export interface LLMAutoGenConfig {
    enabled: boolean;
    userPrompt: string;
}

// Core Step Preset Field Definition
export interface CoreStepPreset {
    id: string;
    name: string;
    allowedTypes: CoreStepInputType[];  // Which input types are allowed for this preset
    order: number;
    defaultMetadataKey?: string;  // Default phenomenon attribute key for caption default value
    llmAutoGen?: LLMAutoGenConfig;  // LLM auto-generation config for this preset's text input
}

// Core Step Definition (defined in settings)
export interface CoreStepDefinition {
    id: string;
    name: string;
    presets: CoreStepPreset[];
    requiresKeyStepLinking: boolean;  // Whether this Core Step requires linking to prior key steps
    llmSystemPrompt?: string;  // Shared system prompt for LLM auto-generation across all presets
    createdAt: string;
}

// Single capture value within a Core Step preset (supports multiple captures per preset)
export interface CoreStepCaptureValue {
    id: string;
    slideIndex: number;
    x: number;
    y: number;
    width: number;
    height: number;
    label?: string;
    caption?: string;
}

// Core Step Preset Value (the actual input for a preset)
export interface CoreStepPresetValue {
    presetId: string;
    type: CoreStepInputType;
    // Value depends on type:
    // - capture: captureValues array (multiple captures per preset)
    // - text: string
    // - image_clipboard: imageId reference
    captureValue?: {  // Legacy single capture (migrated to captureValues on load)
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
        label?: string;
    };
    captureValues?: CoreStepCaptureValue[];  // Multiple captures per preset
    textValue?: string;
    imageId?: string;  // Reference to image in attachments.db
    imageCaption?: string;  // Caption for text and image_clipboard types
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

// Generate unique ID for core step capture values
export function generateCoreStepCaptureId(): string {
    return `cscap_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Create a new core step definition
export function createCoreStepDefinition(name: string, requiresKeyStepLinking: boolean = false): CoreStepDefinition {
    return {
        id: generateCoreStepId(),
        name,
        presets: [],
        requiresKeyStepLinking,
        createdAt: new Date().toISOString(),
    };
}

// Create a new core step preset
export function createCoreStepPreset(
    name: string,
    allowedTypes: CoreStepInputType[],
    order: number,
    defaultMetadataKey?: string
): CoreStepPreset {
    const preset: CoreStepPreset = {
        id: generateCoreStepPresetId(),
        name,
        allowedTypes,
        order,
    };
    if (defaultMetadataKey) {
        preset.defaultMetadataKey = defaultMetadataKey;
    }
    return preset;
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

// ========== Key Step Linking ==========

// A single key step link with priority
export interface KeyStepLink {
    stepId: string;              // ID of the linked step (UnifiedStepItem.id)
    priority: number;            // Priority rank (1 = highest, ties allowed)
}

// Key step linking data for a Core Step instance
export interface KeyStepLinkingData {
    coreStepInstanceId: string;  // The Core Step instance this links to
    linkedSteps: KeyStepLink[];  // Ordered list of linked steps with priorities
    confirmedAt: string;         // When the linking was confirmed
}

// Generate unique ID for key step linking data
export function generateKeyStepLinkId(): string {
    return `ksl_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
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
    steps: WorkflowSteps;  // Own step definitions
    coreSteps?: CoreStepsSettings;  // Core steps defined for this workflow
    createdAt: string;
}

// Workflow Settings Container
export interface WorkflowSettings {
    workflows: WorkflowDefinition[];
    phaseTypes: PhaseType[];
}

// Generate unique ID for workflow definitions
export function generateWorkflowId(): string {
    return `wf_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Default columns for workflow steps
export const DEFAULT_WORKFLOW_COLUMNS: WorkflowStepColumn[] = [
    { id: "step_category", name: "스텝 구분", isDefault: true },
    { id: "system", name: "System", isDefault: true },
    { id: "access_target", name: "접근 Target", isDefault: true },
    { id: "purpose", name: "목적", isDefault: true },
    { id: "related_db_table", name: "연관 DB Table", isDefault: true },
];

// Create a new workflow definition
export function createWorkflowDefinition(
    name: string,
    order: number
): WorkflowDefinition {
    return {
        id: generateWorkflowId(),
        name,
        order,
        steps: { columns: [...DEFAULT_WORKFLOW_COLUMNS], rows: [] },
        createdAt: new Date().toISOString(),
    };
}

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

// ========== Unified Step System ==========

// Unified Step type discriminator
export type UnifiedStepType = 'core' | 'regular';

// Unified Step Item - combines Core and Regular steps into single ordered list
export interface UnifiedStepItem {
    id: string;
    type: UnifiedStepType;
    order: number;
    createdAt: string;
    // Core Step specific fields (when type === 'core')
    coreStepId?: string;
    presetValues?: CoreStepPresetValue[];
    // Regular Step specific fields (when type === 'regular')
    stepId?: string;
    captures?: StepCapture[];
    attachments?: StepAttachment[];
}

// Generate unique ID for unified step items
export function generateUnifiedStepId(): string {
    return `us_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Core Step completion status
export interface CoreStepCompletionStatus {
    isComplete: boolean;
    addedIds: Set<string>;
    missingDefinitions: CoreStepDefinition[];
}

/**
 * Check if all required Core Steps have been added
 */
export function checkCoreStepCompletion(
    unifiedSteps: UnifiedStepItem[],
    definitions: CoreStepDefinition[]
): CoreStepCompletionStatus {
    const coreSteps = unifiedSteps.filter(s => s.type === 'core');
    const addedIds = new Set(coreSteps.map(cs => cs.coreStepId!).filter(Boolean));
    const missingDefinitions = definitions.filter(def => !addedIds.has(def.id));

    return {
        isComplete: missingDefinitions.length === 0 && definitions.length > 0,
        addedIds,
        missingDefinitions,
    };
}

// Validation result for position checks
export interface PositionValidationResult {
    isValid: boolean;
    errorMessage: string | null;
}

/**
 * Validate that first and last steps are Core Steps
 */
export function validateFirstLastCore(
    steps: UnifiedStepItem[]
): PositionValidationResult {
    if (steps.length === 0) {
        return { isValid: true, errorMessage: null };
    }

    const first = steps[0];
    const last = steps[steps.length - 1];

    if (first.type !== 'core') {
        return {
            isValid: false,
            errorMessage: '첫 번째 스텝은 반드시 Core Step이어야 합니다.',
        };
    }

    if (last.type !== 'core') {
        return {
            isValid: false,
            errorMessage: '마지막 스텝은 반드시 Core Step이어야 합니다.',
        };
    }

    return { isValid: true, errorMessage: null };
}

/**
 * Validate a reorder operation before committing
 * Simulates the reorder and checks if result is valid
 */
export function validateReorder(
    steps: UnifiedStepItem[],
    fromIndex: number,
    toIndex: number
): PositionValidationResult {
    if (fromIndex === toIndex) {
        return { isValid: true, errorMessage: null };
    }

    // Simulate the reorder
    const simulatedSteps = [...steps];
    const [removed] = simulatedSteps.splice(fromIndex, 1);
    simulatedSteps.splice(toIndex, 0, removed);

    // Validate the result
    return validateFirstLastCore(simulatedSteps);
}

/**
 * Validate deletion of a step
 * Checks if deletion would leave first/last as non-core step
 */
export function validateDeletion(
    steps: UnifiedStepItem[],
    deleteIndex: number
): PositionValidationResult {
    if (steps.length <= 1) {
        return { isValid: true, errorMessage: null };
    }

    // Simulate the deletion
    const simulatedSteps = steps.filter((_, idx) => idx !== deleteIndex);

    if (simulatedSteps.length === 0) {
        return { isValid: true, errorMessage: null };
    }

    // Validate the result
    return validateFirstLastCore(simulatedSteps);
}

/**
 * Create a unified step item from a Core Step instance
 */
export function createUnifiedCoreStep(
    coreStepId: string,
    presetValues: CoreStepPresetValue[],
    order: number
): UnifiedStepItem {
    return {
        id: generateUnifiedStepId(),
        type: 'core',
        order,
        createdAt: new Date().toISOString(),
        coreStepId,
        presetValues,
    };
}

/**
 * Create a unified step item from a Regular Step
 */
export function createUnifiedRegularStep(
    stepId: string,
    order: number
): UnifiedStepItem {
    return {
        id: generateUnifiedStepId(),
        type: 'regular',
        order,
        createdAt: new Date().toISOString(),
        stepId,
        captures: [],
        attachments: [],
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
    // Core step instances - independent from regular workflow steps (legacy, for backward compat)
    coreStepInstances?: CoreStepInstance[];
    // Unified steps - new integrated list of Core + Regular steps
    unifiedSteps?: UnifiedStepItem[];
    // Phase types (user-defined phases, 'main' phase is implicit)
    phaseTypes?: PhaseType[];
    // Support relations - steps that support other steps in specific phases
    supportRelations?: SupportRelation[];
    // Key step linking data - links Core Steps to their key predecessor steps
    keyStepLinks?: KeyStepLinkingData[];
    // Workflow confirmation status
    isConfirmed?: boolean;
    confirmedAt?: string;
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
 * Build a map from unified step ID to its 1-based display number.
 * This is the single source of truth for step numbering across the UI.
 * All components that need to display step numbers should use this map
 * instead of computing their own indices.
 */
export function buildUnifiedDisplayMap(
    sortedUnifiedSteps: UnifiedStepItem[]
): Map<string, number> {
    const map = new Map<string, number>();
    sortedUnifiedSteps.forEach((step, idx) => {
        map.set(step.id, idx + 1);
    });
    return map;
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

// ========== Migration Functions ==========

/**
 * Migrate legacy data (separate steps + coreStepInstances) to unified steps
 * This is called when loading workflow data that doesn't have unifiedSteps yet
 */
export function migrateToUnifiedSteps(
    data: ProjectWorkflowData
): ProjectWorkflowData {
    // If already has unified steps and they're not empty, skip migration
    if (data.unifiedSteps && data.unifiedSteps.length > 0) {
        return data;
    }

    const unifiedSteps: UnifiedStepItem[] = [];

    // Convert core step instances first (they go at the beginning)
    const sortedCoreSteps = [...(data.coreStepInstances ?? [])].sort((a, b) => a.order - b.order);
    sortedCoreSteps.forEach((cs, idx) => {
        unifiedSteps.push({
            id: generateUnifiedStepId(),
            type: 'core',
            order: idx,
            createdAt: cs.createdAt,
            coreStepId: cs.coreStepId,
            presetValues: cs.presetValues,
        });
    });

    // Then add regular steps
    const sortedSteps = [...(data.steps ?? [])].sort((a, b) => a.order - b.order);
    sortedSteps.forEach((s, idx) => {
        unifiedSteps.push({
            id: generateUnifiedStepId(),
            type: 'regular',
            order: sortedCoreSteps.length + idx,
            createdAt: s.createdAt,
            stepId: s.stepId,
            captures: s.captures,
            attachments: s.attachments,
        });
    });

    return {
        ...data,
        unifiedSteps,
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Convert unified steps back to legacy format for backward compatibility
 * This can be used when saving to ensure old systems can read the data
 */
export function syncUnifiedToLegacy(
    data: ProjectWorkflowData
): ProjectWorkflowData {
    if (!data.unifiedSteps) {
        return data;
    }

    const coreStepInstances: CoreStepInstance[] = [];
    const steps: WorkflowStepInstance[] = [];

    data.unifiedSteps.forEach((item, idx) => {
        if (item.type === 'core') {
            coreStepInstances.push({
                id: item.id,
                coreStepId: item.coreStepId!,
                presetValues: item.presetValues ?? [],
                order: coreStepInstances.length,
                createdAt: item.createdAt,
            });
        } else {
            steps.push({
                id: item.id,
                stepId: item.stepId!,
                captures: item.captures ?? [],
                attachments: item.attachments ?? [],
                order: steps.length,
                createdAt: item.createdAt,
            });
        }
    });

    return {
        ...data,
        steps,
        coreStepInstances,
        updatedAt: new Date().toISOString(),
    };
}

// ========== Key Step Linking Functions ==========

/**
 * Key step linking completion status
 */
export interface KeyStepLinkingStatus {
    isComplete: boolean;
    pendingCoreSteps: UnifiedStepItem[];  // Core Steps that need linking but haven't been linked yet
}

/**
 * Check if all Core Steps requiring linking have been linked
 */
export function checkKeyStepLinkingComplete(
    unifiedSteps: UnifiedStepItem[],
    definitions: CoreStepDefinition[],
    keyStepLinks: KeyStepLinkingData[] | undefined
): KeyStepLinkingStatus {
    const coreStepsRequiringLinking = unifiedSteps
        .filter(s => s.type === 'core')
        .filter(s => {
            const def = definitions.find(d => d.id === s.coreStepId);
            return def?.requiresKeyStepLinking;
        });

    const linkedCoreStepIds = new Set((keyStepLinks ?? []).map(l => l.coreStepInstanceId));
    const pendingCoreSteps = coreStepsRequiringLinking.filter(cs => !linkedCoreStepIds.has(cs.id));

    return {
        isComplete: pendingCoreSteps.length === 0,
        pendingCoreSteps,
    };
}

/**
 * Get steps available for linking (steps before the target Core Step)
 */
export function getAvailableStepsForLinking(
    unifiedSteps: UnifiedStepItem[],
    targetCoreStepId: string
): UnifiedStepItem[] {
    const sortedSteps = [...unifiedSteps].sort((a, b) => a.order - b.order);
    const targetIndex = sortedSteps.findIndex(s => s.id === targetCoreStepId);
    if (targetIndex <= 0) return [];

    // Return all steps before the target Core Step
    return sortedSteps.slice(0, targetIndex);
}

/**
 * Get key step links for a specific Core Step instance
 */
export function getKeyStepLinksForCoreStep(
    coreStepInstanceId: string,
    keyStepLinks: KeyStepLinkingData[] | undefined
): KeyStepLinkingData | undefined {
    return (keyStepLinks ?? []).find(l => l.coreStepInstanceId === coreStepInstanceId);
}

/**
 * Save key step links for a Core Step
 */
export function saveKeyStepLinks(
    workflowData: ProjectWorkflowData,
    coreStepInstanceId: string,
    linkedSteps: KeyStepLink[]
): ProjectWorkflowData {
    const existingLinks = workflowData.keyStepLinks ?? [];
    const filteredLinks = existingLinks.filter(l => l.coreStepInstanceId !== coreStepInstanceId);

    const newLinkData: KeyStepLinkingData = {
        coreStepInstanceId,
        linkedSteps,
        confirmedAt: new Date().toISOString(),
    };

    return {
        ...workflowData,
        keyStepLinks: [...filteredLinks, newLinkData],
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Confirm workflow (mark as confirmed)
 */
export function confirmWorkflow(workflowData: ProjectWorkflowData): ProjectWorkflowData {
    return {
        ...workflowData,
        isConfirmed: true,
        confirmedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Unconfirm workflow (allow editing again)
 */
export function unconfirmWorkflow(workflowData: ProjectWorkflowData): ProjectWorkflowData {
    return {
        ...workflowData,
        isConfirmed: false,
        confirmedAt: undefined,
        updatedAt: new Date().toISOString(),
    };
}
