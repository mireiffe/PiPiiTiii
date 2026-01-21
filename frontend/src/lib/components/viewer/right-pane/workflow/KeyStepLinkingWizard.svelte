<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import Modal from "$lib/components/ui/Modal.svelte";
    import PriorityTierAssignment from "./PriorityTierAssignment.svelte";
    import type {
        UnifiedStepItem,
        CoreStepDefinition,
        KeyStepLink,
        KeyStepLinkingData,
        WorkflowStepRow,
    } from "$lib/types/workflow";
    import { getAvailableStepsForLinking } from "$lib/types/workflow";

    export let isOpen: boolean = false;
    export let coreStepsToLink: UnifiedStepItem[] = []; // Core Steps that need linking
    export let allSteps: UnifiedStepItem[] = []; // All unified steps
    export let coreStepDefinitions: CoreStepDefinition[] = [];
    export let workflowSteps: { rows: WorkflowStepRow[] } | null = null;
    export let existingLinks: KeyStepLinkingData[] = [];

    const dispatch = createEventDispatcher<{
        close: void;
        complete: { links: KeyStepLinkingData[] };
        saveLinks: { coreStepInstanceId: string; linkedSteps: KeyStepLink[] };
    }>();

    // Wizard state
    let currentStepIndex = 0;
    let selectedStepIds: Set<string> = new Set();
    let showPriorityAssignment = false;
    let completedLinks: KeyStepLinkingData[] = [];

    // Reset state when modal opens
    $: if (isOpen) {
        currentStepIndex = 0;
        selectedStepIds = new Set();
        showPriorityAssignment = false;
        completedLinks = [];
    }

    // Current Core Step being processed
    $: currentCoreStep = coreStepsToLink[currentStepIndex];
    $: currentDefinition = currentCoreStep
        ? coreStepDefinitions.find((d) => d.id === currentCoreStep.coreStepId)
        : undefined;

    // Available steps for linking (steps before the current Core Step)
    $: availableSteps = currentCoreStep
        ? getAvailableStepsForLinking(allSteps, currentCoreStep.id)
        : [];

    // Check if we can proceed
    $: isLastStep = currentStepIndex === coreStepsToLink.length - 1;
    $: canProceed = selectedStepIds.size > 0;
    $: needsPriorityAssignment = selectedStepIds.size > 1;

    // Get step display name
    function getStepDisplayName(step: UnifiedStepItem): string {
        if (step.type === "core") {
            const def = coreStepDefinitions.find(
                (d) => d.id === step.coreStepId,
            );
            return def?.name || "Core Step";
        } else {
            if (workflowSteps) {
                const row = workflowSteps.rows.find(
                    (r) => r.id === step.stepId,
                );
                if (row) {
                    const category = row.values["step_category"];
                    const purpose = row.values["purpose"];
                    if (category && purpose) return `[${category}] ${purpose}`;
                    if (category) return `[${category}]`;
                    if (purpose) return purpose;
                }
            }
            return "스텝";
        }
    }

    // Get step index in the workflow
    function getStepIndex(step: UnifiedStepItem): number {
        const sortedSteps = [...allSteps].sort((a, b) => a.order - b.order);
        return sortedSteps.findIndex((s) => s.id === step.id) + 1;
    }

    // Toggle step selection
    function toggleStepSelection(stepId: string) {
        if (selectedStepIds.has(stepId)) {
            selectedStepIds.delete(stepId);
        } else {
            selectedStepIds.add(stepId);
        }
        selectedStepIds = new Set(selectedStepIds);
    }

    // Handle next button click
    function handleNext() {
        if (!canProceed) return;

        if (needsPriorityAssignment && !showPriorityAssignment) {
            // Show priority assignment screen
            showPriorityAssignment = true;
        } else {
            // If only one step selected or priority already assigned
            if (!needsPriorityAssignment) {
                // Save with default priority 1
                const links: KeyStepLink[] = Array.from(selectedStepIds).map(
                    (stepId) => ({
                        stepId,
                        priority: 1,
                    }),
                );
                saveLinkAndProceed(links);
            }
        }
    }

    // Handle priority assignment complete
    function handlePriorityComplete(
        event: CustomEvent<{ links: KeyStepLink[] }>,
    ) {
        saveLinkAndProceed(event.detail.links);
    }

    // Save current link and move to next step
    function saveLinkAndProceed(links: KeyStepLink[]) {
        const linkData: KeyStepLinkingData = {
            coreStepInstanceId: currentCoreStep.id,
            linkedSteps: links,
            confirmedAt: new Date().toISOString(),
        };

        completedLinks = [...completedLinks, linkData];

        // Emit save for immediate persistence
        dispatch("saveLinks", {
            coreStepInstanceId: currentCoreStep.id,
            linkedSteps: links,
        });

        if (isLastStep) {
            // All done, complete the wizard
            dispatch("complete", { links: completedLinks });
        } else {
            // Move to next Core Step
            currentStepIndex++;
            selectedStepIds = new Set();
            showPriorityAssignment = false;
        }
    }

    // Handle back button
    function handleBack() {
        if (showPriorityAssignment) {
            showPriorityAssignment = false;
        } else if (currentStepIndex > 0) {
            currentStepIndex--;
            selectedStepIds = new Set();
            showPriorityAssignment = false;
            // Remove the last completed link if going back
            completedLinks = completedLinks.slice(0, -1);
        } else {
            dispatch("close");
        }
    }

    // Handle close
    function handleClose() {
        dispatch("close");
    }
</script>

<Modal
    {isOpen}
    title="핵심 step 연결"
    size="lg"
    on:close={handleClose}
    closeOnBackdrop={false}
>
    {#if currentCoreStep}
        <!-- Progress Indicator -->
        <div class="mb-4">
            <div
                class="flex items-center justify-between text-xs text-gray-500 mb-2"
            >
                <span
                    >Core Step {currentStepIndex + 1} / {coreStepsToLink.length}</span
                >
                <span class="font-medium text-purple-600"
                    >{currentDefinition?.name || ""}</span
                >
            </div>
            <div class="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                    class="h-full bg-purple-500 transition-all duration-300"
                    style="width: {((currentStepIndex + 1) /
                        coreStepsToLink.length) *
                        100}%"
                ></div>
            </div>
        </div>

        {#if showPriorityAssignment}
            <!-- Priority Assignment Screen -->
            <PriorityTierAssignment
                selectedSteps={availableSteps.filter((s) =>
                    selectedStepIds.has(s.id),
                )}
                {coreStepDefinitions}
                {workflowSteps}
                {getStepDisplayName}
                {getStepIndex}
                on:complete={handlePriorityComplete}
                on:back={() => (showPriorityAssignment = false)}
            />
        {:else}
            <!-- Step Selection Screen -->
            <div
                class="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-4"
            >
                <p class="text-sm text-purple-800">
                    <strong>"{currentDefinition?.name}"</strong>를 도출하는데
                    핵심적인 역할을 한 이전 스텝들을 선택해주세요.
                </p>
            </div>

            <!-- Available Steps for Selection -->
            <div class="space-y-2 max-h-[350px] overflow-y-auto pr-1">
                {#if availableSteps.length === 0}
                    <div
                        class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg"
                    >
                        연결 가능한 이전 스텝이 없습니다.
                    </div>
                {:else}
                    {#each availableSteps as step (step.id)}
                        {@const isSelected = selectedStepIds.has(step.id)}
                        {@const stepIndex = getStepIndex(step)}
                        <button
                            class="w-full p-3 rounded-lg border text-left transition-all
                                {isSelected
                                ? 'border-purple-400 bg-purple-50 ring-2 ring-purple-200'
                                : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'}"
                            on:click={() => toggleStepSelection(step.id)}
                        >
                            <div class="flex items-center gap-3">
                                <!-- Checkbox -->
                                <div
                                    class="w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
                                    {isSelected
                                        ? 'bg-purple-500 border-purple-500'
                                        : 'border-gray-300 bg-white'}"
                                >
                                    {#if isSelected}
                                        <svg
                                            class="w-3 h-3 text-white"
                                            fill="currentColor"
                                            viewBox="0 0 20 20"
                                        >
                                            <path
                                                fill-rule="evenodd"
                                                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                                clip-rule="evenodd"
                                            />
                                        </svg>
                                    {/if}
                                </div>

                                <!-- Step Badge -->
                                <div
                                    class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
                                    {step.type === 'core'
                                        ? 'bg-purple-500 text-white'
                                        : 'bg-blue-500 text-white'}"
                                >
                                    {step.type === "core" ? "C" : stepIndex}
                                </div>

                                <!-- Step Info -->
                                <div class="flex-1 min-w-0">
                                    <div
                                        class="text-sm font-medium text-gray-800 truncate"
                                    >
                                        {getStepDisplayName(step)}
                                    </div>
                                    <div class="text-xs text-gray-400">
                                        {step.type === "core"
                                            ? "Core Step"
                                            : "일반 스텝"}
                                    </div>
                                </div>
                            </div>
                        </button>
                    {/each}
                {/if}
            </div>

            <!-- Selection Summary -->
            {#if selectedStepIds.size > 0}
                <div class="mt-3 text-xs text-purple-600">
                    {selectedStepIds.size}개 스텝 선택됨
                    {#if needsPriorityAssignment}
                        <span class="text-gray-400 ml-1"
                            >(다음 단계에서 우선순위 지정)</span
                        >
                    {/if}
                </div>
            {/if}
        {/if}
    {/if}

    <svelte:fragment slot="footer">
        <div class="flex justify-between items-center">
            <button
                class="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
                on:click={handleBack}
            >
                {showPriorityAssignment
                    ? "이전"
                    : currentStepIndex > 0
                      ? "이전"
                      : "취소"}
            </button>

            {#if !showPriorityAssignment}
                <button
                    class="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium
                           hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    disabled={!canProceed}
                    on:click={handleNext}
                >
                    {#if needsPriorityAssignment}
                        우선순위 설정
                    {:else if isLastStep}
                        완료
                    {:else}
                        다음
                    {/if}
                </button>
            {/if}
        </div>
    </svelte:fragment>
</Modal>
