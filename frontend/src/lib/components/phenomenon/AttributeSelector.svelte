<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { slide } from "svelte/transition";

    export let phenomenonAttributes: { key: string; name: string; value: string; source?: string }[] = [];
    export let linkedEvidenceIds: string[] = [];

    const dispatch = createEventDispatcher<{
        toggleAttribute: { key: string };
    }>();

    function isAttributeLinked(attrKey: string): boolean {
        return linkedEvidenceIds.includes(`attr:${attrKey}`);
    }
</script>

<div class="border-t border-gray-200 bg-white" transition:slide>
    <div class="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
        <span class="text-xs font-bold text-gray-500 uppercase">속성 추가하기</span>
    </div>
    <div class="max-h-48 overflow-y-auto p-2 grid grid-cols-2 gap-2">
        {#each phenomenonAttributes as attr}
            {@const isLinked = isAttributeLinked(attr.key)}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
                class="px-2 py-1.5 rounded border text-xs cursor-pointer flex items-center gap-1.5 transition-colors
                       {isLinked
                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}"
                on:click={() => dispatch("toggleAttribute", { key: attr.key })}
            >
                <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                <span class="truncate" title="{attr.name}: {attr.value}">{attr.name}: {attr.value}</span>
            </div>
        {/each}
        {#if phenomenonAttributes.length === 0}
            <div class="col-span-2 text-center text-xs text-gray-400 py-2">
                사용 가능한 속성이 없습니다.
            </div>
        {/if}
    </div>
</div>
