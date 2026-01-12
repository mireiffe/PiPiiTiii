/**
 * Workflow actions and conditions type definitions
 */

export interface WorkflowActionParam {
    id: string;
    name: string;
    required: boolean;
    param_type?: string;  // "selection" or "description"
    selection_values?: string[];  // For selection type
}

export interface WorkflowAction {
    id: string;
    name: string;
    params: WorkflowActionParam[];
}

export interface WorkflowCondition {
    id: string;
    name: string;
    params: WorkflowActionParam[];
}
