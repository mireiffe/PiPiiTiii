<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import CoreStepItem from "./CoreStepItem.svelte";
    import WorkflowStepItem from "./WorkflowStepItem.svelte";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        WorkflowStepInstance,
        UnifiedStepItem,
        CoreStepInstance,
        CoreStepDefinition,
        CoreStepsSettings,
        StepAttachment,
        KeyStepLinkingData,
    } from "$lib/types/workflow";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";

    // Props
    export let sortedUnifiedSteps: UnifiedStepItem[] = [];
    export let unifiedDisplayMap: Map<string, number> = new Map();
    export let workflowSteps: WorkflowSteps;
    export let coreStepsSettings: CoreStepsSettings;
    export let projectId: string = "";
    export let slideWidth: number = 960;
    export let slideHeight: number = 540;
    export let allCoreStepsAdded: boolean = false;
    export let regularStepCount: number = 0;
    export let keyStepLinks: KeyStepLinkingData[] = [];
    export let phenomenonAttributes: string[] = [];
    export let availableAttributes: { key: string; display_name: string; attr_type: { variant: string } }[] = [];
    export let projectAttributeValues: Record<string, string> = {};
    export let selectedSlideIndices: number[] = [];

    // Step expansion state
    export let expandedStepId: string | null = null;
    export let expandedCoreStepId: string | null = null;
    export let captureTargetStepId: string | null = null;
    export let addingAttachmentToStepId: string | null = null;
    export let attachmentTextInput: string = "";

    // Selection state
    export let selectedStepIds: Set<string> = new Set();
    export let selectionModeActive: boolean = false;

    // Support drag state
    export let dragMode: "reorder" | "support" | null = null;
    export let supportGuideTargetStepId: string | null = null;

    // Component refs for Core Steps
    export let coreStepItemRefs: Record<string, any> = {};

    // Unified drag & drop state (local)
    let unifiedDraggedIdx: number | null = null;
    let unifiedDropTargetIdx: number | null = null;

    const dispatch = createEventDispatcher<{
        // Core Step events
        toggleCoreStepExpand: { instanceId: string };
        removeUnifiedStep: { stepId: string; idx: number };
        unifiedMoveUp: { idx: number };
        unifiedMoveDown: { idx: number };
        unifiedCoreStepUpdate: { event: CustomEvent; unifiedStepId: string };
        coreStepStartCapture: { instanceId: string; presetId: string };
        coreStepImagePaste: { event: CustomEvent; instanceId: string };
        coreStepImageClick: { event: CustomEvent; instanceId: string };
        // Regular Step events
        toggleStepExpand: { stepId: string };
        startCaptureForStep: { stepId: string };
        toggleAttachmentSection: { stepId: string };
        removeUnifiedCapture: { stepId: string; captureId: string };
        openUnifiedAttachmentModal: { stepId: string; attachment: StepAttachment };
        updateUnifiedAttachment: { stepId: string; attachmentId: string; data: string };
        removeAttachment: { stepId: string; attachmentId: string };
        addUnifiedTextAttachment: { stepId: string };
        handleUnifiedPaste: { event: ClipboardEvent; stepId: string };
        // Selection events
        checkboxClick: { stepId: string; event: MouseEvent };
        cardCtrlClick: { stepId: string; event: MouseEvent };
        // Drag & drop (reorder) events
        unifiedReorder: { fromIndex: number; toIndex: number };
        // Text input binding
        attachmentTextInputChange: { value: string };
    }>();

    // Helpers
    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find((r) => r.id === stepId);
    }

    function getCoreStepDefinition(
        coreStepId: string
    ): CoreStepDefinition | undefined {
        return coreStepsSettings.definitions.find((d) => d.id === coreStepId);
    }

    // Convert UnifiedStepItem to CoreStepInstance for CoreStepItem component
    function asCoreStepInstance(item: UnifiedStepItem): CoreStepInstance {
        return {
            id: item.id,
            coreStepId: item.coreStepId!,
            presetValues: item.presetValues ?? [],
            order: item.order,
            createdAt: item.createdAt,
        };
    }

    // Convert UnifiedStepItem to WorkflowStepInstance for WorkflowStepItem component
    function asWorkflowStepInstance(
        item: UnifiedStepItem
    ): WorkflowStepInstance {
        return {
            id: item.id,
            stepId: item.stepId!,
            captures: item.captures ?? [],
            attachments: item.attachments ?? [],
            order: item.order,
            createdAt: item.createdAt,
        };
    }

    // ========== Unified Drag & Drop Handlers ==========
    function handleUnifiedDragStart(e: DragEvent, idx: number) {
        unifiedDraggedIdx = idx;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", idx.toString());
        }
    }

    function handleUnifiedDragEnd() {
        unifiedDraggedIdx = null;
        unifiedDropTargetIdx = null;
    }

    function handleUnifiedDragOver(e: DragEvent, idx: number) {
        e.preventDefault();
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = "move";
        }
        unifiedDropTargetIdx = idx;
    }

    function handleUnifiedDrop(e: DragEvent) {
        e.preventDefault();
        e.stopPropagation();

        if (unifiedDraggedIdx !== null && unifiedDropTargetIdx !== null) {
            let toIndex = unifiedDropTargetIdx;
            if (unifiedDraggedIdx < toIndex) toIndex -= 1;

            if (toIndex !== unifiedDraggedIdx) {
                dispatch("unifiedReorder", {
                    fromIndex: unifiedDraggedIdx,
                    toIndex: toIndex,
                });
            }
        }

        unifiedDraggedIdx = null;
        unifiedDropTargetIdx = null;
    }

    // Attachment text input handling
    function handleAttachmentTextInputChange(e: Event) {
        const target = e.target as HTMLInputElement;
        dispatch("attachmentTextInputChange", { value: target.value });
    }
</script>

<div
    class="flex-1 overflow-y-auto p-3 space-y-2 relative flex flex-col"
>
    <div class="relative">
        <div
            class="absolute left-[18px] top-0 bottom-0 w-px bg-gray-200 z-0"
        ></div>

        {#each sortedUnifiedSteps as unifiedStep, idx (unifiedStep.id)}
            {@const isBeingDragged = unifiedDraggedIdx === idx}
            {@const showDropIndicator =
                unifiedDropTargetIdx === idx && unifiedDraggedIdx !== idx}

            <!-- Core Step Item -->
            {#if unifiedStep.type === "core"}
                {@const csDef = getCoreStepDefinition(unifiedStep.coreStepId!)}
                {#if csDef}
                    <div
                        class="relative mb-2"
                        style={isBeingDragged ? "opacity: 0.5;" : ""}
                        draggable="true"
                        on:dragstart={(e) => handleUnifiedDragStart(e, idx)}
                        on:dragend={handleUnifiedDragEnd}
                        on:dragover={(e) => handleUnifiedDragOver(e, idx)}
                        on:drop={handleUnifiedDrop}
                    >
                        {#if showDropIndicator}
                            <div
                                class="absolute top-0 left-6 right-0 h-0.5 bg-purple-500 rounded-full z-50 pointer-events-none transform -translate-y-1/2 shadow-sm"
                            ></div>
                        {/if}
                        <CoreStepItem
                            bind:this={coreStepItemRefs[unifiedStep.id]}
                            instance={asCoreStepInstance(unifiedStep)}
                            definition={csDef}
                            displayNumber={unifiedDisplayMap.get(unifiedStep.id) ?? idx + 1}
                            isExpanded={expandedCoreStepId === unifiedStep.id}
                            {projectId}
                            {slideWidth}
                            {slideHeight}
                            {keyStepLinks}
                            allSteps={sortedUnifiedSteps}
                            coreStepDefinitions={coreStepsSettings.definitions}
                            {workflowSteps}
                            {phenomenonAttributes}
                            {availableAttributes}
                            {projectAttributeValues}
                            {selectedSlideIndices}
                            on:toggleExpand={() =>
                                dispatch("toggleCoreStepExpand", {
                                    instanceId: unifiedStep.id,
                                })}
                            on:remove={() =>
                                dispatch("removeUnifiedStep", {
                                    stepId: unifiedStep.id,
                                    idx,
                                })}
                            on:moveUp={() =>
                                dispatch("unifiedMoveUp", { idx })}
                            on:moveDown={() =>
                                dispatch("unifiedMoveDown", { idx })}
                            on:update={(e) =>
                                dispatch("unifiedCoreStepUpdate", {
                                    event: e,
                                    unifiedStepId: unifiedStep.id,
                                })}
                            on:startCapture={(e) =>
                                dispatch("coreStepStartCapture", {
                                    instanceId: unifiedStep.id,
                                    presetId: e.detail.presetId,
                                })}
                            on:imagePaste={(e) =>
                                dispatch("coreStepImagePaste", {
                                    event: e,
                                    instanceId: unifiedStep.id,
                                })}
                            on:imageClick={(e) =>
                                dispatch("coreStepImageClick", {
                                    event: e,
                                    instanceId: unifiedStep.id,
                                })}
                        />
                    </div>
                {:else}
                    <!-- Orphan Core Step - definition deleted -->
                    <div
                        class="relative mb-2 pl-6"
                        style={isBeingDragged ? "opacity: 0.5;" : ""}
                    >
                        {#if showDropIndicator}
                            <div
                                class="absolute top-0 left-8 right-0 h-0.5 bg-red-500 rounded-full z-50 pointer-events-none transform -translate-y-1/2 shadow-sm"
                            ></div>
                        {/if}
                        <!-- Number Badge -->
                        <div
                            class="absolute left-0 top-2.5 w-5 h-5 rounded-full bg-red-400 flex items-center justify-center text-white text-[9px] font-bold shadow-sm z-20"
                        >
                            ?
                        </div>
                        <!-- Card -->
                        <div
                            class="bg-white rounded-lg border border-red-200 shadow-sm"
                        >
                            <div
                                class="p-3 flex items-center justify-between gap-2"
                            >
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2">
                                        <span
                                            class="text-xs font-medium text-red-600 bg-red-100 px-1.5 py-0.5 rounded"
                                        >
                                            삭제됨
                                        </span>
                                        <span
                                            class="text-sm font-medium text-gray-500 truncate"
                                        >
                                            Core Step (정의 없음)
                                        </span>
                                    </div>
                                    <p class="text-xs text-red-500 mt-1">
                                        설정에서 삭제된 Core Step입니다.
                                        삭제해주세요.
                                    </p>
                                </div>
                                <button
                                    class="px-2 py-1 text-xs text-red-600 hover:text-white bg-red-50 hover:bg-red-500 border border-red-200 hover:border-red-500 rounded transition-colors"
                                    on:click={() =>
                                        dispatch("removeUnifiedStep", {
                                            stepId: unifiedStep.id,
                                            idx,
                                        })}
                                >
                                    삭제
                                </button>
                            </div>
                        </div>
                    </div>
                {/if}

                <!-- Regular Step Item (only visible when all core steps added) -->
            {:else if unifiedStep.type === "regular"}
                {#if allCoreStepsAdded}
                    {@const stepDef = getStepDefinition(unifiedStep.stepId!)}
                    {@const color = EVIDENCE_COLORS[idx % EVIDENCE_COLORS.length]}
                    {@const showSupportGuide =
                        dragMode === "support" &&
                        supportGuideTargetStepId === unifiedStep.id}

                    <div
                        class="relative mb-2"
                        style={isBeingDragged ? "opacity: 0.5;" : ""}
                        draggable="true"
                        on:dragstart={(e) => handleUnifiedDragStart(e, idx)}
                        on:dragend={handleUnifiedDragEnd}
                        on:dragover={(e) => handleUnifiedDragOver(e, idx)}
                        on:drop={handleUnifiedDrop}
                    >
                        {#if showDropIndicator}
                            <div
                                class="absolute top-0 left-8 right-0 h-0.5 bg-blue-500 rounded-full z-50 pointer-events-none transform -translate-y-1/2 shadow-sm"
                            ></div>
                        {/if}

                        <!-- Support creation guide -->
                        {#if showSupportGuide}
                            <div
                                class="absolute -right-1 top-1/2 -translate-y-1/2 z-20 pointer-events-none"
                            >
                                <div class="support-guide-indicator">
                                    <div
                                        class="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center shadow-lg animate-bounce-right"
                                    >
                                        <svg
                                            class="w-3 h-3 text-white"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="3"
                                                d="M12 4v16m8-8H4"
                                            />
                                        </svg>
                                    </div>
                                    <span
                                        class="absolute left-full ml-1 top-1/2 -translate-y-1/2 whitespace-nowrap text-[10px] font-medium text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded shadow"
                                    >
                                        위상 지원
                                    </span>
                                </div>
                            </div>
                        {/if}

                        <WorkflowStepItem
                            step={asWorkflowStepInstance(unifiedStep)}
                            index={idx}
                            {stepDef}
                            {color}
                            {workflowSteps}
                            {projectId}
                            {slideWidth}
                            {slideHeight}
                            displayNumber={unifiedDisplayMap.get(unifiedStep.id) ?? idx + 1}
                            isExpanded={expandedStepId === unifiedStep.id}
                            isCapturing={captureTargetStepId === unifiedStep.id}
                            isAddingAttachment={addingAttachmentToStepId ===
                                unifiedStep.id}
                            {isBeingDragged}
                            showDropIndicatorTop={false}
                            showDropIndicatorBottom={false}
                            isLastStep={idx === sortedUnifiedSteps.length - 1}
                            bind:attachmentTextInput
                            isSelected={selectedStepIds.has(unifiedStep.id)}
                            showSelectionCheckbox={selectionModeActive}
                            on:toggleExpand={() =>
                                dispatch("toggleStepExpand", {
                                    stepId: unifiedStep.id,
                                })}
                            on:startCapture={() =>
                                dispatch("startCaptureForStep", {
                                    stepId: unifiedStep.id,
                                })}
                            on:toggleAttachment={() =>
                                dispatch("toggleAttachmentSection", {
                                    stepId: unifiedStep.id,
                                })}
                            on:moveUp={() =>
                                dispatch("unifiedMoveUp", { idx })}
                            on:moveDown={() =>
                                dispatch("unifiedMoveDown", { idx })}
                            on:remove={() =>
                                dispatch("removeUnifiedStep", {
                                    stepId: unifiedStep.id,
                                    idx,
                                })}
                            on:removeCapture={(e) =>
                                dispatch("removeUnifiedCapture", {
                                    stepId: unifiedStep.id,
                                    captureId: e.detail.captureId,
                                })}
                            on:openAttachmentModal={(e) =>
                                dispatch("openUnifiedAttachmentModal", {
                                    stepId: unifiedStep.id,
                                    attachment: e.detail.attachment,
                                })}
                            on:updateAttachment={(e) =>
                                dispatch("updateUnifiedAttachment", {
                                    stepId: unifiedStep.id,
                                    attachmentId: e.detail.attachmentId,
                                    data: e.detail.data,
                                })}
                            on:removeAttachment={(e) =>
                                dispatch("removeAttachment", {
                                    stepId: unifiedStep.id,
                                    attachmentId: e.detail.attachmentId,
                                })}
                            on:addTextAttachment={() =>
                                dispatch("addUnifiedTextAttachment", {
                                    stepId: unifiedStep.id,
                                })}
                            on:paste={(e) =>
                                dispatch("handleUnifiedPaste", {
                                    event: e.detail,
                                    stepId: unifiedStep.id,
                                })}
                            on:checkboxClick={(e) =>
                                dispatch("checkboxClick", {
                                    stepId: unifiedStep.id,
                                    event: e.detail,
                                })}
                            on:cardClick={(e) =>
                                dispatch("cardCtrlClick", {
                                    stepId: unifiedStep.id,
                                    event: e.detail,
                                })}
                        />
                    </div>
                {/if}
            {/if}
        {/each}
    </div>

    <!-- Empty State -->
    {#if sortedUnifiedSteps.length === 0}
        <div
            class="flex flex-col items-center justify-center text-gray-300 py-8"
        >
            <span class="text-xs opacity-50">
                {coreStepsSettings.definitions.length > 0
                    ? "Core Step을 추가하세요"
                    : "스텝을 추가하세요"}
            </span>
        </div>
    {/if}

    <!-- Hidden Regular Steps Message (when Core Steps not complete) -->
    {#if !allCoreStepsAdded && regularStepCount > 0}
        <div
            class="text-center py-4 text-gray-400 text-xs border-t border-gray-200 mt-2"
        >
            <span class="bg-gray-100 px-2 py-1 rounded">
                {regularStepCount}개의 일반 스텝이 숨겨져 있습니다
            </span>
            <br />
            <span class="text-[10px] opacity-70"
                >모든 Core Step을 추가하면 표시됩니다</span
            >
        </div>
    {/if}

    <!-- Drop Zone for End of List -->
    <div class="flex-1 min-h-[20px]"></div>
</div>

<style>
    /* Support guide indicator container */
    .support-guide-indicator {
        display: flex;
        align-items: center;
    }
</style>
