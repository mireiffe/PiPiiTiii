import { apiFetch, BASE_URL } from "./client";

export async function fetchProjects() {
    return apiFetch("/api/projects");
}

export async function fetchProject(id: string) {
    return apiFetch(`/api/project/${id}`);
}

export async function uploadProject(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch("/api/upload", {
        method: "POST",
        body: formData,
    });
}

export async function fetchProjectStatus(id: string) {
    return apiFetch(`/api/project/${id}/status`);
}

export async function updateShapePositions(id: string, updates: any[]) {
    return apiFetch(`/api/project/${id}/update_positions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates }),
    });
}

export async function updateShapeDescription(id: string, data: { slide_index: number; shape_index: string; description: string }) {
    return apiFetch(`/api/project/${id}/update_description`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
}

export async function reparseProject(id: string) {
    return apiFetch(`/api/project/${id}/reparse_all`, {
        method: "POST",
    });
}

export async function reparseSlide(id: string, slideIndex: number) {
    return apiFetch(`/api/project/${id}/slides/${slideIndex}/reparse`, {
        method: "POST",
    });
}

export async function downloadProject(id: string) {
    const res = await apiFetch(`/api/project/${id}/download`);
    if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        // Extract filename from Content-Disposition header if possible, or default
        const contentDisposition = res.headers.get("Content-Disposition");
        let filename = "presentation.pptx";
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

export async function fetchFilters() {
    return apiFetch("/api/filters");
}

export async function fetchSettings() {
    return apiFetch("/api/settings");
}

export async function updateSettings(settings: any) {
    return apiFetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
    });
}

export async function fetchProjectSummary(id: string) {
    return apiFetch(`/api/project/${id}/summary`);
}

export async function updateProjectSummary(id: string, data: Record<string, string>) {
    return apiFetch(`/api/project/${id}/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data }),
    });
}

export async function generateSummaryStream(
    projectId: string,
    fieldId: string,
    slideIndices: number[]
): Promise<ReadableStream<Uint8Array> | null> {
    const response = await apiFetch(`/api/project/${projectId}/generate_summary/${fieldId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slide_indices: slideIndices }),
    });

    if (!response.ok) {
        throw new Error(`Failed to generate summary: ${response.statusText}`);
    }

    return response.body;
}

export async function updateProjectSummaryLLM(id: string, fieldId: string, content: string) {
    return apiFetch(`/api/project/${id}/summary_llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field_id: fieldId, content }),
    });
}

export async function fetchPromptVersion() {
    return apiFetch("/api/settings/prompt_version");
}

export async function fetchProjectsSummaryStatus() {
    return apiFetch("/api/projects/summary_status");
}

export async function batchGenerateSummary(
    projectIds: string[],
    slideIndices?: number[]
): Promise<ReadableStream<Uint8Array> | null> {
    const response = await apiFetch("/api/projects/batch_generate_summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_ids: projectIds, slide_indices: slideIndices }),
    });

    if (!response.ok) {
        throw new Error(`Failed to batch generate summary: ${response.statusText}`);
    }

    return response.body;
}

export async function updateProjectPromptVersion(id: string) {
    return apiFetch(`/api/project/${id}/update_prompt_version`, {
        method: "POST",
    });
}

// ========== Workflow API ==========

export async function validateWorkflows() {
    return apiFetch("/api/workflow/validate");
}

// ========== Workflow API (Step-based, Multi-workflow) ==========

import type { ProjectWorkflowData } from "$lib/types/workflow";

/**
 * Fetch all workflows for a project
 * Returns: { workflows: { workflowId: ProjectWorkflowData, ... } }
 */
export async function fetchProjectWorkflows(id: string) {
    return apiFetch(`/api/project/${id}/workflow`);
}

/**
 * Fetch a specific workflow by ID
 * Returns: { workflow: ProjectWorkflowData | null }
 */
export async function fetchProjectWorkflow(id: string, workflowId?: string) {
    const url = workflowId
        ? `/api/project/${id}/workflow?workflow_id=${encodeURIComponent(workflowId)}`
        : `/api/project/${id}/workflow`;
    return apiFetch(url);
}

/**
 * Update a specific workflow by ID
 */
export async function updateProjectWorkflow(id: string, workflow: ProjectWorkflowData, workflowId?: string) {
    return apiFetch(`/api/project/${id}/workflow`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow, workflow_id: workflowId }),
    });
}

// Attribute definitions (for settings page)
export interface AttributeDefinition {
    key: string;
    display_name: string;
    attr_type: {
        variant: string;
    };
}

export async function fetchAllAttributes() {
    return apiFetch("/api/attributes");
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
    base64Data: string
) {
    return apiFetch("/api/attachments/image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
export async function deleteAttachmentImage(imageId: string) {
    return apiFetch(`/api/attachments/image/${imageId}`, {
        method: "DELETE",
    });
}
