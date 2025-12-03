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
