<script>
    import { createEventDispatcher } from "svelte";

    /** @type {number} */
    export let selectedCount = 0;
    /** @type {boolean} */
    export let batchGenerating = false;
    /** @type {{current: number, total: number}} */
    export let batchProgress = { current: 0, total: 0 };

    const dispatch = createEventDispatcher();
</script>

<div class="sticky top-0 z-20 bg-purple-50 border-b border-purple-200 px-4 py-3 flex items-center justify-between shadow-sm">
    <div class="flex items-center gap-3">
        <span class="text-sm font-medium text-purple-700">
            {selectedCount}개 선택됨
        </span>
        <div class="flex items-center gap-1">
            <button
                class="px-3 py-1.5 text-xs font-medium rounded-md bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors"
                on:click={() => dispatch("selectAll")}
            >
                전체 선택
            </button>
            <button
                class="px-3 py-1.5 text-xs font-medium rounded-md bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors"
                on:click={() => dispatch("deselectAll")}
            >
                전체 해제
            </button>
            <button
                class="px-3 py-1.5 text-xs font-medium rounded-md bg-amber-100 text-amber-700 border border-amber-300 hover:bg-amber-200 transition-colors"
                on:click={() => dispatch("selectOutdated")}
                title="요약이 없거나 이전 버전인 프로젝트만 선택"
            >
                업데이트 필요만 선택
            </button>
        </div>
    </div>
    <button
        class="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg
               bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700
               text-white shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        on:click={() => dispatch("startBatch")}
        disabled={selectedCount === 0 || batchGenerating}
    >
        {#if batchGenerating}
            <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>생성 중... ({batchProgress.current}/{batchProgress.total})</span>
        {:else}
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>선택 항목 요약 생성</span>
        {/if}
    </button>
</div>
