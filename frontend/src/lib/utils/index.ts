/**
 * Centralized utility exports
 */

// ID generation
export {
    generateId,
    createId,
    // Legacy exports for backward compatibility
    generateEvidenceId,
    generateCauseImageId,
    generateActionCaptureId,
    generateCoreStepId,
    generateCoreStepPresetId,
    generateCoreStepInstanceId,
    generatePhaseId,
    generateSupportId,
    generateStepInstanceId,
    generateStepCaptureId,
    generateAttachmentId,
    generateWorkflowId,
} from './id';
export type { IdPrefix } from './id';

// List operations
export {
    moveUp,
    moveDown,
    removeAt,
    removeWhere,
    append,
    prepend,
    insertAt,
    updateAt,
    updateWhere,
    reorder,
    updateOrderField,
    createListManager,
    findById,
    findIndexById,
    removeById,
    updateById,
} from './listOperations';
