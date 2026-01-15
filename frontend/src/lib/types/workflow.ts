/**
 * Workflow step type definitions
 */

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

// Step Container Definition (settings)
export interface StepContainer {
    id: string;
    name: string;
    order: number;
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
    containerId?: string;  // Reference to StepContainer.id (optional, null = uncategorized)
    captures: StepCapture[];
    attachments: StepAttachment[];
    order: number;
    createdAt: string;
}

// Project's Workflow Data
export interface ProjectWorkflowData {
    steps: WorkflowStepInstance[];
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

// Generate unique ID for containers
export function generateContainerId(): string {
    return `cont_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
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
