<script lang="ts">
    import { onMount } from 'svelte';
    import CategoryBarChart from './CategoryBarChart.svelte';
    import { fetchSettings, fetchAllAttributes, fetchAllKeyInfoInstances } from '$lib/api/project';
    import type {
        KeyInfoSettings,
        KeyInfoCategoryDefinition,
        KeyInfoInstance,
    } from '$lib/types/keyInfo';

    interface AttributeDefinition {
        key: string;
        display_name: string;
        attr_type: { variant: string };
    }

    // Props
    export let projects: Array<Record<string, any>> = [];

    // State
    let loading = true;
    let error: string | null = null;
    let dashboardAttributes: string[] = [];
    let attributeDefinitions: AttributeDefinition[] = [];
    let keyInfoSettings: KeyInfoSettings = { categories: [] };
    let keyInfoProjects: Array<{
        projectId: string;
        projectTitle: string;
        instances: KeyInfoInstance[];
    }> = [];
    let totalCompletedProjects = 0;

    // Filter state: Record<attrKey, selectedValues[]>
    let selectedFilters: Record<string, string[]> = {};

    // Category colors (same as KeyInfoDashboard)
    const categoryColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
        '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16',
    ];

    function getCategoryColor(index: number): string {
        return categoryColors[index % categoryColors.length];
    }

    // Attr colors (same as AttributeDashboard)
    const attrColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6',
        '#06B6D4', '#EC4899', '#EF4444', '#84CC16',
    ];

    function getAttrColor(key: string): string {
        const idx = dashboardAttributes.indexOf(key);
        return attrColors[Math.max(0, idx) % attrColors.length];
    }

    async function loadData() {
        loading = true;
        error = null;
        try {
            const [settingsRes, attrsRes, instancesRes] = await Promise.all([
                fetchSettings(),
                fetchAllAttributes(),
                fetchAllKeyInfoInstances(),
            ]);

            if (!settingsRes.ok) throw new Error('설정을 불러오는데 실패했습니다');
            if (!attrsRes.ok) throw new Error('속성 정보를 불러오는데 실패했습니다');
            if (!instancesRes.ok) throw new Error('KeyInfo 데이터를 불러오는데 실패했습니다');

            const settingsData = await settingsRes.json();
            dashboardAttributes = settingsData.dashboard_attributes || [];
            keyInfoSettings = settingsData.key_info_settings || { categories: [] };
            attributeDefinitions = await attrsRes.json();

            const instancesData = await instancesRes.json();
            keyInfoProjects = instancesData.projects || [];
            totalCompletedProjects = keyInfoProjects.length;

            // Reset filters
            selectedFilters = {};
        } catch (e) {
            console.error('Failed to load exploration data:', e);
            error = e instanceof Error ? e.message : '데이터 로드 실패';
        } finally {
            loading = false;
        }
    }

    // Helpers for value normalization
    function getProjectAttrValue(project: Record<string, any>, key: string): string {
        const val = project[key];
        if (val == null || val === '') return '(미입력)';
        const attrDef = attributeDefinitions.find(a => a.key === key);
        if (attrDef?.attr_type?.variant === 'toggle') {
            return (val === true || val === 'true' || val === 1 || val === '1') ? 'Yes' : 'No';
        }
        return String(val);
    }

    // Filter: toggle a value for an attribute key
    function toggleFilter(attrKey: string, value: string) {
        const current = selectedFilters[attrKey] || [];
        const idx = current.indexOf(value);
        if (idx >= 0) {
            const next = current.filter((_, i) => i !== idx);
            if (next.length === 0) {
                const { [attrKey]: _, ...rest } = selectedFilters;
                selectedFilters = rest;
            } else {
                selectedFilters = { ...selectedFilters, [attrKey]: next };
            }
        } else {
            selectedFilters = { ...selectedFilters, [attrKey]: [...current, value] };
        }
    }

    function removeFilter(attrKey: string) {
        const { [attrKey]: _, ...rest } = selectedFilters;
        selectedFilters = rest;
    }

    function clearAllFilters() {
        selectedFilters = {};
    }

    // Reactive: active filter entries
    $: activeFilterEntries = Object.entries(selectedFilters).filter(([, vals]) => vals.length > 0);
    $: hasActiveFilters = activeFilterEntries.length > 0;

    // Reactive: filtered projects (AND logic)
    $: filteredProjects = projects.filter(project => {
        for (const [attrKey, values] of activeFilterEntries) {
            const val = getProjectAttrValue(project, attrKey);
            if (!values.includes(val)) return false;
        }
        return true;
    });

    // Reactive: filtered KeyInfo projects
    $: filteredKeyInfoProjects = keyInfoProjects.filter(kp =>
        filteredProjects.some(fp => fp.id === kp.projectId)
    );

    // Attr definitions filtered to dashboard attributes
    $: dashboardAttrDefs = dashboardAttributes
        .map(key => attributeDefinitions.find(a => a.key === key))
        .filter((a): a is AttributeDefinition => a != null);

    // Compute attribute distribution for a given key over a given project set
    function computeAttrDistribution(
        key: string,
        projectSet: Array<Record<string, any>>,
    ): { name: string; count: number; color?: string }[] {
        const attrDef = attributeDefinitions.find(a => a.key === key);
        if (!attrDef) return [];

        const variant = attrDef.attr_type?.variant || 'multi_select';
        const color = getAttrColor(key);
        const counts = new Map<string, number>();

        for (const p of projectSet) {
            const val = getProjectAttrValue(p, key);
            counts.set(val, (counts.get(val) || 0) + 1);
        }

        let entries = [...counts.entries()];

        if (variant === 'range') {
            entries.sort((a, b) => {
                const numA = Number(a[0]);
                const numB = Number(b[0]);
                if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
                return a[0].localeCompare(b[0]);
            });
        } else if (variant === 'toggle') {
            // Yes first, No second
            entries.sort((a, b) => {
                if (a[0] === 'Yes') return -1;
                if (b[0] === 'Yes') return 1;
                return 0;
            });
        } else {
            entries.sort((a, b) => b[1] - a[1]);
        }

        return entries.map(([name, count]) => ({
            name,
            count,
            color: variant === 'toggle'
                ? (name === 'Yes' ? '#10B981' : '#EF4444')
                : color,
        }));
    }

    // Reactive: attribute distributions
    $: attrDistributions = dashboardAttrDefs.map(attrDef => ({
        key: attrDef.key,
        displayName: attrDef.display_name,
        variant: attrDef.attr_type?.variant || 'multi_select',
        data: computeAttrDistribution(attrDef.key, filteredProjects),
        isSelected: (selectedFilters[attrDef.key]?.length ?? 0) > 0,
        selectedValues: selectedFilters[attrDef.key] || [],
    }));

    // Reactive: KeyInfo distributions per category
    $: keyInfoDistributions = keyInfoSettings.categories
        .slice()
        .sort((a, b) => a.order - b.order)
        .map(category => {
            // Count unique projects per item
            const itemCounts = new Map<string, number>();
            for (const item of category.items) {
                itemCounts.set(item.id, 0);
            }

            for (const kp of filteredKeyInfoProjects) {
                const usedItems = new Set<string>();
                for (const inst of kp.instances) {
                    if (inst.categoryId === category.id && !usedItems.has(inst.itemId)) {
                        usedItems.add(inst.itemId);
                        itemCounts.set(inst.itemId, (itemCounts.get(inst.itemId) || 0) + 1);
                    }
                }
            }

            const data = category.items
                .map(item => ({
                    name: item.title,
                    count: itemCounts.get(item.id) || 0,
                }))
                .sort((a, b) => b.count - a.count);

            return { category, data };
        });

    // Get display name for a filter key
    function getFilterDisplayName(key: string): string {
        const attrDef = attributeDefinitions.find(a => a.key === key);
        return attrDef?.display_name || key;
    }

    onMount(() => {
        loadData();
    });
</script>

<div class="h-full flex flex-col bg-gray-50 overflow-hidden">
    {#if loading}
        <div class="flex-1 flex items-center justify-center">
            <div class="flex flex-col items-center gap-3">
                <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
                <span class="text-sm text-gray-500">탐색 데이터 로딩 중...</span>
            </div>
        </div>
    {:else if error}
        <div class="flex-1 flex items-center justify-center">
            <div class="text-center">
                <div class="text-red-500 mb-2">{error}</div>
                <button
                    class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                    on:click={loadData}
                >
                    다시 시도
                </button>
            </div>
        </div>
    {:else if projects.length === 0}
        <div class="flex-1 flex flex-col items-center justify-center text-gray-400 p-8">
            <svg class="w-16 h-16 mb-4 opacity-20" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
            </svg>
            <p class="text-lg font-medium mb-2">프로젝트가 없습니다</p>
        </div>
    {:else}
        <!-- Header -->
        <div class="bg-white border-b border-gray-200 px-6 py-3 shadow-sm shrink-0">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-indigo-100 rounded-lg">
                        <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <h1 class="text-xl font-bold text-gray-900">탐색</h1>
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-100 text-indigo-700">
                        전체 <span class="font-bold">{projects.length}</span>개
                    </span>
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-700">
                        KeyInfo 확정 <span class="font-bold">{totalCompletedProjects}</span>개
                    </span>
                </div>
                <button
                    class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    on:click={loadData}
                    title="새로고침"
                >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </button>
            </div>
        </div>

        <!-- Filter Chips -->
        {#if hasActiveFilters}
            <div class="bg-white border-b border-gray-200 px-6 py-2.5 shrink-0">
                <div class="flex items-center gap-2 flex-wrap">
                    {#each activeFilterEntries as [attrKey, values]}
                        {#each values as value}
                            <span class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
                                {getFilterDisplayName(attrKey)}: {value}
                                <button
                                    class="ml-0.5 hover:text-indigo-600 transition-colors"
                                    on:click={() => toggleFilter(attrKey, value)}
                                    title="필터 제거"
                                >
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </span>
                        {/each}
                    {/each}
                    <button
                        class="text-xs text-gray-500 hover:text-red-500 px-2 py-1 rounded hover:bg-red-50 transition-colors"
                        on:click={clearAllFilters}
                    >
                        전체 해제
                    </button>
                    <span class="text-xs text-gray-400 ml-auto">
                        필터 결과: <span class="font-semibold text-gray-600">{filteredProjects.length}</span>개 프로젝트
                    </span>
                </div>
            </div>
        {/if}

        <!-- Scrollable Content -->
        <div class="flex-1 overflow-y-auto p-4 space-y-6">
            {#if dashboardAttributes.length === 0}
                <!-- No dashboard attributes configured -->
                <div class="bg-white rounded-lg border border-gray-200 p-6 shadow-sm text-center text-gray-400">
                    <p class="text-sm">설정에서 대시보드 속성을 추가해주세요</p>
                </div>
            {:else}
                <!-- Attribute Distributions -->
                <div>
                    <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3 px-1">
                        Attribute 분포
                        {#if hasActiveFilters}
                            <span class="text-xs font-normal text-gray-400 normal-case tracking-normal ml-2">({filteredProjects.length}개 프로젝트 기준)</span>
                        {/if}
                    </h2>
                    <div class="space-y-3">
                        {#each attrDistributions as dist}
                            <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm {dist.isSelected ? 'ring-2 ring-indigo-200 border-indigo-300' : ''}">
                                <div class="flex items-center justify-between mb-2">
                                    <div class="flex items-center gap-2">
                                        <h3 class="text-sm font-semibold text-gray-700">{dist.displayName}</h3>
                                        {#if dist.isSelected}
                                            <span class="text-xs px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 font-medium">
                                                선택됨
                                            </span>
                                        {/if}
                                    </div>
                                    {#if dist.isSelected}
                                        <button
                                            class="text-xs text-gray-400 hover:text-red-500 transition-colors"
                                            on:click={() => removeFilter(dist.key)}
                                        >
                                            선택 해제
                                        </button>
                                    {/if}
                                </div>
                                {#if dist.data.length === 0}
                                    <div class="text-sm text-gray-400 py-2">데이터가 없습니다</div>
                                {:else}
                                    <CategoryBarChart
                                        data={dist.data}
                                        height={Math.max(100, dist.data.length * 36)}
                                        clickable={true}
                                        highlightNames={dist.selectedValues}
                                        on:itemClick={(e) => toggleFilter(dist.key, e.detail.name)}
                                    />
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            <!-- KeyInfo Distributions -->
            <div>
                <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3 px-1">
                    KeyInfo 분포
                    <span class="text-xs font-normal text-gray-400 normal-case tracking-normal ml-2">(확정 프로젝트 기준, {filteredKeyInfoProjects.length}개)</span>
                </h2>
                {#if filteredKeyInfoProjects.length === 0}
                    <div class="bg-white rounded-lg border border-gray-200 p-6 shadow-sm text-center text-gray-400">
                        <p class="text-sm">확정된 프로젝트가 없습니다</p>
                    </div>
                {:else if keyInfoSettings.categories.length === 0}
                    <div class="bg-white rounded-lg border border-gray-200 p-6 shadow-sm text-center text-gray-400">
                        <p class="text-sm">KeyInfo 카테고리가 설정되지 않았습니다</p>
                    </div>
                {:else}
                    <div class="space-y-3">
                        {#each keyInfoDistributions as dist, catIndex}
                            {@const hasData = dist.data.some(d => d.count > 0)}
                            <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
                                <div class="flex items-center gap-2 mb-2">
                                    <div class="w-2.5 h-2.5 rounded-full" style="background-color: {getCategoryColor(catIndex)};"></div>
                                    <h3 class="text-sm font-semibold text-gray-700">{dist.category.name}</h3>
                                </div>
                                {#if !hasData}
                                    <div class="text-sm text-gray-400 py-2">데이터가 없습니다</div>
                                {:else}
                                    <CategoryBarChart
                                        data={dist.data.filter(d => d.count > 0).map((d, i) => ({ ...d, color: getCategoryColor(catIndex) }))}
                                        height={Math.max(100, dist.data.filter(d => d.count > 0).length * 36)}
                                    />
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>

            {#if filteredProjects.length === 0 && hasActiveFilters}
                <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center">
                    <p class="text-sm text-amber-700">조건에 맞는 프로젝트가 없습니다</p>
                    <button
                        class="mt-2 text-xs text-amber-600 hover:text-amber-800 underline"
                        on:click={clearAllFilters}
                    >
                        필터 전체 해제
                    </button>
                </div>
            {/if}
        </div>
    {/if}
</div>
