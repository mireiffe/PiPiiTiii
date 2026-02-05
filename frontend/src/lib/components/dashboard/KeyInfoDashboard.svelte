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
            <div class="space-y-3">
                {#each categories as category (category.id)}
                    {@const isExpanded = expandedCategories.has(category.id)}
                    {@const totalUsage = getCategoryTotalUsage(category)}
                    {@const sortedItems = getSortedItems(category)}

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
                                <span class="font-medium text-gray-800">{category.name}</span>
                                <span class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                                    {category.items.length}개 항목
                                </span>
                            </div>
                            <span class="text-sm text-blue-600 font-medium">
                                {totalUsage}회 사용
                            </span>
                        </button>

                        <!-- Items List -->
                        {#if isExpanded}
                            <div class="border-t border-gray-100">
                                {#if sortedItems.length === 0}
                                    <div class="px-4 py-3 text-sm text-gray-400 text-center">
                                        항목이 없습니다
                                    </div>
                                {:else}
                                    {#each sortedItems as item (item.id)}
                                        {@const usageCount = getItemUsageCount(category.id, item.id)}
                                        <button
                                            class="w-full px-4 py-2.5 flex items-center justify-between hover:bg-blue-50 transition-colors border-b border-gray-50 last:border-b-0"
                                            on:click={() => openDetailModal(category, item)}
                                            disabled={usageCount === 0}
                                            class:cursor-not-allowed={usageCount === 0}
                                            class:opacity-50={usageCount === 0}
                                        >
                                            <div class="flex items-center gap-2 pl-7">
                                                <span class="text-sm text-gray-700">{item.title}</span>
                                                {#if item.description}
                                                    <span class="text-xs text-gray-400 truncate max-w-[200px]" title={item.description}>
                                                        - {item.description}
                                                    </span>
                                                {/if}
                                            </div>
                                            <div class="flex items-center gap-2">
                                                <span class="text-sm {usageCount > 0 ? 'text-blue-600 font-medium' : 'text-gray-400'}">
                                                    {usageCount}회
                                                </span>
                                                {#if usageCount > 0}
                                                    <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                                    </svg>
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
