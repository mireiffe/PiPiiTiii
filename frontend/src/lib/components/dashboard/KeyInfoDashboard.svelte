<script lang="ts">
    import { onMount } from 'svelte';
    import KeyInfoDetailModal from './KeyInfoDetailModal.svelte';
    import ActivityLogPanel from './ActivityLogPanel.svelte';
    import { fetchAllKeyInfoInstances, fetchSettings } from '$lib/api/project';
    import type {
        KeyInfoSettings,
        KeyInfoCategoryDefinition,
        KeyInfoItemDefinition,
        KeyInfoInstance,
        KeyInfoCaptureValue,
    } from '$lib/types/keyInfo';

    // Props
    type ModalTitleConfigItem = string | { key: string; prefix?: string; suffix?: string };
    export let modalTitleConfig: ModalTitleConfigItem[] = ["title"];
    export let projects: Array<{ id: string; name?: string; title?: string }> = [];

    // Top-level tab: 'dashboard' | 'logs'
    let activeTab: 'dashboard' | 'logs' = 'dashboard';

    // Dashboard data structure
    interface ProjectAttributes {
        [key: string]: string | number | boolean | null | undefined;
    }

    interface DashboardItem {
        item: KeyInfoItemDefinition;
        usageCount: number;
        instances: Array<{
            projectId: string;
            projectTitle: string;
            projectAttributes?: ProjectAttributes;
            textValue?: string;
            captureValues?: KeyInfoCaptureValue[];
            imageIds?: string[];
            imageCaptions?: Record<string, string>;
            captureValue?: KeyInfoCaptureValue;
            imageId?: string;
            imageCaption?: string;
        }>;
    }

    interface DashboardCategory {
        category: KeyInfoCategoryDefinition;
        totalUsage: number;
        items: DashboardItem[];
    }

    // State
    let loading = true;
    let error: string | null = null;
    let keyInfoSettings: KeyInfoSettings = { categories: [] };
    let dashboardData: DashboardCategory[] = [];
    let totalCompletedProjects = 0;
    let totalUsageCount = 0;

    // UI State
    let selectedCategoryId: string | null = null;
    let modalOpen = false;
    let selectedItem: DashboardItem | null = null;

    // Category colors
    const categoryColors = [
        '#3B82F6', // blue
        '#10B981', // green
        '#F59E0B', // amber
        '#EF4444', // red
        '#8B5CF6', // purple
        '#EC4899', // pink
        '#06B6D4', // cyan
        '#84CC16', // lime
    ];

    function getCategoryColor(index: number): string {
        return categoryColors[index % categoryColors.length];
    }

    async function loadDashboardData() {
        loading = true;
        error = null;

        try {
            // Load settings and all instances in parallel
            const [settingsRes, instancesRes] = await Promise.all([
                fetchSettings(),
                fetchAllKeyInfoInstances(),
            ]);

            if (!settingsRes.ok) {
                throw new Error('설정을 불러오는데 실패했습니다');
            }
            if (!instancesRes.ok) {
                throw new Error('데이터를 불러오는데 실패했습니다');
            }

            const settingsData = await settingsRes.json();
            const instancesData = await instancesRes.json();

            keyInfoSettings = settingsData.key_info_settings || { categories: [] };
            const projects = instancesData.projects || [];

            // Track unique projects
            const projectIds = new Set<string>();
            projects.forEach((p: { projectId: string }) => projectIds.add(p.projectId));
            totalCompletedProjects = projectIds.size;

            // Build dashboard data
            const categoryMap = new Map<string, DashboardCategory>();

            // Initialize categories
            keyInfoSettings.categories.forEach(category => {
                categoryMap.set(category.id, {
                    category,
                    totalUsage: 0,
                    items: category.items.map(item => ({
                        item,
                        usageCount: 0,
                        instances: [],
                    })),
                });
            });

            // Process all instances
            let totalCount = 0;
            for (const project of projects) {
                const { projectId, projectTitle, instances, ...projectAttributes } = project as {
                    projectId: string;
                    projectTitle: string;
                    instances: KeyInfoInstance[];
                    [key: string]: unknown;
                };

                // Track which items this project uses (to count unique projects per item)
                const usedItems = new Set<string>();

                for (const instance of instances) {
                    const catData = categoryMap.get(instance.categoryId);
                    if (!catData) continue;

                    const itemData = catData.items.find(i => i.item.id === instance.itemId);
                    if (!itemData) continue;

                    const itemKey = `${instance.categoryId}_${instance.itemId}`;
                    if (!usedItems.has(itemKey)) {
                        usedItems.add(itemKey);
                        itemData.usageCount++;
                        catData.totalUsage++;
                        totalCount++;
                    }

                    // Add instance data with all project attributes
                    itemData.instances.push({
                        projectId,
                        projectTitle,
                        projectAttributes: projectAttributes as ProjectAttributes,
                        textValue: instance.textValue,
                        captureValues: instance.captureValues,
                        imageIds: instance.imageIds,
                        imageCaptions: instance.imageCaptions,
                        captureValue: instance.captureValue,
                        imageId: instance.imageId,
                        imageCaption: instance.imageCaption,
                    });
                }
            }

            totalUsageCount = totalCount;

            // Sort items by usage count (descending)
            categoryMap.forEach(catData => {
                catData.items.sort((a, b) => b.usageCount - a.usageCount);
            });

            // Convert map to sorted array
            dashboardData = Array.from(categoryMap.values())
                .sort((a, b) => a.category.order - b.category.order);

            // Select first category by default
            if (dashboardData.length > 0 && !selectedCategoryId) {
                selectedCategoryId = dashboardData[0].category.id;
            }

        } catch (e) {
            console.error('Failed to load dashboard data:', e);
            error = e instanceof Error ? e.message : '데이터 로드 실패';
        } finally {
            loading = false;
        }
    }

    function openDetailModal(item: DashboardItem) {
        selectedItem = item;
        modalOpen = true;
    }

    function closeDetailModal() {
        modalOpen = false;
        selectedItem = null;
    }

    $: selectedCategory = dashboardData.find(d => d.category.id === selectedCategoryId);

    onMount(() => {
        loadDashboardData();
    });
</script>

<div class="h-full flex flex-col bg-gray-50 overflow-hidden">
    <!-- Top-level Tabs -->
    <div class="bg-white border-b border-gray-200 px-6 pt-3 shrink-0 flex items-center gap-1">
        <button
            class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
                {activeTab === 'dashboard'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
            on:click={() => activeTab = 'dashboard'}
        >
            <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Dashboard
            </span>
        </button>
        <button
            class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
                {activeTab === 'logs'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
            on:click={() => activeTab = 'logs'}
        >
            <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                활동 로그
            </span>
        </button>
    </div>

    {#if activeTab === 'logs'}
        <ActivityLogPanel {projects} />
    {:else if loading}
        <div class="flex-1 flex items-center justify-center">
            <div class="flex flex-col items-center gap-3">
                <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
                <span class="text-sm text-gray-500">대시보드 로딩 중...</span>
            </div>
        </div>
    {:else if error}
        <div class="flex-1 flex items-center justify-center">
            <div class="text-center">
                <div class="text-red-500 mb-2">{error}</div>
                <button
                    class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    on:click={loadDashboardData}
                >
                    다시 시도
                </button>
            </div>
        </div>
    {:else if dashboardData.length === 0}
        <div class="flex-1 flex flex-col items-center justify-center text-gray-400 p-8">
            <svg class="w-16 h-16 mb-4 opacity-20" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <p class="text-lg font-medium mb-2">KeyInfo 설정이 없습니다</p>
            <p class="text-sm text-gray-400">설정에서 카테고리와 항목을 추가해주세요</p>
        </div>
    {:else}
        <!-- Header -->
        <div class="bg-white border-b border-gray-200 px-6 py-3 shadow-sm">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-blue-100 rounded-lg">
                        <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                    </div>
                    <h1 class="text-xl font-bold text-gray-900">KeyInfo Dashboard</h1>
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">
                        확정 PPT <span class="font-bold">{totalCompletedProjects}</span>
                    </span>
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-700">
                        카테고리 <span class="font-bold">{dashboardData.length}</span>
                    </span>
                </div>
                <button
                    class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    on:click={loadDashboardData}
                    title="새로고침"
                >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </button>
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-hidden flex flex-col p-4 gap-4">
            <!-- Category Top3 Charts (horizontal layout) -->
            <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
                <h3 class="text-sm font-semibold text-gray-700 mb-3">카테고리별 TOP 3</h3>
                <div class="grid gap-4" style="grid-template-columns: repeat({Math.min(dashboardData.length, 4)}, 1fr);">
                    {#each dashboardData as catData, catIndex}
                        {@const top3Items = catData.items.slice(0, 3)}
                        {@const maxCount = Math.max(...top3Items.map(i => i.usageCount), 1)}
                        <div class="min-w-0">
                            <div class="flex items-center gap-2 mb-2">
                                <div class="w-2 h-2 rounded-full" style="background-color: {getCategoryColor(catIndex)};"></div>
                                <span class="text-xs font-semibold text-gray-700 truncate">{catData.category.name}</span>
                            </div>
                            <div class="space-y-1.5">
                                {#each top3Items as itemData, itemIndex}
                                    <button
                                        class="w-full text-left group"
                                        on:click={() => openDetailModal(itemData)}
                                    >
                                        <div class="flex items-center gap-2">
                                            <span class="text-[10px] font-bold text-gray-400 w-3">{itemIndex + 1}</span>
                                            <div class="flex-1 min-w-0">
                                                <div class="flex items-center gap-1.5">
                                                    <span class="text-xs text-gray-700 truncate group-hover:text-blue-600 transition-colors">
                                                        {itemData.item.title}
                                                    </span>
                                                    <span class="text-[10px] text-gray-400 flex-shrink-0">
                                                        {itemData.usageCount}
                                                    </span>
                                                </div>
                                                <div class="h-1.5 bg-gray-100 rounded-full mt-0.5 overflow-hidden">
                                                    <div
                                                        class="h-full rounded-full transition-all group-hover:opacity-80"
                                                        style="width: {(itemData.usageCount / maxCount) * 100}%; background-color: {getCategoryColor(catIndex)};"
                                                    ></div>
                                                </div>
                                            </div>
                                        </div>
                                    </button>
                                {:else}
                                    <div class="text-[10px] text-gray-400 italic pl-5">항목 없음</div>
                                {/each}
                            </div>
                        </div>
                    {/each}
                </div>
            </div>

            <!-- Category Tabs + Items -->
            <div class="flex-1 bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden flex flex-col">
                <!-- Category Tabs -->
                <div class="border-b border-gray-200 px-4 pt-3 overflow-x-auto">
                    <div class="flex gap-1">
                        {#each dashboardData as catData, i}
                            <button
                                class="px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors whitespace-nowrap
                                    {selectedCategoryId === catData.category.id
                                        ? 'border-blue-600 text-blue-600 bg-blue-50'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
                                on:click={() => selectedCategoryId = catData.category.id}
                            >
                                {catData.category.name}
                                <span class="ml-1.5 px-1.5 py-0.5 text-xs rounded-full
                                    {selectedCategoryId === catData.category.id
                                        ? 'bg-blue-100 text-blue-700'
                                        : 'bg-gray-100 text-gray-500'}">
                                    {catData.items.length}
                                </span>
                            </button>
                        {/each}
                    </div>
                </div>

                <!-- Items List -->
                <div class="flex-1 overflow-y-auto p-4">
                    {#if selectedCategory}
                        {#if selectedCategory.items.length === 0}
                            <div class="text-center text-gray-400 py-8">
                                이 카테고리에 정의된 항목이 없습니다
                            </div>
                        {:else}
                            <div class="space-y-2">
                                {#each selectedCategory.items as itemData}
                                    <button
                                        class="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 transition-colors group"
                                        on:click={() => openDetailModal(itemData)}
                                    >
                                        <div class="flex items-center justify-between">
                                            <div class="flex-1 min-w-0">
                                                <div class="flex items-center gap-2">
                                                    <span class="font-medium text-gray-900">{itemData.item.title}</span>
                                                    {#if itemData.usageCount > 0}
                                                        <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">
                                                            {itemData.usageCount}회 사용
                                                        </span>
                                                    {:else}
                                                        <span class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-400">
                                                            미사용
                                                        </span>
                                                    {/if}
                                                </div>
                                                {#if itemData.item.description}
                                                    <p class="text-sm text-gray-500 mt-0.5 truncate">
                                                        {itemData.item.description}
                                                    </p>
                                                {/if}
                                            </div>
                                            <svg
                                                class="w-5 h-5 text-gray-300 group-hover:text-blue-500 transition-colors flex-shrink-0 ml-2"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                            </svg>
                                        </div>
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>

<!-- Detail Modal -->
<KeyInfoDetailModal
    isOpen={modalOpen}
    itemTitle={selectedItem?.item.title ?? ''}
    itemDescription={selectedItem?.item.description ?? ''}
    usageCount={selectedItem?.usageCount ?? 0}
    instances={selectedItem?.instances ?? []}
    {modalTitleConfig}
    on:close={closeDetailModal}
/>
