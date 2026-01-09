<script>
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import SlideSelectorPanel from "./SlideSelectorPanel.svelte";
    import SummaryFieldItem from "./SummaryFieldItem.svelte";

    export let isExpanded = false;
    export let settings;
    export let summaryData;
    export let summaryDataLLM;
    export let savingSummary = false;
    export let generatingFieldIds;
    export let generatingAll = false;
    export let selectedSlideIndices = [];
    export let comparingFieldId = null;
    export let editingFieldId = null;
    export let project;

    const dispatch = createEventDispatcher();
</script>

<div
    class="border-b border-gray-200 {isExpanded
        ? 'flex-1 flex flex-col min-h-0'
        : ''}"
>
    <AccordionHeader
        icon="📄"
        title="요약 정보"
        {isExpanded}
        savingIndicator={savingSummary}
        on:click={() => dispatch("toggleExpand")}
    />

    {#if isExpanded}
        <div
            transition:slide={{ duration: 200, axis: "y" }}
            class="border-t border-gray-100 bg-gray-50/30 flex-1 flex flex-col min-h-0"
        >
            <div class="p-5 space-y-5 flex-1 h-full overflow-y-auto custom-scrollbar">
                <div class="flex items-center justify-end">
                    {#if settings.summary_fields && settings.summary_fields.length > 0}
                        <button
                            on:click={() => dispatch("generateAllSummaries")}
                            disabled={generatingFieldIds.size > 0 || generatingAll}
                            title="모든 요약 필드를 LLM으로 자동 생성"
                            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg
                                bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700
                                text-white shadow-sm hover:shadow-md transition-all duration-200
                                disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
                        >
                            {#if generatingAll}
                                <svg class="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24">
                                    <circle
                                        class="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        stroke-width="4"
                                        fill="none"
                                    ></circle>
                                    <path
                                        class="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                    ></path>
                                </svg>
                            {:else}
                                <svg
                                    class="w-3.5 h-3.5"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M13 10V3L4 14h7v7l9-11h-7z"
                                    />
                                </svg>
                            {/if}
                            <span>전체 자동 생성</span>
                        </button>
                    {/if}
                </div>

                <!-- Slide Selection for Summary -->
                {#if settings.summary_fields && settings.summary_fields.length > 0}
                    <SlideSelectorPanel
                        {selectedSlideIndices}
                        {project}
                        on:toggleSlideSelection
                    />
                {/if}

                <!-- Summary Fields -->
                {#if settings.summary_fields && settings.summary_fields.length > 0}
                    <div class="space-y-6">
                        {#each settings.summary_fields.sort((a, b) => a.order - b.order) as field}
                            <SummaryFieldItem
                                {field}
                                {summaryData}
                                {summaryDataLLM}
                                {generatingFieldIds}
                                {generatingAll}
                                {comparingFieldId}
                                {editingFieldId}
                                on:toggleCompare
                                on:restoreLLMVersion
                                on:generateSummaryForField
                                on:setEditing={(e) => (editingFieldId = e.detail.fieldId)}
                                on:clearEditing={() => (editingFieldId = null)}
                                on:saveSummary
                            />
                        {/each}
                    </div>
                {:else}
                    <div
                        class="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-200 flex flex-col items-center gap-3"
                    >
                        <div class="bg-gray-100 p-3 rounded-full">
                            <svg
                                class="w-6 h-6 text-gray-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                                />
                            </svg>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-600 mb-1">
                                요약 필드가 없습니다
                            </p>
                            <p class="text-xs text-gray-400">
                                설정에서 요약 필드를 추가해주세요.
                            </p>
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    {/if}
</div>
