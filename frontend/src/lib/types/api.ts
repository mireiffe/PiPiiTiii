/**
 * API Types
 *
 * Type definitions for API requests and responses.
 * Removes 'any' types and provides type safety for API calls.
 */

import type { WorkflowSteps, WorkflowSettings, ProjectWorkflowData, PhaseType } from './workflow';

// ========== Shape Types ==========

export interface ShapePosition {
    slide_index: number;
    shape_index: string;
    left: number;
    top: number;
}

export interface ShapeDescription {
    slide_index: number;
    shape_index: string;
    description: string;
}

export interface Shape {
    shape_index: string;
    name?: string;
    type_code?: string | number;
    left: number;
    top: number;
    width: number;
    height: number;
    parsed_left?: number;
    parsed_top?: number;
    z_order_position?: number;
    image_path?: string;
    description?: string;
    text?: string;
    fill_color?: string;
    line_color?: string;
    font_size?: number;
    font_name?: string;
    font_bold?: boolean;
    font_italic?: boolean;
    font_color?: string;
    children?: Shape[];
}

export interface Slide {
    slide_index: number;
    shapes: Shape[];
    thumbnail_path?: string;
}

// ========== Project Types ==========

export interface Project {
    id: string;
    name: string;
    file_path: string;
    created_at: string;
    updated_at?: string;
    slides: Slide[];
    slide_width: number;
    slide_height: number;
    status?: 'pending' | 'processing' | 'completed' | 'error';
}

export interface ProjectListItem {
    id: string;
    name: string;
    created_at: string;
    updated_at?: string;
    status?: string;
    slide_count?: number;
}

// ========== Settings Types ==========

export interface SummaryField {
    id: string;
    name: string;
    prompt?: string;
    order: number;
}

export interface Settings {
    summary_fields: SummaryField[];
    workflow_steps: WorkflowSteps;
    workflow_settings?: WorkflowSettings;
    use_thumbnails?: boolean;
    tutorial_project_id?: string;  // Project ID for tutorial mode
}

// ========== Summary Types ==========

export interface SummaryData {
    user: Record<string, string>;
    llm: Record<string, string>;
}

// ========== Workflow Types (API Response) ==========

export interface WorkflowsResponse {
    workflows: Record<string, ProjectWorkflowData>;
}

// ========== Attribute Types ==========

export interface AttributeDefinition {
    key: string;
    display_name: string;
    attr_type: {
        variant: string;
    };
}

// ========== API Response Types ==========

export interface ApiResponse<T> {
    ok: boolean;
    data?: T;
    error?: string;
}

// ========== Filter Types ==========

export interface FilterOption {
    value: string;
    label: string;
    count?: number;
}

export interface FilterConfig {
    id: string;
    name: string;
    type: 'toggle' | 'multiselect' | 'range' | 'sort';
    options?: FilterOption[];
    min?: number;
    max?: number;
}

// ========== Upload Types ==========

export interface UploadProgress {
    projectId: string;
    status: 'uploading' | 'processing' | 'completed' | 'error';
    progress?: number;
    message?: string;
}

// ========== Batch Generation Types ==========

export interface BatchGenerationStatus {
    projectId: string;
    fieldId: string;
    status: 'pending' | 'generating' | 'completed' | 'error';
    content?: string;
    error?: string;
}
