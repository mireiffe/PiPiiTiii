<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        UnifiedStepItem,
        CoreStepDefinition,
        KeyStepLink,
        WorkflowStepRow,
    } from "$lib/types/workflow";

    export let selectedSteps: UnifiedStepItem[] = [];
    export let coreStepDefinitions: CoreStepDefinition[] = [];
    export let workflowSteps: { rows: WorkflowStepRow[] } | null = null;
    export let getStepDisplayName: (step: UnifiedStepItem) => string;
    export let getStepIndex: (step: UnifiedStepItem) => number;

    const dispatch = createEventDispatcher<{
        complete: { links: KeyStepLink[] };
        back: void;
    }>();

    // Tier structure
    interface Tier {
        priority: number;
        label: string;
        steps: UnifiedStepItem[];
    }

    // Initialize tiers
    let tiers: Tier[] = [
        { priority: 1, label: "가장 중요", steps: [] },
        { priority: 2, label: "중요", steps: [] },
        { priority: 3, label: "관련", steps: [] },
    ];

    // Unassigned steps
    let unassignedSteps: UnifiedStepItem[] = [...selectedSteps];

    // Drag state
    let draggedStep: UnifiedStepItem | null = null;
    let draggedFromTier: number | null = null; // null means from unassigned
    let dropTargetTier: number | null = null;

    // Check if all steps are assigned
    $: allAssigned = unassignedSteps.length === 0;
    $: hasAnyAssigned = tiers.some((t) => t.steps.length > 0);

    // Handle drag start
    function handleDragStart(step: UnifiedStepItem, fromTier: number | null) {
        draggedStep = step;
        draggedFromTier = fromTier;
    }

    // Handle drag end
    function handleDragEnd() {
        draggedStep = null;
        draggedFromTier = null;
        dropTargetTier = null;
    }

    // Handle drag over tier
    function handleDragOver(event: DragEvent, tierIndex: number) {
        event.preventDefault();
        dropTargetTier = tierIndex;
    }

    // Handle drag leave tier
    function handleDragLeave() {
        dropTargetTier = null;
    }

    // Handle drop on tier
    function handleDropOnTier(event: DragEvent, tierIndex: number) {
        event.preventDefault();

        if (!draggedStep) return;

        // Remove from source
        if (draggedFromTier === null) {
            unassignedSteps = unassignedSteps.filter(
                (s) => s.id !== draggedStep!.id,
            );
        } else {
            tiers[draggedFromTier].steps = tiers[draggedFromTier].steps.filter(
                (s) => s.id !== draggedStep!.id,
            );
        }

        // Add to target tier
        tiers[tierIndex].steps = [...tiers[tierIndex].steps, draggedStep];
        tiers = [...tiers];

        handleDragEnd();
    }

    // Handle drop back to unassigned
    function handleDropToUnassigned(event: DragEvent) {
        event.preventDefault();

        if (!draggedStep || draggedFromTier === null) return;

        // Remove from tier
        tiers[draggedFromTier].steps = tiers[draggedFromTier].steps.filter(
            (s) => s.id !== draggedStep!.id,
        );
        tiers = [...tiers];

        // Add to unassigned
        unassignedSteps = [...unassignedSteps, draggedStep];

        handleDragEnd();
    }

    // Add a new tier
    function addTier() {
        if (tiers.length >= 5) return;
        const newPriority = tiers.length + 1;
        tiers = [
            ...tiers,
            { priority: newPriority, label: `${newPriority}순위`, steps: [] },
        ];
    }

    // Remove last empty tier
    function removeLastTier() {
        if (tiers.length <= 1) return;
        const lastTier = tiers[tiers.length - 1];
        if (lastTier.steps.length === 0) {
            tiers = tiers.slice(0, -1);
        }
    }

    // Handle complete
    function handleComplete() {
        if (!allAssigned) return;

        const links: KeyStepLink[] = [];
        tiers.forEach((tier) => {
            tier.steps.forEach((step) => {
                links.push({
                    stepId: step.id,
                    priority: tier.priority,
                });
            });
        });

        dispatch("complete", { links });
    }

    // Move all unassigned to a tier
    function moveAllToTier(tierIndex: number) {
        tiers[tierIndex].steps = [
            ...tiers[tierIndex].steps,
            ...unassignedSteps,
        ];
        unassignedSteps = [];
        tiers = [...tiers];
    }
</script>

<div class="space-y-4">
    <!-- Instructions -->
    <div class="bg-amber-50 border border-amber-200 rounded-lg p-3">
        <p class="text-sm text-amber-800">
            선택한 스텝들을 중요도에 따라 그룹으로 분류해주세요.
            <br />
            <span class="text-xs text-amber-600"
                >같은 그룹 내 스텝들은 동일한 우선순위를 가집니다.</span
            >
        </p>
    </div>

    <!-- Priority Tiers -->
    <div class="space-y-2">
        {#each tiers as tier, tierIndex (tier.priority)}
            <div
                class="rounded-lg border-2 border-dashed p-3 min-h-[60px] transition-all duration-200
                    {dropTargetTier === tierIndex
                    ? 'border-purple-400 bg-purple-50'
                    : ''}
                    {tier.steps.length > 0
                    ? 'border-purple-300 bg-purple-50/50'
                    : 'border-gray-200 bg-gray-50'}"
                on:dragover={(e) => handleDragOver(e, tierIndex)}
                on:dragleave={handleDragLeave}
                on:drop={(e) => handleDropOnTier(e, tierIndex)}
                role="region"
                aria-label="{tier.label} 그룹"
            >
                <!-- Tier Header -->
                <div class="flex items-center gap-2 mb-2">
                    <span
                        class="w-6 h-6 rounded-full bg-purple-500 text-white text-xs font-bold flex items-center justify-center"
                    >
                        {tier.priority}
                    </span>
                    <span class="text-xs font-medium text-purple-700">
                        {tier.label}
                    </span>
                    {#if tier.steps.length > 0}
                        <span class="text-[10px] text-purple-400">
                            ({tier.steps.length}개)
                        </span>
                    {/if}
                </div>

                <!-- Steps in Tier -->
                <div class="flex flex-wrap gap-2">
                    {#each tier.steps as step (step.id)}
                        <div
                            class="px-3 py-1.5 bg-white rounded-lg border border-purple-200 text-sm cursor-grab
                                   hover:border-purple-400 hover:shadow-sm transition-all active:cursor-grabbing"
                            draggable="true"
                            on:dragstart={() =>
                                handleDragStart(step, tierIndex)}
                            on:dragend={handleDragEnd}
                            role="button"
                            tabindex="0"
                        >
                            <div class="flex items-center gap-2">
                                <span
                                    class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold
                                    {step.type === 'core'
                                        ? 'bg-purple-100 text-purple-700'
                                        : 'bg-blue-100 text-blue-700'}"
                                >
                                    {step.type === "core"
                                        ? "C"
                                        : getStepIndex(step)}
                                </span>
                                <span class="text-gray-700 text-xs">
                                    {getStepDisplayName(step).length > 25
                                        ? getStepDisplayName(step).slice(
                                              0,
                                              25,
                                          ) + "..."
                                        : getStepDisplayName(step)}
                                </span>
                            </div>
                        </div>
                    {/each}

                    {#if tier.steps.length === 0}
                        <span class="text-xs text-gray-400 italic py-2">
                            스텝을 여기로 드래그하세요
                        </span>
                    {/if}
                </div>
            </div>
        {/each}
    </div>

    <!-- Add/Remove Tier Buttons -->
    <div class="flex gap-2 text-xs">
        {#if tiers.length < 5}
            <button
                class="text-purple-600 hover:text-purple-700 hover:underline"
                on:click={addTier}
            >
                + 우선순위 그룹 추가
            </button>
        {/if}
        {#if tiers.length > 1 && tiers[tiers.length - 1].steps.length === 0}
            <button
                class="text-gray-500 hover:text-gray-700 hover:underline"
                on:click={removeLastTier}
            >
                - 마지막 그룹 제거
            </button>
        {/if}
    </div>

    <!-- Unassigned Steps -->
    {#if unassignedSteps.length > 0}
        <div
            class="mt-4 pt-4 border-t border-gray-200"
            on:dragover|preventDefault
            on:drop={handleDropToUnassigned}
        >
            <div class="flex items-center justify-between mb-2">
                <p class="text-xs text-gray-500">미분류 스텝:</p>
                {#if unassignedSteps.length > 1}
                    <button
                        class="text-[10px] text-purple-600 hover:text-purple-700 hover:underline"
                        on:click={() => moveAllToTier(0)}
                    >
                        모두 1순위로
                    </button>
                {/if}
            </div>
            <div class="flex flex-wrap gap-2">
                {#each unassignedSteps as step (step.id)}
                    <div
                        class="px-3 py-1.5 bg-gray-100 rounded-lg border border-gray-200 text-sm cursor-grab
                               hover:border-gray-400 transition-all active:cursor-grabbing"
                        draggable="true"
                        on:dragstart={() => handleDragStart(step, null)}
                        on:dragend={handleDragEnd}
                        role="button"
                        tabindex="0"
                    >
                        <div class="flex items-center gap-2">
                            <span
                                class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold
                                {step.type === 'core'
                                    ? 'bg-purple-100 text-purple-700'
                                    : 'bg-blue-100 text-blue-700'}"
                            >
                                {step.type === "core"
                                    ? "C"
                                    : getStepIndex(step)}
                            </span>
                            <span class="text-gray-700 text-xs">
                                {getStepDisplayName(step).length > 25
                                    ? getStepDisplayName(step).slice(0, 25) +
                                      "..."
                                    : getStepDisplayName(step)}
                            </span>
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    {/if}

    <!-- Action Buttons -->
    <div
        class="flex justify-between items-center pt-4 border-t border-gray-200"
    >
        <button
            class="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            on:click={() => dispatch("back")}
        >
            이전
        </button>

        <button
            class="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium
                   hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={!allAssigned}
            on:click={handleComplete}
        >
            {#if !allAssigned}
                모든 스텝을 배치해주세요
            {:else}
                완료
            {/if}
        </button>
    </div>
</div>
