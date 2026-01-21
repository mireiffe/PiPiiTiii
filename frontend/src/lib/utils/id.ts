/**
 * Centralized ID generation utility
 *
 * Consolidates all ID generation patterns from:
 * - phenomenon.ts: generateEvidenceId, generateCauseImageId, generateActionCaptureId
 * - workflow.ts: generateCoreStepId, generateCoreStepPresetId, generateCoreStepInstanceId,
 *                generatePhaseId, generateSupportId, generateStepInstanceId,
 *                generateStepCaptureId, generateAttachmentId, generateWorkflowId
 */

/**
 * Generate a unique ID with a given prefix
 * Format: {prefix}_{timestamp}_{random7chars}
 */
export function generateId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Type-safe ID generators for specific domains
export type IdPrefix =
    | 'ev'       // Evidence
    | 'img'      // Cause Image
    | 'acap'     // Action Capture
    | 'cs'       // Core Step Definition
    | 'csp'      // Core Step Preset
    | 'csi'      // Core Step Instance
    | 'phase'    // Phase
    | 'support'  // Support Relation
    | 'step'     // Step Instance
    | 'scap'     // Step Capture
    | 'att'      // Attachment
    | 'wf'       // Workflow
    | 'row';     // Row (for step definitions)

/**
 * Domain-specific ID generators for better code clarity
 */
export const createId = {
    evidence: () => generateId('ev'),
    causeImage: () => generateId('img'),
    actionCapture: () => generateId('acap'),
    coreStep: () => generateId('cs'),
    coreStepPreset: () => generateId('csp'),
    coreStepInstance: () => generateId('csi'),
    phase: () => generateId('phase'),
    support: () => generateId('support'),
    stepInstance: () => generateId('step'),
    stepCapture: () => generateId('scap'),
    attachment: () => generateId('att'),
    workflow: () => generateId('wf'),
    row: () => generateId('row'),
} as const;

// Re-export legacy function names for backward compatibility
// These can be gradually migrated to use createId.xxx
export const generateEvidenceId = createId.evidence;
export const generateCauseImageId = createId.causeImage;
export const generateActionCaptureId = createId.actionCapture;
export const generateCoreStepId = createId.coreStep;
export const generateCoreStepPresetId = createId.coreStepPreset;
export const generateCoreStepInstanceId = createId.coreStepInstance;
export const generatePhaseId = createId.phase;
export const generateSupportId = createId.support;
export const generateStepInstanceId = createId.stepInstance;
export const generateStepCaptureId = createId.stepCapture;
export const generateAttachmentId = createId.attachment;
export const generateWorkflowId = createId.workflow;
