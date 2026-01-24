<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { uiStore, selectedCount } from "$lib/stores/ui";

    export let allStepIds: string[] = [];

    const dispatch = createEventDispatcher<{
        selectAll: void;
        clearSelection: void;
    }>();

    $: count = $selectedCount;

    function handleSelectAll() {
        uiStore.selectAll(allStepIds);
        dispatch("selectAll");
    }

    function handleClearSelection() {
        uiStore.clearSelection();
        dispatch("clearSelection");
    }
</script>

{#if count > 0}
    <div
        class="px-3 py-2 bg-blue-50 border-b border-blue-200 flex items-center gap-2 flex-wrap"
    >
        <div class="flex items-center gap-2">
            <span class="text-xs font-medium text-blue-700">
                {count}개 선택됨
            </span>
            <button
                class="text-xs text-blue-500 hover:text-blue-700 underline"
                on:click={handleSelectAll}
            >
                전체 선택
            </button>
            <button
                class="text-xs text-gray-500 hover:text-gray-700 underline"
                on:click={handleClearSelection}
            >
                선택 해제
            </button>
        </div>
    </div>
{/if}
