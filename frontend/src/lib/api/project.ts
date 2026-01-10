import { apiFetch } from "./client";

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

// Slide capture region for Phenomenon node
export interface SlideCapture {
    slideIndex: number;
    x: number;
    y: number;
    width: number;
    height: number;
}

// Color palette for capture regions
export const CAPTURE_COLORS = [
    { bg: 'rgba(239, 68, 68, 0.2)', border: '#ef4444', name: '빨강' },   // red
    { bg: 'rgba(59, 130, 246, 0.2)', border: '#3b82f6', name: '파랑' },  // blue
    { bg: 'rgba(34, 197, 94, 0.2)', border: '#22c55e', name: '초록' },   // green
    { bg: 'rgba(168, 85, 247, 0.2)', border: '#a855f7', name: '보라' },  // purple
    { bg: 'rgba(249, 115, 22, 0.2)', border: '#f97316', name: '주황' },  // orange
    { bg: 'rgba(236, 72, 153, 0.2)', border: '#ec4899', name: '분홍' },  // pink
    { bg: 'rgba(20, 184, 166, 0.2)', border: '#14b8a6', name: '청록' },  // teal
    { bg: 'rgba(234, 179, 8, 0.2)', border: '#eab308', name: '노랑' },   // yellow
];

export interface WorkflowNode {
    type: "Selector" | "Sequence" | "Condition" | "Action" | "Phenomenon";
    name?: string;
    children?: string[];
    actionId?: string;
    params?: Record<string, string>;
    // Phenomenon node specific fields
    captures?: SlideCapture[];
    description?: string;
}

export interface WorkflowData {
    rootId: string;
    nodes: Record<string, WorkflowNode>;
    meta?: Record<string, any>;
}

export interface WorkflowActionParam {
    id: string;
    name: string;
    required: boolean;
}

export interface WorkflowAction {
    id: string;
    name: string;
    params: WorkflowActionParam[];
}

export async function fetchProjectWorkflow(id: string) {
    return apiFetch(`/api/project/${id}/workflow`);
}

export async function updateProjectWorkflow(id: string, workflow: WorkflowData | null) {
    return apiFetch(`/api/project/${id}/workflow`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow }),
    });
}

export async function validateWorkflows() {
    return apiFetch("/api/workflow/validate");
}

export async function generateWorkflowLLM(projectId: string, query: string) {
    return apiFetch(`/api/project/${projectId}/workflow/generate_llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
    });
}
