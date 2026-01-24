<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import StepDefinitionPopup from "./StepDefinitionPopup.svelte";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        CoreStepsSettings,
        CoreStepDefinition,
    } from "$lib/types/workflow";

    export let workflowSteps: WorkflowSteps;
    export let coreStepsSettings: CoreStepsSettings;
    export let allCoreStepsAdded: boolean;
    export let addedCoreStepIds: Set<string>;
    export let getStepUsageCount: (stepId: string) => number;

    let showAddStepPopup = false;
    let showCoreStepSelector = false;
    let popupRef: HTMLDivElement | null = null;

    const dispatch = createEventDispatcher<{
        addStep: WorkflowStepRow;
        selectCoreStep: { definition: CoreStepDefinition };
        deleteStepDefinition: { stepId: string };
        createStepDefinition: { values: Record<string, string> };
        updateStepDefinition: { stepId: string; values: Record<string, string> };
    }>();

    function toggleAddStepPopup() {
        if (allCoreStepsAdded) {
            showAddStepPopup = !showAddStepPopup;
            showCoreStepSelector = false;
        }
    }

    function toggleCoreStepSelector() {
        showCoreStepSelector = !showCoreStepSelector;
        showAddStepPopup = false;
    }

    function handleAddStep(e: CustomEvent<WorkflowStepRow>) {
        dispatch("addStep", e.detail);
        showAddStepPopup = false;
    }

    function handleSelectCoreStep(def: CoreStepDefinition) {
        if (!addedCoreStepIds.has(def.id)) {
            dispatch("selectCoreStep", { definition: def });
            showCoreStepSelector = false;
        }
    }

    function handleClickOutside(event: MouseEvent) {
        const target = event.target as HTMLElement;
        if (popupRef && !popupRef.contains(target)) {
            showAddStepPopup = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="p-3 pb-0 bg-gray-50/50 border-b border-gray-100 relative">
    <div class="flex gap-2">
        <!-- Regular Step Button (disabled if core steps not complete) -->
        <button
            class="flex-1 py-2.5 border border-dashed rounded-lg transition-all flex items-center justify-center gap-1.5 group bg-white/80
            {allCoreStepsAdded
                ? 'border-gray-300 text-gray-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50'
                : 'border-gray-200 text-gray-300 cursor-not-allowed opacity-60'}"
            on:click|stopPropagation={toggleAddStepPopup}
            disabled={!allCoreStepsAdded}
            title={allCoreStepsAdded
                ? "일반 스텝 추가"
                : "먼저 모든 Core Step을 추가하세요"}
        >
            <span class="text-xs font-medium">＋ 스텝 연결</span>
        </button>

        <!-- Core Step Button (if any core steps are missing) -->
        {#if coreStepsSettings.definitions.length > 0 && !allCoreStepsAdded}
            <button
                class="flex-1 py-2.5 border border-dashed border-purple-300 rounded-lg text-purple-400 hover:border-purple-500 hover:text-purple-600 hover:bg-purple-50/50 transition-all flex items-center justify-center gap-1.5 group bg-white/80"
                on:click|stopPropagation={toggleCoreStepSelector}
            >
                <span class="text-xs font-medium">＋ Core Step</span>
            </button>
        {/if}
    </div>

    {#if showAddStepPopup && allCoreStepsAdded}
        <div bind:this={popupRef}>
            <StepDefinitionPopup
                {workflowSteps}
                {getStepUsageCount}
                on:addStep={handleAddStep}
                on:deleteStepDefinition={(e) =>
                    dispatch("deleteStepDefinition", e.detail)}
                on:createStepDefinition={(e) =>
                    dispatch("createStepDefinition", e.detail)}
                on:updateStepDefinition={(e) =>
                    dispatch("updateStepDefinition", e.detail)}
                on:close={() => (showAddStepPopup = false)}
            />
        </div>
    {/if}

    <!-- Core Step Selector Popup (only shows missing ones) -->
    {#if showCoreStepSelector}
        <div
            class="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 p-2 z-50"
        >
            <div class="text-xs font-medium text-gray-500 mb-2 px-2">
                Core Step 선택
            </div>
            <div class="space-y-1 max-h-[200px] overflow-y-auto">
                {#each coreStepsSettings.definitions as csDef (csDef.id)}
                    {@const isAlreadyAdded = addedCoreStepIds.has(csDef.id)}
                    <button
                        class="w-full px-3 py-2 text-left text-sm rounded-lg transition-colors flex items-center gap-2
                        {isAlreadyAdded
                            ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                            : 'hover:bg-purple-50'}"
                        on:click={() => handleSelectCoreStep(csDef)}
                        disabled={isAlreadyAdded}
                    >
                        <span
                            class="w-5 h-5 rounded-full text-white text-xs flex items-center justify-center font-medium {isAlreadyAdded
                                ? 'bg-gray-400'
                                : 'bg-purple-600'}"
                        >
                            {isAlreadyAdded ? "✓" : "C"}
                        </span>
                        <span class="flex-1 truncate">{csDef.name}</span>
                        {#if isAlreadyAdded}
                            <span class="text-xs text-gray-400">추가됨</span>
                        {:else}
                            <span class="text-xs text-gray-400"
                                >{csDef.presets.length}개 필드</span
                            >
                        {/if}
                    </button>
                {/each}
            </div>
            <div class="border-t border-gray-100 mt-2 pt-2">
                <a
                    href="/settings#section-workflows"
                    class="block px-3 py-1.5 text-xs text-purple-600 hover:bg-purple-50 rounded-lg"
                >
                    설정에서 워크플로우 Core Step 관리
                </a>
            </div>
        </div>
    {/if}
</div>
