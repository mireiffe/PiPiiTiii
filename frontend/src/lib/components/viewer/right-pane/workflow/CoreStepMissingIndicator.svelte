<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { CoreStepDefinition } from "$lib/types/workflow";

    export let missingDefinitions: CoreStepDefinition[] = [];

    const dispatch = createEventDispatcher<{
        selectCoreStep: { definition: CoreStepDefinition };
    }>();

    function handleSelect(def: CoreStepDefinition) {
        dispatch("selectCoreStep", { definition: def });
    }
</script>

{#if missingDefinitions.length > 0}
    <div class="px-3 pt-3 pb-2 bg-amber-50/80 border-b border-amber-200">
        <div
            class="text-xs font-medium text-amber-700 mb-2 flex items-center gap-1"
        >
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
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
            </svg>
            다음 Core Step을 먼저 추가해주세요:
        </div>
        <div class="flex flex-wrap gap-2">
            {#each missingDefinitions as def (def.id)}
                <button
                    class="px-3 py-1.5 bg-white border border-amber-300 rounded-lg text-xs font-medium text-amber-700 hover:bg-amber-100 hover:border-amber-400 transition-colors flex items-center gap-1.5 shadow-sm"
                    on:click={() => handleSelect(def)}
                >
                    <span
                        class="w-4 h-4 rounded-full bg-purple-500 text-white text-[10px] flex items-center justify-center font-bold"
                        >C</span
                    >
                    {def.name}
                </button>
            {/each}
        </div>
    </div>
{/if}
