<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchKeyinfoUsageCounts, fetchKeyinfoUsageDetails, fetchSettings } from '$lib/api/project';
    import type {
        KeyInfoCategoryDefinition,
        KeyInfoItemDefinition,
        KeyInfoUsageDetail,
        KeyInfoSettings
    } from '$lib/types/keyInfo';
    import KeyInfoUsageDetailModal from './KeyInfoUsageDetailModal.svelte';

    // State
    let loading = true;
    let error: string | null = null;
    let categories: KeyInfoCategoryDefinition[] = [];
    let usageCounts: Record<string, number> = {};
    let usageDetails: Record<string, KeyInfoUsageDetail[]> = {};

    // UI State
    let expandedCategories: Set<string> = new Set();
    let selectedItem: { category: KeyInfoCategoryDefinition; item: KeyInfoItemDefinition } | null = null;

    // Chart colors for categories
    const CHART_COLORS = [
        { bg: 'bg-blue-500', light: 'bg-blue-100', text: 'text-blue-600' },
        { bg: 'bg-emerald-500', light: 'bg-emerald-100', text: 'text-emerald-600' },
        { bg: 'bg-amber-500', light: 'bg-amber-100', text: 'text-amber-600' },
        { bg: 'bg-purple-500', light: 'bg-purple-100', text: 'text-purple-600' },
        { bg: 'bg-rose-500', light: 'bg-rose-100', text: 'text-rose-600' },
        { bg: 'bg-cyan-500', light: 'bg-cyan-100', text: 'text-cyan-600' },
    ];

    function getCategoryColor(index: number) {
        return CHART_COLORS[index % CHART_COLORS.length];
    }

    onMount(async () => {
        await loadData();
    });

    async function loadData() {
        loading = true;
        error = null;
        try {
            // Fetch settings, counts, and details in parallel
            const [settingsRes, countsRes, detailsRes] = await Promise.all([
                fetchSettings(),
                fetchKeyinfoUsageCounts(),
                fetchKeyinfoUsageDetails(),
            ]);

            if (!settingsRes.ok) throw new Error('Failed to load settings');
            if (!countsRes.ok) throw new Error('Failed to load usage counts');
            if (!detailsRes.ok) throw new Error('Failed to load usage details');

            const settingsData = await settingsRes.json();
            const countsData = await countsRes.json();
            const detailsData = await detailsRes.json();

            categories = (settingsData.key_info_settings as KeyInfoSettings)?.categories || [];
            usageCounts = countsData.counts || {};
            usageDetails = detailsData.details || {};

            // Sort categories by order
            categories.sort((a, b) => a.order - b.order);

            // Expand first category by default if exists
            if (categories.length > 0) {
                expandedCategories.add(categories[0].id);
            }
        } catch (e) {
            error = e instanceof Error ? e.message : 'Unknown error';
        } finally {
            loading = false;
        }
    }

    function toggleCategory(categoryId: string) {
        if (expandedCategories.has(categoryId)) {
            expandedCategories.delete(categoryId);
        } else {
            expandedCategories.add(categoryId);
        }
        expandedCategories = expandedCategories; // Trigger reactivity
    }

    function getItemUsageCount(categoryId: string, itemId: string): number {
        const key = `${categoryId}_${itemId}`;
        return usageCounts[key] || 0;
    }

    function getItemUsageDetails(categoryId: string, itemId: string): KeyInfoUsageDetail[] {
        const key = `${categoryId}_${itemId}`;
        return usageDetails[key] || [];
    }

    function getCategoryTotalUsage(category: KeyInfoCategoryDefinition): number {
        return category.items.reduce((sum, item) => sum + getItemUsageCount(category.id, item.id), 0);
    }

    function getSortedItems(category: KeyInfoCategoryDefinition): KeyInfoItemDefinition[] {
        // Sort items by usage count (descending)
        return [...category.items].sort((a, b) => {
            const countA = getItemUsageCount(category.id, a.id);
            const countB = getItemUsageCount(category.id, b.id);
            return countB - countA;
        });
    }

    function openDetailModal(category: KeyInfoCategoryDefinition, item: KeyInfoItemDefinition) {
        selectedItem = { category, item };
    }

    function closeDetailModal() {
        selectedItem = null;
    }

    // Calculate max usage for chart scaling
    $: maxCategoryUsage = Math.max(...categories.map(c => getCategoryTotalUsage(c)), 1);
    $: totalUsage = categories.reduce((sum, c) => sum + getCategoryTotalUsage(c), 0);
</script>

<div class="h-full flex flex-col overflow-hidden">
    <!-- Header -->
    <div class="px-6 py-4 border-b border-gray-200 bg-white">
        <h2 class="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            KeyInfo Dashboard
        </h2>
        <p class="text-sm text-gray-500 mt-1">
            확정된 PPT의 핵심정보 현황
        </p>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-4">
        {#if loading}
            <div class="flex items-center justify-center h-32">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        {:else if error}
            <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                <p class="font-medium">Error loading data</p>
                <p class="text-sm mt-1">{error}</p>
                <button
                    class="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                    on:click={loadData}
                >
                    Retry
                </button>
            </div>
        {:else if categories.length === 0}
            <div class="flex flex-col items-center justify-center h-32 text-gray-400">
                <svg class="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p class="text-sm">KeyInfo 카테고리가 정의되지 않았습니다.</p>
                <p class="text-xs mt-1">Settings에서 카테고리를 추가해주세요.</p>
            </div>
        {:else}
            <!-- Category Overview Chart -->
            <div class="bg-white rounded-lg border border-gray-200 p-4 mb-4">
                <h3 class="text-sm font-medium text-gray-700 mb-3">카테고리별 사용 현황</h3>
                <div class="space-y-2">
                    {#each categories as category, index (category.id)}
                        {@const usage = getCategoryTotalUsage(category)}
                        {@const percentage = totalUsage > 0 ? (usage / totalUsage) * 100 : 0}
                        {@const barWidth = maxCategoryUsage > 0 ? (usage / maxCategoryUsage) * 100 : 0}
                        {@const color = getCategoryColor(index)}
                        <div class="flex items-center gap-3">
                            <span class="text-xs text-gray-600 w-16 truncate" title={category.name}>
                                {category.name}
                            </span>
                            <div class="flex-1 h-5 {color.light} rounded-full overflow-hidden">
                                <div
                                    class="h-full {color.bg} rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                                    style="width: {barWidth}%"
                                >
                                    {#if barWidth > 15}
                                        <span class="text-xs text-white font-medium">{usage}</span>
                                    {/if}
                                </div>
                            </div>
                            {#if barWidth <= 15}
                                <span class="text-xs {color.text} font-medium w-8">{usage}</span>
                            {:else}
                                <span class="text-xs text-gray-400 w-8">{percentage.toFixed(0)}%</span>
                            {/if}
                        </div>
                    {/each}
                </div>
                <div class="mt-3 pt-3 border-t border-gray-100 flex justify-between text-xs text-gray-500">
                    <span>{categories.length}개 카테고리</span>
                    <span>총 {totalUsage}회 사용</span>
                </div>
            </div>

            <!-- Categories Detail -->
            <div class="space-y-3">
                {#each categories as category, categoryIndex (category.id)}
                    {@const isExpanded = expandedCategories.has(category.id)}
                    {@const totalUsage = getCategoryTotalUsage(category)}
                    {@const sortedItems = getSortedItems(category)}
                    {@const color = getCategoryColor(categoryIndex)}
                    {@const maxItemUsage = Math.max(...sortedItems.map(item => getItemUsageCount(category.id, item.id)), 1)}

                    <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
                        <!-- Category Header -->
                        <button
                            class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                            on:click={() => toggleCategory(category.id)}
                        >
                            <div class="flex items-center gap-3">
                                <svg
                                    class="w-4 h-4 text-gray-400 transition-transform {isExpanded ? 'rotate-90' : ''}"
                                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                >
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                </svg>
                                <span class="w-2 h-2 rounded-full {color.bg}"></span>
                                <span class="font-medium text-gray-800">{category.name}</span>
                                <span class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                                    {category.items.length}개 항목
                                </span>
                            </div>
                            <span class="text-sm {color.text} font-medium">
                                {totalUsage}회 사용
                            </span>
                        </button>

                        <!-- Items List with mini charts -->
                        {#if isExpanded}
                            <div class="border-t border-gray-100">
                                {#if sortedItems.length === 0}
                                    <div class="px-4 py-3 text-sm text-gray-400 text-center">
                                        항목이 없습니다
                                    </div>
                                {:else}
                                    {#each sortedItems as item (item.id)}
                                        {@const usageCount = getItemUsageCount(category.id, item.id)}
                                        {@const itemBarWidth = maxItemUsage > 0 ? (usageCount / maxItemUsage) * 100 : 0}
                                        <button
                                            class="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-blue-50 transition-colors border-b border-gray-50 last:border-b-0"
                                            on:click={() => openDetailModal(category, item)}
                                            disabled={usageCount === 0}
                                            class:cursor-not-allowed={usageCount === 0}
                                            class:opacity-50={usageCount === 0}
                                        >
                                            <div class="flex items-center gap-2 pl-7 min-w-0 flex-1">
                                                <span class="text-sm text-gray-700 truncate">{item.title}</span>
                                            </div>
                                            <!-- Mini bar chart -->
                                            <div class="w-24 h-2 bg-gray-100 rounded-full overflow-hidden flex-shrink-0">
                                                <div
                                                    class="h-full {color.bg} rounded-full transition-all duration-300"
                                                    style="width: {itemBarWidth}%"
                                                ></div>
                                            </div>
                                            <div class="flex items-center gap-2 flex-shrink-0">
                                                <span class="text-sm w-8 text-right {usageCount > 0 ? color.text + ' font-medium' : 'text-gray-400'}">
                                                    {usageCount}
                                                </span>
                                                {#if usageCount > 0}
                                                    <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                                    </svg>
                                                {:else}
                                                    <div class="w-4"></div>
                                                {/if}
                                            </div>
                                        </button>
                                    {/each}
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>

<!-- Detail Modal -->
{#if selectedItem}
    <KeyInfoUsageDetailModal
        category={selectedItem.category}
        item={selectedItem.item}
        details={getItemUsageDetails(selectedItem.category.id, selectedItem.item.id)}
        on:close={closeDetailModal}
    />
{/if}
