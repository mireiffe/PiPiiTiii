<script lang="ts">
    import { onMount } from 'svelte';
    import CategoryBarChart from './CategoryBarChart.svelte';
    import { fetchSettings, fetchAllAttributes } from '$lib/api/project';

    interface AttributeDefinition {
        key: string;
        display_name: string;
        attr_type: { variant: string };
    }

    interface AttributeStats {
        key: string;
        displayName: string;
        variant: string;
        data: { name: string; count: number; color?: string }[];
        totalProjects: number;
        emptyCount: number;
    }

    // Props
    export let projects: Array<Record<string, any>> = [];

    // State
    let loading = true;
    let error: string | null = null;
    let dashboardAttributes: string[] = [];
    let attributeDefinitions: AttributeDefinition[] = [];
    let selectedAttrKey: string | null = null;

    const categoryColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
        '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16',
    ];

    async function loadData() {
        loading = true;
        error = null;
        try {
            const [settingsRes, attrsRes] = await Promise.all([
                fetchSettings(),
                fetchAllAttributes(),
            ]);

            if (!settingsRes.ok) throw new Error('설정을 불러오는데 실패했습니다');
            if (!attrsRes.ok) throw new Error('속성 정보를 불러오는데 실패했습니다');

            const settingsData = await settingsRes.json();
            dashboardAttributes = settingsData.dashboard_attributes || [];
            attributeDefinitions = await attrsRes.json();

            // Select first attribute by default
            if (dashboardAttributes.length > 0 && !selectedAttrKey) {
                selectedAttrKey = dashboardAttributes[0];
            }
        } catch (e) {
            console.error('Failed to load attribute dashboard data:', e);
            error = e instanceof Error ? e.message : '데이터 로드 실패';
        } finally {
            loading = false;
        }
    }

    function computeMultiSelectStats(key: string, displayName: string): AttributeStats {
        const counts = new Map<string, number>();
        let emptyCount = 0;
        for (const p of projects) {
            const val = p[key];
            if (val == null || val === '') {
                emptyCount++;
                continue;
            }
            const strVal = String(val);
            counts.set(strVal, (counts.get(strVal) || 0) + 1);
        }
        const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
        return {
            key, displayName, variant: 'multi_select',
            data: sorted.map(([name, count], i) => ({
                name, count, color: categoryColors[i % categoryColors.length],
            })),
            totalProjects: projects.length,
            emptyCount,
        };
    }

    function computeRangeStats(key: string, displayName: string): AttributeStats {
        const counts = new Map<string, number>();
        let emptyCount = 0;
        for (const p of projects) {
            const val = p[key];
            if (val == null || val === '') {
                emptyCount++;
                continue;
            }
            const strVal = String(val);
            counts.set(strVal, (counts.get(strVal) || 0) + 1);
        }
        // Sort numerically if possible
        const sorted = [...counts.entries()].sort((a, b) => {
            const numA = Number(a[0]);
            const numB = Number(b[0]);
            if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
            return a[0].localeCompare(b[0]);
        });
        return {
            key, displayName, variant: 'range',
            data: sorted.map(([name, count], i) => ({
                name, count, color: categoryColors[i % categoryColors.length],
            })),
            totalProjects: projects.length,
            emptyCount,
        };
    }

    function computeToggleStats(key: string, displayName: string): AttributeStats {
        let trueCount = 0;
        let falseCount = 0;
        let emptyCount = 0;
        for (const p of projects) {
            const v = p[key];
            if (v == null || v === '') {
                emptyCount++;
            } else if (v === true || v === 'true' || v === 1 || v === '1') {
                trueCount++;
            } else {
                falseCount++;
            }
        }
        return {
            key, displayName, variant: 'toggle',
            data: [
                { name: 'Yes', count: trueCount, color: '#10B981' },
                { name: 'No', count: falseCount, color: '#EF4444' },
            ],
            totalProjects: projects.length,
            emptyCount,
        };
    }

    function computeStatsForKey(key: string): AttributeStats | null {
        const attrDef = attributeDefinitions.find(a => a.key === key);
        if (!attrDef) return null;

        const variant = attrDef.attr_type?.variant || 'multi_select';
        const displayName = attrDef.display_name;

        if (variant === 'toggle') {
            return computeToggleStats(key, displayName);
        } else if (variant === 'range') {
            return computeRangeStats(key, displayName);
        } else {
            return computeMultiSelectStats(key, displayName);
        }
    }

    // Attribute definitions filtered to dashboard-selected ones (for tab display)
    $: dashboardAttrDefs = dashboardAttributes
        .map(key => attributeDefinitions.find(a => a.key === key))
        .filter((a): a is AttributeDefinition => a != null);

    $: selectedStats = (!loading && selectedAttrKey) ? computeStatsForKey(selectedAttrKey) : null;

    onMount(() => {
        loadData();
    });
</script>

<div class="h-full flex flex-col bg-gray-50 overflow-hidden">
    {#if loading}
        <div class="flex-1 flex items-center justify-center">
            <div class="flex flex-col items-center gap-3">
                <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-green-600"></div>
                <span class="text-sm text-gray-500">대시보드 로딩 중...</span>
            </div>
        </div>
    {:else if error}
        <div class="flex-1 flex items-center justify-center">
            <div class="text-center">
                <div class="text-red-500 mb-2">{error}</div>
                <button
                    class="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
                    on:click={loadData}
                >
                    다시 시도
                </button>
            </div>
        </div>
    {:else if dashboardAttributes.length === 0}
        <div class="flex-1 flex flex-col items-center justify-center text-gray-400 p-8">
            <svg class="w-16 h-16 mb-4 opacity-20" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M17.707 9.293a1 1 0 010 1.414l-7 7a1 1 0 01-1.414 0l-7-7A.997.997 0 012 10V5a3 3 0 013-3h5c.256 0 .512.098.707.293l7 7zM5 6a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
            </svg>
            <p class="text-lg font-medium mb-2">대시보드 속성이 설정되지 않았습니다</p>
            <p class="text-sm text-gray-400">
                <a href="/settings" class="text-blue-500 hover:underline">설정</a>에서 대시보드에 표시할 속성을 선택해주세요
            </p>
        </div>
    {:else}
        <!-- Header -->
        <div class="bg-white border-b border-gray-200 px-6 py-3 shadow-sm shrink-0">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-green-100 rounded-lg">
                        <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                    </div>
                    <h1 class="text-xl font-bold text-gray-900">Attribute Dashboard</h1>
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">
                        전체 PPT <span class="font-bold">{projects.length}</span>
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

        <!-- Attribute Tabs + Content -->
        <div class="flex-1 overflow-hidden flex flex-col">
            <!-- Attribute Tabs -->
            <div class="border-b border-gray-200 bg-white px-4 pt-3 overflow-x-auto shrink-0">
                <div class="flex gap-1">
                    {#each dashboardAttrDefs as attr (attr.key)}
                        <button
                            class="px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors whitespace-nowrap
                                {selectedAttrKey === attr.key
                                    ? 'border-green-600 text-green-600 bg-green-50'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
                            on:click={() => selectedAttrKey = attr.key}
                        >
                            {attr.display_name}
                        </button>
                    {/each}
                </div>
            </div>

            <!-- Selected Attribute Stats -->
            <div class="flex-1 overflow-y-auto p-4">
                {#if selectedStats}
                    <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-base font-semibold text-gray-700">{selectedStats.displayName}</h3>
                            <div class="flex items-center gap-3 text-xs text-gray-400">
                                <span>{selectedStats.data.length}개 값</span>
                                {#if selectedStats.emptyCount > 0}
                                    <span class="text-amber-500">미입력 {selectedStats.emptyCount}</span>
                                {/if}
                            </div>
                        </div>
                        <CategoryBarChart
                            data={selectedStats.data}
                            height={Math.max(160, selectedStats.data.length * 36)}
                        />
                    </div>
                {:else}
                    <div class="text-center text-gray-400 py-8">
                        속성을 선택해주세요
                    </div>
                {/if}
            </div>
        </div>
    {/if}
</div>
