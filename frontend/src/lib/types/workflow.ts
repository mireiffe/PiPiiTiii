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

// ========== Container Branch (Multi-Column Flow) ==========

// Branch point within a container
// When a step starts a new branch, it and subsequent steps in that container
// are displayed in a new column to the right of the parent step
export interface ContainerBranch {
    id: string;
    branchStartStepId: string;  // The step that starts this branch
    parentStepId: string;       // The step this branch is positioned next to (on the right)
    createdAt: string;
}

// Generate unique ID for branches
export function generateBranchId(): string {
    return `branch_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// Create a new branch
export function createContainerBranch(
    branchStartStepId: string,
    parentStepId: string
): ContainerBranch {
    return {
        id: generateBranchId(),
        branchStartStepId,
        parentStepId,
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
    containerId?: string;  // Reference to StepContainer.id (optional, null = uncategorized)
    captures: StepCapture[];
    attachments: StepAttachment[];
    order: number;
    createdAt: string;
}

// Project's Workflow Data
export interface ProjectWorkflowData {
    steps: WorkflowStepInstance[];
    // Container branches for multi-column layout
    // Key: containerId (or '__uncategorized__' for uncategorized steps)
    containerBranches?: Record<string, ContainerBranch[]>;
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

// ========== Branch Utility Functions ==========

/**
 * Get the column index for a step within a container
 * Column 0 is the default (left-most), higher indices are branches to the right
 */
export function getStepColumnIndex(
    stepId: string,
    containerId: string | undefined,
    steps: WorkflowStepInstance[],
    containerBranches?: Record<string, ContainerBranch[]>
): number {
    const containerKey = containerId ?? '__uncategorized__';
    const branches = containerBranches?.[containerKey] ?? [];

    if (branches.length === 0) return 0;

    // Get steps in this container in order
    const containerSteps = steps.filter(s =>
        (s.containerId ?? '__uncategorized__') === containerKey
    );

    const stepIndex = containerSteps.findIndex(s => s.id === stepId);
    if (stepIndex === -1) return 0;

    // Find which branch this step belongs to (if any)
    // A step belongs to a branch if it is the branch start or comes after it in the container
    let currentColumn = 0;

    for (const branch of branches) {
        const branchStartIndex = containerSteps.findIndex(s => s.id === branch.branchStartStepId);
        if (branchStartIndex !== -1 && stepIndex >= branchStartIndex) {
            currentColumn++;
        }
    }

    return currentColumn;
}

/**
 * Get all steps organized by columns within a container
 */
export interface ContainerColumn {
    columnIndex: number;
    steps: WorkflowStepInstance[];
    branchInfo?: ContainerBranch;  // Info about the branch that starts this column (if not column 0)
}

/**
 * Layout row for rendering - supports paired (side-by-side) display
 * When branches exist, first steps of each branch are paired with parent
 */
export interface ContainerLayoutRow {
    type: 'single' | 'paired';
    // For single: one step
    // For paired: first step is parent, rest are branch starts
    cells: {
        columnIndex: number;
        step: WorkflowStepInstance | null;  // null for empty cell
        isBranchStart: boolean;
        hideBadge?: boolean;  // Hide the step number badge
    }[];
}

/**
 * Get container layout as rows for rendering
 * Branch first steps are placed in the same row as their parent step
 */
export function getContainerLayoutRows(
    containerId: string | undefined,
    steps: WorkflowStepInstance[],
    containerBranches?: Record<string, ContainerBranch[]>
): { rows: ContainerLayoutRow[], columns: ContainerColumn[] } {
    const columns = getContainerColumns(containerId, steps, containerBranches);

    if (columns.length === 0 || columns.every(c => c.steps.length === 0)) {
        return { rows: [], columns };
    }

    // For single column, just return simple rows
    if (columns.length === 1) {
        const rows: ContainerLayoutRow[] = columns[0].steps.map(step => ({
            type: 'single' as const,
            cells: [{ columnIndex: 0, step, isBranchStart: false }]
        }));
        return { rows, columns };
    }

    // Build paired rows
    // First row: parent step (col 0, index 0) paired with branch start steps
    // Subsequent rows: remaining steps in each column
    const rows: ContainerLayoutRow[] = [];

    // Find the maximum column height (excluding first step which goes to row 0)
    const maxHeight = Math.max(...columns.map((col, idx) =>
        idx === 0 ? col.steps.length : col.steps.length - 1  // branch columns have first step in row 0
    ));

    // Row 0: Parent step + all branch first steps
    const firstRow: ContainerLayoutRow = {
        type: 'paired',
        cells: columns.map((col, colIdx) => ({
            columnIndex: colIdx,
            step: col.steps[0] ?? null,
            isBranchStart: colIdx > 0,
            hideBadge: colIdx > 0,  // Hide badge for branch start steps
        }))
    };
    rows.push(firstRow);

    // Subsequent rows: steps from index 1 onwards (for col 0) or index 1 onwards (for branch cols)
    for (let rowIdx = 1; rowIdx <= maxHeight; rowIdx++) {
        const row: ContainerLayoutRow = {
            type: 'paired',
            cells: columns.map((col, colIdx) => {
                // For column 0, use rowIdx directly
                // For branch columns, use rowIdx (since first step is in row 0)
                const stepIdx = rowIdx;
                const step = col.steps[stepIdx] ?? null;
                return {
                    columnIndex: colIdx,
                    step,
                    isBranchStart: false,
                };
            })
        };
        // Only add row if it has at least one step
        if (row.cells.some(c => c.step !== null)) {
            rows.push(row);
        }
    }

    return { rows, columns };
}

export function getContainerColumns(
    containerId: string | undefined,
    steps: WorkflowStepInstance[],
    containerBranches?: Record<string, ContainerBranch[]>
): ContainerColumn[] {
    const containerKey = containerId ?? '__uncategorized__';
    const branches = containerBranches?.[containerKey] ?? [];

    // Get steps in this container in order
    const containerSteps = steps.filter(s =>
        (s.containerId ?? '__uncategorized__') === containerKey
    );

    if (containerSteps.length === 0) {
        return [{ columnIndex: 0, steps: [] }];
    }

    if (branches.length === 0) {
        return [{ columnIndex: 0, steps: containerSteps }];
    }

    // Sort branches by their start position
    const sortedBranches = [...branches].sort((a, b) => {
        const aIdx = containerSteps.findIndex(s => s.id === a.branchStartStepId);
        const bIdx = containerSteps.findIndex(s => s.id === b.branchStartStepId);
        return aIdx - bIdx;
    });

    // Build columns
    const columns: ContainerColumn[] = [];
    let currentColumnSteps: WorkflowStepInstance[] = [];
    let branchIndex = 0;

    for (let i = 0; i < containerSteps.length; i++) {
        const step = containerSteps[i];

        // Check if this step starts a new branch
        if (branchIndex < sortedBranches.length &&
            step.id === sortedBranches[branchIndex].branchStartStepId) {
            // Save current column
            if (i > 0) {
                columns.push({
                    columnIndex: columns.length,
                    steps: currentColumnSteps,
                    branchInfo: columns.length > 0 ? sortedBranches[columns.length - 1] : undefined,
                });
            }
            // Start new column
            currentColumnSteps = [step];
            branchIndex++;
        } else {
            currentColumnSteps.push(step);
        }
    }

    // Add last column
    columns.push({
        columnIndex: columns.length,
        steps: currentColumnSteps,
        branchInfo: columns.length > 0 ? sortedBranches[columns.length - 1] : undefined,
    });

    return columns;
}

/**
 * Validate if a branch can be created (left-to-right order only)
 * Returns null if valid, or an error message if invalid
 */
export function validateBranchCreation(
    branchStartStepId: string,
    parentStepId: string,
    containerId: string | undefined,
    steps: WorkflowStepInstance[]
): string | null {
    const containerKey = containerId ?? '__uncategorized__';

    // Get steps in this container in order
    const containerSteps = steps.filter(s =>
        (s.containerId ?? '__uncategorized__') === containerKey
    );

    const branchStartIndex = containerSteps.findIndex(s => s.id === branchStartStepId);
    const parentIndex = containerSteps.findIndex(s => s.id === parentStepId);

    if (branchStartIndex === -1 || parentIndex === -1) {
        return "스텝을 찾을 수 없습니다.";
    }

    // Branch start must come AFTER parent (left-to-right order)
    if (branchStartIndex <= parentIndex) {
        return "분기는 왼쪽에서 오른쪽 순서로만 생성할 수 있습니다.";
    }

    return null;
}

/**
 * Add a branch to workflow data
 */
export function addBranch(
    workflowData: ProjectWorkflowData,
    containerId: string | undefined,
    branchStartStepId: string,
    parentStepId: string
): ProjectWorkflowData {
    const containerKey = containerId ?? '__uncategorized__';
    const branches = workflowData.containerBranches ?? {};
    const containerBranches = branches[containerKey] ?? [];

    const newBranch = createContainerBranch(branchStartStepId, parentStepId);

    return {
        ...workflowData,
        containerBranches: {
            ...branches,
            [containerKey]: [...containerBranches, newBranch],
        },
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Remove a branch from workflow data
 */
export function removeBranch(
    workflowData: ProjectWorkflowData,
    containerId: string | undefined,
    branchId: string
): ProjectWorkflowData {
    const containerKey = containerId ?? '__uncategorized__';
    const branches = workflowData.containerBranches ?? {};
    const containerBranches = branches[containerKey] ?? [];

    return {
        ...workflowData,
        containerBranches: {
            ...branches,
            [containerKey]: containerBranches.filter(b => b.id !== branchId),
        },
        updatedAt: new Date().toISOString(),
    };
}

/**
 * Clean up orphaned branches (when steps are deleted or moved)
 */
export function cleanupOrphanedBranches(
    workflowData: ProjectWorkflowData
): ProjectWorkflowData {
    if (!workflowData.containerBranches) return workflowData;

    const stepIds = new Set(workflowData.steps.map(s => s.id));
    const stepContainerMap = new Map(workflowData.steps.map(s => [s.id, s.containerId ?? '__uncategorized__']));

    const cleanedBranches: Record<string, ContainerBranch[]> = {};

    for (const [containerKey, branches] of Object.entries(workflowData.containerBranches)) {
        cleanedBranches[containerKey] = branches.filter(branch => {
            // Both steps must exist
            if (!stepIds.has(branch.branchStartStepId) || !stepIds.has(branch.parentStepId)) {
                return false;
            }
            // Both steps must be in this container
            if (stepContainerMap.get(branch.branchStartStepId) !== containerKey ||
                stepContainerMap.get(branch.parentStepId) !== containerKey) {
                return false;
            }
            return true;
        });
    }

    return {
        ...workflowData,
        containerBranches: cleanedBranches,
        updatedAt: new Date().toISOString(),
    };
}
