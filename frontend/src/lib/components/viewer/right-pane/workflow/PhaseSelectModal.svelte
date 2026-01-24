<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { PhaseType } from "$lib/types/workflow";
    import { modalStore } from "$lib/stores/modal";

    export let globalPhases: PhaseType[] = [];

    const dispatch = createEventDispatcher<{
        select: { phaseId: string };
        close: void;
    }>();

    $: isOpen = $modalStore.phaseSelect.isOpen;
    $: supporterStepId = $modalStore.phaseSelect.supporterStepId;
    $: targetStepId = $modalStore.phaseSelect.targetStepId;

    function handleSelect(phaseId: string) {
        dispatch("select", { phaseId });
        modalStore.closePhaseSelectModal();
    }

    function handleClose() {
        dispatch("close");
        modalStore.closePhaseSelectModal();
    }

    function handleBackdropClick() {
        handleClose();
    }
</script>

{#if isOpen && supporterStepId && targetStepId}
    <div
        class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
        on:click={handleBackdropClick}
        on:keydown={(e) => e.key === "Escape" && handleClose()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="phase-select-title"
        tabindex="-1"
    >
        <div
            class="bg-white rounded-lg shadow-xl p-4 min-w-[200px] max-w-[300px]"
            on:click|stopPropagation
            on:keydown|stopPropagation
            role="document"
        >
            <h3 id="phase-select-title" class="text-sm font-medium text-gray-800 mb-3">
                위상 선택
            </h3>
            <div class="space-y-2">
                {#each globalPhases as phase (phase.id)}
                    <button
                        class="w-full px-3 py-2 text-left text-sm rounded-lg border border-gray-200 hover:border-purple-400 hover:bg-purple-50 transition-colors flex items-center gap-2"
                        on:click={() => handleSelect(phase.id)}
                    >
                        <span
                            class="w-3 h-3 rounded-full"
                            style="background-color: {phase.color}"
                        ></span>
                        {phase.name}
                    </button>
                {/each}
            </div>
            <button
                class="mt-3 w-full py-1.5 text-xs text-gray-500 hover:text-gray-700"
                on:click={handleClose}
            >
                취소
            </button>
        </div>
    </div>
{/if}
