/**
 * Project API
 *
 * API functions for project management, workflows, and attachments.
 */

import { apiFetch, BASE_URL } from './client';
import type { ProjectWorkflowData } from '$lib/types/workflow';
import type { ProjectKeyInfoData } from '$lib/types/keyInfo';
import type {
    ShapePosition,
    ShapeDescription,
    Settings,
    SummaryData,
    WorkflowsResponse,
    AttributeDefinition,
    Project,
    ProjectListItem,
} from '$lib/types/api';

// ========== Project Management ==========

export async function fetchProjects(): Promise<Response> {
    return apiFetch('/api/projects');
}

export async function fetchProject(id: string): Promise<Response> {
    return apiFetch(`/api/project/${id}`);
}

export async function uploadProject(file: File): Promise<Response> {
    const formData = new FormData();
    formData.append('file', file);
    return apiFetch('/api/upload', {
        method: 'POST',
        body: formData,
    });
}

export async function fetchProjectStatus(id: string): Promise<Response> {
    return apiFetch(`/api/project/${id}/status`);
}

// ========== Shape Operations ==========

export async function updateShapePositions(id: string, updates: ShapePosition[]): Promise<Response> {
    return apiFetch(`/api/project/${id}/update_positions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates }),
    });
}

export async function updateShapeDescription(id: string, data: ShapeDescription): Promise<Response> {
    return apiFetch(`/api/project/${id}/update_description`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
}

// ========== Reparse Operations ==========

export async function reparseProject(id: string): Promise<Response> {
    return apiFetch(`/api/project/${id}/reparse_all`, {
        method: 'POST',
    });
}

export async function reparseSlide(id: string, slideIndex: number): Promise<Response> {
    return apiFetch(`/api/project/${id}/slides/${slideIndex}/reparse`, {
        method: 'POST',
    });
}

// ========== Download ==========

export async function downloadProject(id: string): Promise<Response> {
    const res = await apiFetch(`/api/project/${id}/download`);
    if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const contentDisposition = res.headers.get('Content-Disposition');
        let filename = 'presentation.pptx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?([^"]+)"?/);
            if (match && match[1]) {
                filename = match[1];
            }
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
    return res;
}

// ========== Filters & Settings ==========

export async function fetchFilters(): Promise<Response> {
    return apiFetch('/api/filters');
}

export async function fetchSettings(): Promise<Response> {
    return apiFetch('/api/settings');
}

export async function updateSettings(settings: Settings): Promise<Response> {
    return apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
    });
}

// ========== Summary ==========

export async function fetchProjectSummary(id: string): Promise<Response> {
    return apiFetch(`/api/project/${id}/summary`);
}

export async function updateProjectSummary(id: string, data: Record<string, string>): Promise<Response> {
    return apiFetch(`/api/project/${id}/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data }),
    });
}

export async function generateSummaryStream(
    projectId: string,
    fieldId: string,
    slideIndices: number[],
): Promise<ReadableStream<Uint8Array> | null> {
    const response = await apiFetch(`/api/project/${projectId}/generate_summary/${fieldId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slide_indices: slideIndices }),
    });

    if (!response.ok) {
        throw new Error(`Failed to generate summary: ${response.statusText}`);
    }

    return response.body;
}

export async function generateTextStream(
    projectId: string,
    systemPrompt: string,
    userPrompt: string,
    slideIndices: number[],
): Promise<ReadableStream<Uint8Array> | null> {
    const response = await apiFetch(`/api/project/${projectId}/generate_text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            system_prompt: systemPrompt,
            user_prompt: userPrompt,
            slide_indices: slideIndices,
        }),
    });

    if (!response.ok) {
        throw new Error(`Failed to generate text: ${response.statusText}`);
    }

    return response.body;
}

export async function updateProjectSummaryLLM(id: string, fieldId: string, content: string): Promise<Response> {
    return apiFetch(`/api/project/${id}/summary_llm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_id: fieldId, content }),
    });
}

export async function fetchPromptVersion(): Promise<Response> {
    return apiFetch('/api/settings/prompt_version');
}

export async function fetchProjectsSummaryStatus(): Promise<Response> {
    return apiFetch('/api/projects/summary_status');
}

export async function batchGenerateSummary(
    projectIds: string[],
    slideIndices?: number[],
): Promise<ReadableStream<Uint8Array> | null> {
    const response = await apiFetch('/api/projects/batch_generate_summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_ids: projectIds, slide_indices: slideIndices }),
    });

    if (!response.ok) {
        throw new Error(`Failed to batch generate summary: ${response.statusText}`);
    }

    return response.body;
}

export async function updateProjectPromptVersion(id: string): Promise<Response> {
    return apiFetch(`/api/project/${id}/update_prompt_version`, {
        method: 'POST',
    });
}

// ========== Workflow Validation ==========

export interface WorkflowIssue {
    type: string;
    workflow_id: string;
    step_id: string;
}

export interface InvalidProject {
    project_id: string;
    issues: WorkflowIssue[];
}

export async function validateWorkflows(): Promise<Response> {
    return apiFetch('/api/workflow/validate');
}

/**
 * Remove invalid steps from a project's workflows
 */
export async function removeInvalidWorkflowSteps(
    projectId: string,
    issues: { workflow_id: string; step_id: string }[],
): Promise<Response> {
    return apiFetch('/api/workflow/remove-invalid-steps', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, issues }),
    });
}

/**
 * Fetch keyinfo status for all projects
 * Returns: { not_started_project_ids: string[], in_progress_project_ids: string[] }
 */
export async function fetchKeyinfoStatus(): Promise<Response> {
    return apiFetch('/api/projects/keyinfo-status');
}

/**
 * Fetch usage counts for each keyinfo item across all projects
 * Returns: { counts: { "categoryId_itemId": number, ... } }
 */
export async function fetchKeyinfoUsageCounts(): Promise<Response> {
    return apiFetch('/api/keyinfo/usage-counts');
}

/**
 * Fetch all keyinfo instances from completed projects for dashboard
 * Returns: { projects: [{ projectId, projectTitle, instances: [...] }, ...] }
 */
export async function fetchAllKeyInfoInstances(): Promise<Response> {
    return apiFetch('/api/keyinfo/all-instances');
}

// ========== Workflow API (Step-based, Multi-workflow) ==========

/**
 * Fetch all workflows for a project
 * Returns: { workflows: { workflowId: ProjectWorkflowData, ... } }
 */
export async function fetchProjectWorkflows(id: string): Promise<Response> {
    return apiFetch(`/api/project/${id}/workflow`);
}

/**
 * Fetch a specific workflow by ID
 * Returns: { workflow: ProjectWorkflowData | null }
 */
export async function fetchProjectWorkflow(id: string, workflowId?: string): Promise<Response> {
    const url = workflowId
        ? `/api/project/${id}/workflow?workflow_id=${encodeURIComponent(workflowId)}`
        : `/api/project/${id}/workflow`;
    return apiFetch(url);
}

/**
 * Update a specific workflow by ID
 */
export async function updateProjectWorkflow(
    id: string,
    workflow: ProjectWorkflowData,
    workflowId?: string,
): Promise<Response> {
    return apiFetch(`/api/project/${id}/workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow, workflow_id: workflowId }),
    });
}

// ========== Keep (Archive) ==========

export async function updateProjectKept(id: string, kept: boolean): Promise<Response> {
    return apiFetch(`/api/project/${id}/keep`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kept }),
    });
}

// ========== Attributes ==========

export async function fetchAllAttributes(): Promise<Response> {
    return apiFetch('/api/attributes');
}

export async function fetchProjectAttributes(projectId: string): Promise<Response> {
    return apiFetch(`/api/project/${projectId}/attributes`);
}

// ========== Attachments API ==========

/**
 * Upload an attachment image to the separate BLOB database.
 * @param imageId - Unique ID for the image (typically the attachment ID)
 * @param projectId - The project this image belongs to
 * @param base64Data - Base64 encoded image data (with or without data URL prefix)
 */
export async function uploadAttachmentImage(
    imageId: string,
    projectId: string,
    base64Data: string,
): Promise<Response> {
    return apiFetch('/api/attachments/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            image_id: imageId,
            project_id: projectId,
            data: base64Data,
        }),
    });
}

/**
 * Get the URL for an attachment image.
 * @param imageId - The image ID to retrieve
 */
export function getAttachmentImageUrl(imageId: string): string {
    return `${BASE_URL}/api/attachments/image/${imageId}`;
}

/**
 * Delete an attachment image from the BLOB database.
 * @param imageId - The image ID to delete
 */
export async function deleteAttachmentImage(imageId: string): Promise<Response> {
    return apiFetch(`/api/attachments/image/${imageId}`, {
        method: 'DELETE',
    });
}

// ========== Activity Logs API ==========

/**
 * Fetch activity logs with optional filtering and pagination
 */
export async function fetchActivityLogs(
    limit: number = 50,
    offset: number = 0,
    actionType?: string,
): Promise<Response> {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (actionType) {
        params.set('action_type', actionType);
    }
    return apiFetch(`/api/activity-logs?${params.toString()}`);
}

// ========== Key Info API (핵심정보) ==========

/**
 * Fetch key info data for a project
 * Returns: { instances: KeyInfoInstance[] }
 */
export async function fetchProjectKeyInfo(id: string): Promise<Response> {
    return apiFetch(`/api/project/${id}/keyinfo`);
}

/**
 * Update key info data for a project
 */
export async function updateProjectKeyInfo(
    id: string,
    data: ProjectKeyInfoData,
): Promise<Response> {
    return apiFetch(`/api/project/${id}/keyinfo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data }),
    });
}

/**
 * Update key info completed status for a project
 */
export async function updateProjectKeyInfoCompleted(
    id: string,
    completed: boolean,
): Promise<Response> {
    return apiFetch(`/api/project/${id}/keyinfo/completed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed }),
    });
}
