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
