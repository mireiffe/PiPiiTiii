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
    let expandedStepIds: Set<string> = new Set(); // For step detail expansion
    let lastAvailableStepsKey = ""; // Track changes to auto-select all

    // Reset state when modal opens
    $: if (isOpen) {
        currentStepIndex = 0;
        selectedStepIds = new Set();
        showPriorityAssignment = false;
        completedLinks = [];
        expandedStepIds = new Set();
        lastAvailableStepsKey = "";
    }

    // Auto-select all steps when availableSteps changes (on modal open or step change)
    $: {
        const currentKey = `${currentStepIndex}-${availableSteps.map(s => s.id).join(",")}`;
        if (isOpen && availableSteps.length > 0 && currentKey !== lastAvailableStepsKey) {
            selectedStepIds = new Set(availableSteps.map(s => s.id));
            lastAvailableStepsKey = currentKey;
        }
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

    // Select all steps
    function selectAllSteps() {
        selectedStepIds = new Set(availableSteps.map(s => s.id));
    }

    // Deselect all steps
    function deselectAllSteps() {
        selectedStepIds = new Set();
    }

    // Toggle step expansion (for viewing details)
    function toggleStepExpansion(stepId: string) {
        if (expandedStepIds.has(stepId)) {
            expandedStepIds.delete(stepId);
        } else {
            expandedStepIds.add(stepId);
        }
        expandedStepIds = new Set(expandedStepIds);
    }

    // Get step details for display
    function getStepDetails(step: UnifiedStepItem): { category?: string; purpose?: string; details?: string } {
        if (step.type === "core") {
            const def = coreStepDefinitions.find(d => d.id === step.coreStepId);
            return {
                category: "Core Step",
                purpose: def?.name || "",
                details: def?.description || ""
            };
        } else if (workflowSteps) {
            const row = workflowSteps.rows.find(r => r.id === step.stepId);
            if (row) {
                return {
                    category: row.values["step_category"] || "",
                    purpose: row.values["purpose"] || "",
                    details: row.values["details"] || row.values["description"] || ""
                };
            }
        }
        return {};
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

            <!-- Select All / Deselect All Buttons -->
            {#if availableSteps.length > 0}
                <div class="flex gap-2 mb-3">
                    <button
                        class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors
                            {selectedStepIds.size === availableSteps.length
                                ? 'bg-gray-100 text-gray-400 cursor-default'
                                : 'bg-purple-100 text-purple-700 hover:bg-purple-200'}"
                        on:click={selectAllSteps}
                        disabled={selectedStepIds.size === availableSteps.length}
                    >
                        전체 선택
                    </button>
                    <button
                        class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors
                            {selectedStepIds.size === 0
                                ? 'bg-gray-100 text-gray-400 cursor-default'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
                        on:click={deselectAllSteps}
                        disabled={selectedStepIds.size === 0}
                    >
                        전체 해제
                    </button>
                </div>
            {/if}

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
                        {@const isExpanded = expandedStepIds.has(step.id)}
                        {@const stepIndex = getStepIndex(step)}
                        {@const stepDetails = getStepDetails(step)}
                        <div
                            class="rounded-lg border transition-all
                                {isSelected
                                ? 'border-purple-400 bg-purple-50 ring-2 ring-purple-200'
                                : 'border-gray-200 bg-white'}"
                        >
                            <div class="flex items-center gap-3 p-3">
                                <!-- Checkbox (click to toggle selection) -->
                                <button
                                    class="w-5 h-5 rounded border-2 flex items-center justify-center transition-colors flex-shrink-0
                                    {isSelected
                                        ? 'bg-purple-500 border-purple-500'
                                        : 'border-gray-300 bg-white hover:border-purple-300'}"
                                    on:click|stopPropagation={() => toggleStepSelection(step.id)}
                                    title={isSelected ? "선택 해제" : "선택"}
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
                                </button>

                                <!-- Body area (click to expand/collapse) -->
                                <button
                                    class="flex items-center gap-3 flex-1 min-w-0 text-left hover:opacity-80 transition-opacity"
                                    on:click={() => toggleStepExpansion(step.id)}
                                >
                                    <!-- Step Badge -->
                                    <div
                                        class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0
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

                                    <!-- Expand/Collapse Icon -->
                                    <svg
                                        class="w-4 h-4 text-gray-400 flex-shrink-0 transition-transform
                                            {isExpanded ? 'rotate-180' : ''}"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M19 9l-7 7-7-7"
                                        />
                                    </svg>
                                </button>
                            </div>

                            <!-- Expanded Details -->
                            {#if isExpanded}
                                <div class="px-3 pb-3 pt-0 ml-8 border-t border-gray-100 mt-1">
                                    <div class="pt-2 space-y-1.5 text-xs">
                                        {#if stepDetails.category}
                                            <div class="flex gap-2">
                                                <span class="text-gray-400 w-14 flex-shrink-0">카테고리</span>
                                                <span class="text-gray-700">{stepDetails.category}</span>
                                            </div>
                                        {/if}
                                        {#if stepDetails.purpose}
                                            <div class="flex gap-2">
                                                <span class="text-gray-400 w-14 flex-shrink-0">목적</span>
                                                <span class="text-gray-700">{stepDetails.purpose}</span>
                                            </div>
                                        {/if}
                                        {#if stepDetails.details}
                                            <div class="flex gap-2">
                                                <span class="text-gray-400 w-14 flex-shrink-0">상세</span>
                                                <span class="text-gray-600 whitespace-pre-wrap">{stepDetails.details}</span>
                                            </div>
                                        {/if}
                                        {#if !stepDetails.category && !stepDetails.purpose && !stepDetails.details}
                                            <div class="text-gray-400 italic">상세 정보가 없습니다.</div>
                                        {/if}
                                    </div>
                                </div>
                            {/if}
                        </div>
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
