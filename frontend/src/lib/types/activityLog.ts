/**
 * Activity Log Types
 */

export interface ActivityLog {
    id: number;
    action_type: string;
    project_id: string | null;
    summary: string;
    details: Record<string, unknown> | null;
    created_at: string;
}

export interface ActivityLogsResponse {
    logs: ActivityLog[];
    total: number;
}

/** Action type labels for display */
export const ACTION_TYPE_LABELS: Record<string, string> = {
    keyinfo_add: '핵심정보 추가',
    keyinfo_update: '핵심정보 수정',
    keyinfo_delete: '핵심정보 삭제',
    keyinfo_complete: '핵심정보 완료',
    keyinfo_uncomplete: '핵심정보 완료 해제',
    settings_update: '설정 변경',
    project_upload: '프로젝트 업로드',
    project_archive: '프로젝트 보관',
    project_unarchive: '프로젝트 보관 해제',
};

/** Action type colors for badges */
export const ACTION_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    keyinfo_add: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
    keyinfo_update: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
    keyinfo_delete: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
    keyinfo_complete: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    keyinfo_uncomplete: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
    settings_update: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
    project_upload: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
    project_archive: { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
    project_unarchive: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
};

/** Action type icon SVG paths */
export const ACTION_TYPE_ICONS: Record<string, string> = {
    keyinfo_add: 'M12 4v16m8-8H4',
    keyinfo_update: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
    keyinfo_delete: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
    keyinfo_complete: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    keyinfo_uncomplete: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
    settings_update: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
    project_upload: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12',
    project_archive: 'M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z',
    project_unarchive: 'M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z',
};

/** Filter group definitions */
export const LOG_FILTER_GROUPS = [
    {
        label: '전체',
        value: '',
    },
    {
        label: '핵심정보',
        value: 'keyinfo_add,keyinfo_update,keyinfo_delete,keyinfo_complete,keyinfo_uncomplete',
    },
    {
        label: '설정',
        value: 'settings_update',
    },
    {
        label: '프로젝트',
        value: 'project_upload,project_archive,project_unarchive',
    },
];
