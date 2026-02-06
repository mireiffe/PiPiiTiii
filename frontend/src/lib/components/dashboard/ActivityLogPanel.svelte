<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchActivityLogs } from '$lib/api/project';
    import type { ActivityLog } from '$lib/types/activityLog';
    import {
        ACTION_TYPE_LABELS,
        ACTION_TYPE_COLORS,
        ACTION_TYPE_ICONS,
        LOG_FILTER_GROUPS,
    } from '$lib/types/activityLog';

    // Props
    export let projects: Array<{ id: string; name?: string; title?: string }> = [];

    // State
    let logs: ActivityLog[] = [];
    let total = 0;
    let loading = true;
    let error: string | null = null;

    // Filter
    let activeFilter = '';

    // Pagination
    const PAGE_SIZE = 30;
    let offset = 0;
    let loadingMore = false;

    // Build a project name map for display
    $: projectNameMap = new Map(
        projects.map(p => [p.id, p.title || p.name || p.id])
    );

    function getProjectName(projectId: string | null): string {
        if (!projectId) return '';
        return projectNameMap.get(projectId) || projectId.substring(0, 8) + '...';
    }

    async function loadLogs(reset = false) {
        if (reset) {
            offset = 0;
            logs = [];
        }

        if (reset) {
            loading = true;
        } else {
            loadingMore = true;
        }
        error = null;

        try {
            const res = await fetchActivityLogs(
                PAGE_SIZE,
                offset,
                activeFilter || undefined,
            );
            if (!res.ok) throw new Error('로그를 불러오는데 실패했습니다');

            const data = await res.json();
            if (reset) {
                logs = data.logs;
            } else {
                logs = [...logs, ...data.logs];
            }
            total = data.total;
        } catch (e) {
            error = e instanceof Error ? e.message : '로그 로드 실패';
        } finally {
            loading = false;
            loadingMore = false;
        }
    }

    function loadMore() {
        offset += PAGE_SIZE;
        loadLogs(false);
    }

    function changeFilter(filterValue: string) {
        activeFilter = filterValue;
        loadLogs(true);
    }

    function formatTime(isoString: string): string {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now.getTime() - date.getTime();

        // Within 1 minute
        if (diff < 60 * 1000) return '방금 전';
        // Within 1 hour
        if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)}분 전`;
        // Within 24 hours
        if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)}시간 전`;
        // Within 7 days
        if (diff < 7 * 24 * 60 * 60 * 1000) return `${Math.floor(diff / 86400000)}일 전`;

        // Older: show date
        return date.toLocaleDateString('ko-KR', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function getActionColor(actionType: string) {
        return ACTION_TYPE_COLORS[actionType] || { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' };
    }

    function getActionLabel(actionType: string): string {
        return ACTION_TYPE_LABELS[actionType] || actionType;
    }

    function getActionIcon(actionType: string): string {
        return ACTION_TYPE_ICONS[actionType] || 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
    }

    $: hasMore = logs.length < total;

    onMount(() => {
        loadLogs(true);
    });
</script>

<div class="h-full flex flex-col overflow-hidden">
    <!-- Filter Bar -->
    <div class="px-4 py-3 border-b border-gray-200 bg-white flex items-center gap-2 shrink-0 overflow-x-auto">
        {#each LOG_FILTER_GROUPS as group}
            <button
                class="px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-150 whitespace-nowrap
                    {activeFilter === group.value
                        ? 'bg-gray-800 text-white border-gray-800 shadow-sm'
                        : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400 hover:bg-gray-50'}"
                on:click={() => changeFilter(group.value)}
            >
                {group.label}
            </button>
        {/each}
    </div>

    <!-- Logs List -->
    <div class="flex-1 overflow-y-auto">
        {#if loading}
            <div class="flex items-center justify-center py-12">
                <div class="flex flex-col items-center gap-3">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span class="text-sm text-gray-500">로그 로딩 중...</span>
                </div>
            </div>
        {:else if error}
            <div class="flex items-center justify-center py-12">
                <div class="text-center">
                    <div class="text-red-500 text-sm mb-2">{error}</div>
                    <button
                        class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                        on:click={() => loadLogs(true)}
                    >
                        다시 시도
                    </button>
                </div>
            </div>
        {:else if logs.length === 0}
            <div class="flex flex-col items-center justify-center py-16 text-gray-400">
                <svg class="w-12 h-12 mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p class="text-sm font-medium">활동 로그가 없습니다</p>
            </div>
        {:else}
            <div class="divide-y divide-gray-100">
                {#each logs as log (log.id)}
                    {@const color = getActionColor(log.action_type)}
                    <div class="px-4 py-3 hover:bg-gray-50/80 transition-colors">
                        <div class="flex items-start gap-3">
                            <!-- Icon -->
                            <div class="mt-0.5 p-1.5 rounded-lg {color.bg} shrink-0">
                                <svg class="w-3.5 h-3.5 {color.text}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getActionIcon(log.action_type)} />
                                </svg>
                            </div>

                            <!-- Content -->
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 flex-wrap">
                                    <span class="text-xs font-semibold px-1.5 py-0.5 rounded border {color.bg} {color.text} {color.border}">
                                        {getActionLabel(log.action_type)}
                                    </span>
                                    {#if log.project_id}
                                        <span class="text-xs text-gray-500 truncate max-w-[200px]" title={log.project_id}>
                                            {getProjectName(log.project_id)}
                                        </span>
                                    {/if}
                                </div>
                                <p class="text-sm text-gray-700 mt-0.5">{log.summary}</p>

                                <!-- Details -->
                                {#if log.details}
                                    {@const details = log.details}
                                    <div class="mt-1.5 text-xs text-gray-500 space-y-0.5">
                                        {#if log.action_type === 'settings_update' && details.changes}
                                            <ul class="list-none space-y-0.5">
                                                {#each details.changes as change}
                                                    <li class="flex items-start gap-1.5">
                                                        <span class="text-purple-400 mt-px shrink-0">•</span>
                                                        <span>{change}</span>
                                                    </li>
                                                {/each}
                                            </ul>
                                        {:else if log.action_type === 'keyinfo_update' && details.changedItems}
                                            <ul class="list-none space-y-0.5">
                                                {#each details.changedItems as item}
                                                    <li class="flex items-start gap-1.5">
                                                        <span class="text-indigo-400 mt-px shrink-0">•</span>
                                                        <span>
                                                            <span class="font-medium text-gray-600">[{item.categoryName}]</span>
                                                            {item.itemName}
                                                            <span class="text-gray-400">({item.changes.join(', ')})</span>
                                                        </span>
                                                    </li>
                                                {/each}
                                            </ul>
                                        {:else if log.action_type === 'keyinfo_add' && details.categoryName}
                                            <div class="flex items-center gap-1.5">
                                                <span class="text-blue-400 shrink-0">•</span>
                                                <span>
                                                    <span class="font-medium text-gray-600">[{details.categoryName}]</span>
                                                    {details.itemName}
                                                </span>
                                            </div>
                                        {:else if log.action_type === 'keyinfo_delete' && details.removedItems}
                                            <ul class="list-none space-y-0.5">
                                                {#each details.removedItems as item}
                                                    <li class="flex items-start gap-1.5">
                                                        <span class="text-red-400 mt-px shrink-0">•</span>
                                                        <span>{item}</span>
                                                    </li>
                                                {/each}
                                            </ul>
                                        {/if}
                                    </div>
                                {/if}
                            </div>

                            <!-- Time -->
                            <span class="text-[11px] text-gray-400 whitespace-nowrap shrink-0 mt-0.5" title={new Date(log.created_at).toLocaleString('ko-KR')}>
                                {formatTime(log.created_at)}
                            </span>
                        </div>
                    </div>
                {/each}
            </div>

            <!-- Load More -->
            {#if hasMore}
                <div class="px-4 py-3 text-center border-t border-gray-100">
                    <button
                        class="px-4 py-2 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors font-medium disabled:opacity-50"
                        on:click={loadMore}
                        disabled={loadingMore}
                    >
                        {#if loadingMore}
                            <span class="inline-flex items-center gap-2">
                                <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                </svg>
                                로딩 중...
                            </span>
                        {:else}
                            더 보기 ({logs.length}/{total})
                        {/if}
                    </button>
                </div>
            {/if}
        {/if}
    </div>
</div>
