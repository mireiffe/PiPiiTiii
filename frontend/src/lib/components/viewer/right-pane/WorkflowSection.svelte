<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import AttachmentModal from "./workflow/AttachmentModal.svelte";
    import ImageAddModal from "./workflow/ImageAddModal.svelte";
    import StepDefinitionPopup from "./workflow/StepDefinitionPopup.svelte";
    import WorkflowStepItem from "./workflow/WorkflowStepItem.svelte";
    import TimelineGraph from "./workflow/TimelineGraph.svelte";
    import {
        createDragDropHandlers,
        type DragDropState,
    } from "./workflow/useWorkflowDragDrop";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        WorkflowStepInstance,
        ProjectWorkflowData,
        StepAttachment,
        StepContainer,
    } from "$lib/types/workflow";
    import {
        createEmptyWorkflowData,
        createStepInstance,
        createStepCapture,
        createAttachment,
        generateAttachmentId,
    } from "$lib/types/workflow";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";
    import {
        uploadAttachmentImage,
        deleteAttachmentImage,
    } from "$lib/api/project";

    export let isExpanded = false;
    export let projectId: string = "";
    export let workflowData: ProjectWorkflowData = createEmptyWorkflowData();
    export let workflowSteps: WorkflowSteps = { columns: [], rows: [] };
    export let stepContainers: StepContainer[] = [];
    export let savingWorkflow = false;
    export let captureMode = false;
    export let captureTargetStepId: string | null = null;

    const dispatch = createEventDispatcher();

    let viewMode: "list" | "graph" = "list";
    let showAddStepPopup = false;
    let expandedStepId: string | null = null;
    let addingAttachmentToStepId: string | null = null;
    let attachmentTextInput = "";
    let popupRef: HTMLDivElement | null = null;

    // Attachment Modal State
    let showAttachmentModal = false;
    let editingAttachment: StepAttachment | null = null;
    let editingAttachmentStepId: string | null = null;
    let modalCaption = "";

    // Image Add Modal State
    let showImageAddModal = false;
    let pendingImageData: string | null = null;
    let pendingImageStepId: string | null = null;
    let pendingImageCaption = "";
    let isUploadingImage = false;

    // Drag & Drop State
    let dragState: DragDropState = { draggedIndex: null, dropTargetIndex: null };
    let dropTargetContainerId: string | null = null;  // For container-level drop
    let collapsedContainers: Set<string> = new Set();

    const dragDropHandlers = createDragDropHandlers(
        () => dragState,
        (newState) => (dragState = { ...dragState, ...newState }),
        (fromIndex, toIndex) => {
            const steps = [...workflowData.steps];
            const [removed] = steps.splice(fromIndex, 1);
            steps.splice(toIndex, 0, removed);
            workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
            dispatch("workflowChange", workflowData);
        },
        () => captureMode && exitCaptureMode()
    );

    // Container helpers
    function toggleContainerCollapse(containerId: string) {
        if (collapsedContainers.has(containerId)) {
            collapsedContainers.delete(containerId);
        } else {
            collapsedContainers.add(containerId);
        }
        collapsedContainers = collapsedContainers;
    }

    function getStepsByContainer(containerId: string | null): WorkflowStepInstance[] {
        return workflowData.steps.filter(s =>
            containerId === null ? !s.containerId : s.containerId === containerId
        );
    }

    function handleContainerDragOver(e: DragEvent, containerId: string | null) {
        e.preventDefault();
        if (dragState.draggedIndex !== null) {
            dropTargetContainerId = containerId;
        }
    }

    function handleContainerDragLeave() {
        dropTargetContainerId = null;
    }

    function handleContainerDrop(e: DragEvent, containerId: string | null) {
        e.preventDefault();
        if (dragState.draggedIndex === null) return;

        const step = workflowData.steps[dragState.draggedIndex];
        if (step.containerId !== containerId) {
            // Move step to new container
            const steps = workflowData.steps.map((s, i) =>
                i === dragState.draggedIndex ? { ...s, containerId: containerId || undefined } : s
            );
            workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
            dispatch("workflowChange", workflowData);
        }

        dragState = { draggedIndex: null, dropTargetIndex: null };
        dropTargetContainerId = null;
    }

    // Handle drop on a step within a container (combines reorder + container change)
    function handleStepDropWithContainer(e: DragEvent, targetContainerId: string | undefined) {
        e.preventDefault();
        e.stopPropagation();

        const { draggedIndex, dropTargetIndex } = dragState;
        if (draggedIndex === null || dropTargetIndex === null) return;

        const steps = [...workflowData.steps];
        const draggedStep = steps[draggedIndex];

        // Update container if different
        const newContainerId = targetContainerId || undefined;
        if (draggedStep.containerId !== newContainerId) {
            steps[draggedIndex] = { ...draggedStep, containerId: newContainerId };
        }

        // Reorder
        const [removed] = steps.splice(draggedIndex, 1);
        let target = dropTargetIndex;
        if (draggedIndex < target) target -= 1;
        if (target !== draggedIndex || draggedStep.containerId !== newContainerId) {
            steps.splice(target, 0, removed);
            workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
            dispatch("workflowChange", workflowData);
        }

        dragState = { draggedIndex: null, dropTargetIndex: null };
        dropTargetContainerId = null;
    }

    // Sort containers by order
    $: sortedContainers = [...stepContainers].sort((a, b) => a.order - b.order);

    // Reactive: pre-compute steps by container (workflowData.steps dependency is explicit)
    $: stepsByContainerId = (() => {
        const map: Record<string, WorkflowStepInstance[]> = { __uncategorized__: [] };
        sortedContainers.forEach(c => { map[c.id] = []; });

        workflowData.steps.forEach(step => {
            const key = step.containerId ?? '__uncategorized__';
            if (map[key]) {
                map[key].push(step);
            } else {
                // containerId references a non-existent container, put in uncategorized
                map.__uncategorized__.push(step);
            }
        });

        return map;
    })();

    // Reactive uncategorized steps
    $: uncategorizedSteps = sortedContainers.length > 0 ? (stepsByContainerId.__uncategorized__ || []) : [];

    // Helpers
    function exitCaptureMode() {
        if (captureMode) {
            dispatch("toggleCaptureMode", { stepId: null });
        }
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            if (showAttachmentModal) closeAttachmentModal();
            else if (showImageAddModal) closeImageAddModal();
            else if (captureMode) exitCaptureMode();
        }
    }

    onMount(() => window.addEventListener("keydown", handleKeyDown));
    onDestroy(() => window.removeEventListener("keydown", handleKeyDown));

    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find((r) => r.id === stepId);
    }

    function getStepUsageCount(stepId: string): number {
        return workflowData.steps.filter((s) => s.stepId === stepId).length;
    }

    // Step Management
    function handleAddStep(stepRow: WorkflowStepRow) {
        const newStep = createStepInstance(stepRow.id, workflowData.steps.length);
        workflowData = {
            ...workflowData,
            steps: [...workflowData.steps, newStep],
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
        showAddStepPopup = false;
        expandedStepId = newStep.id;
    }

    function handleRemoveStep(stepId: string) {
        if (confirm("이 스텝을 정말 삭제하시겠습니까?")) {
            if (captureTargetStepId === stepId) {
                dispatch("toggleCaptureMode", { stepId: null });
            }
            workflowData = {
                ...workflowData,
                steps: workflowData.steps.filter((s) => s.id !== stepId),
                updatedAt: new Date().toISOString(),
            };
            dispatch("workflowChange", workflowData);
        }
    }

    function toggleStepExpand(stepId: string) {
        if (captureMode) exitCaptureMode();
        expandedStepId = expandedStepId === stepId ? null : stepId;
        addingAttachmentToStepId = null;
    }

    function moveStepUp(index: number) {
        if (index === 0) return;
        const steps = [...workflowData.steps];
        [steps[index - 1], steps[index]] = [steps[index], steps[index - 1]];
        workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function moveStepDown(index: number) {
        if (index === workflowData.steps.length - 1) return;
        const steps = [...workflowData.steps];
        [steps[index], steps[index + 1]] = [steps[index + 1], steps[index]];
        workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    // Capture Management
    function startCaptureForStep(stepId: string) {
        if (captureMode && captureTargetStepId === stepId) {
            exitCaptureMode();
        } else {
            dispatch("toggleCaptureMode", { stepId });
        }
    }

    export function addCapture(capture: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
    }) {
        if (!captureTargetStepId) return;
        const stepIndex = workflowData.steps.findIndex((s) => s.id === captureTargetStepId);
        if (stepIndex === -1) return;

        const newCapture = createStepCapture(
            capture.slideIndex,
            capture.x,
            capture.y,
            capture.width,
            capture.height
        );
        workflowData.steps[stepIndex].captures = [
            ...workflowData.steps[stepIndex].captures,
            newCapture,
        ];
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function removeCapture(stepId: string, captureId: string) {
        const stepIndex = workflowData.steps.findIndex((s) => s.id === stepId);
        if (stepIndex === -1) return;
        workflowData.steps[stepIndex].captures = workflowData.steps[stepIndex].captures.filter(
            (c) => c.id !== captureId
        );
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    export function getCaptureOverlays() {
        const overlays: any[] = [];
        let colorIndex = 0;
        for (const step of workflowData.steps) {
            const color = EVIDENCE_COLORS[colorIndex % EVIDENCE_COLORS.length];
            for (const capture of step.captures) {
                overlays.push({ ...capture, stepId: step.id, color, colorIndex });
            }
            colorIndex++;
        }
        return overlays;
    }

    // Attachment Management
    function toggleAttachmentSection(stepId: string) {
        if (captureMode) exitCaptureMode();
        addingAttachmentToStepId = addingAttachmentToStepId === stepId ? null : stepId;
    }

    async function handlePaste(event: ClipboardEvent, stepId: string) {
        const items = event.clipboardData?.items;
        if (!items) return;
        for (const item of items) {
            if (item.type.startsWith("image/")) {
                event.preventDefault();
                const blob = item.getAsFile();
                if (!blob) continue;
                const reader = new FileReader();
                reader.onload = () => openImageAddModal(stepId, reader.result as string);
                reader.readAsDataURL(blob);
                return;
            }
        }
    }

    function addTextAttachment(stepId: string) {
        if (!attachmentTextInput.trim()) return;
        const stepIndex = workflowData.steps.findIndex((s) => s.id === stepId);
        if (stepIndex === -1) return;
        const attachment = createAttachment("text", attachmentTextInput.trim());
        workflowData.steps[stepIndex].attachments = [
            ...workflowData.steps[stepIndex].attachments,
            attachment,
        ];
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
        attachmentTextInput = "";
        addingAttachmentToStepId = null;
    }

    async function removeAttachment(stepId: string, attachmentId: string) {
        const stepIndex = workflowData.steps.findIndex((s) => s.id === stepId);
        if (stepIndex === -1) return;

        const attachment = workflowData.steps[stepIndex].attachments.find((a) => a.id === attachmentId);
        if (attachment?.type === "image" && attachment.imageId) {
            try {
                await deleteAttachmentImage(attachment.imageId);
            } catch (error) {
                console.error("Failed to delete image from backend:", error);
            }
        }

        workflowData.steps[stepIndex].attachments = workflowData.steps[stepIndex].attachments.filter(
            (a) => a.id !== attachmentId
        );
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    // Attachment Modal
    function openAttachmentModal(stepId: string, attachment: StepAttachment) {
        editingAttachmentStepId = stepId;
        editingAttachment = attachment;
        modalCaption = attachment.caption || "";
        showAttachmentModal = true;
    }

    function closeAttachmentModal() {
        showAttachmentModal = false;
        editingAttachment = null;
        editingAttachmentStepId = null;
        modalCaption = "";
    }

    function saveAttachmentChanges() {
        if (!editingAttachment || !editingAttachmentStepId) return;

        const stepIndex = workflowData.steps.findIndex((s) => s.id === editingAttachmentStepId);
        if (stepIndex === -1) return;

        const attachmentIndex = workflowData.steps[stepIndex].attachments.findIndex(
            (a) => a.id === editingAttachment!.id
        );
        if (attachmentIndex === -1) return;

        workflowData.steps[stepIndex].attachments[attachmentIndex] = {
            ...workflowData.steps[stepIndex].attachments[attachmentIndex],
            caption: modalCaption.trim() || undefined,
        };

        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
        closeAttachmentModal();
    }

    function deleteAttachmentFromModal() {
        if (!editingAttachment || !editingAttachmentStepId) return;
        if (confirm("이 첨부를 삭제하시겠습니까?")) {
            removeAttachment(editingAttachmentStepId, editingAttachment.id);
            closeAttachmentModal();
        }
    }

    // Image Add Modal
    function openImageAddModal(stepId: string, base64Data: string) {
        pendingImageStepId = stepId;
        pendingImageData = base64Data;
        pendingImageCaption = "";
        showImageAddModal = true;
    }

    function closeImageAddModal() {
        showImageAddModal = false;
        pendingImageData = null;
        pendingImageStepId = null;
        pendingImageCaption = "";
    }

    async function confirmAddImage() {
        if (!pendingImageStepId || !pendingImageData || !projectId) return;

        const stepIndex = workflowData.steps.findIndex((s) => s.id === pendingImageStepId);
        if (stepIndex === -1) return;

        isUploadingImage = true;
        try {
            const imageId = generateAttachmentId();
            const response = await uploadAttachmentImage(imageId, projectId, pendingImageData);

            if (!response.ok) throw new Error("Failed to upload image");

            const attachment = createAttachment("image", imageId, pendingImageCaption.trim() || undefined);
            workflowData.steps[stepIndex].attachments = [
                ...workflowData.steps[stepIndex].attachments,
                attachment,
            ];
            workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
            dispatch("workflowChange", workflowData);
            closeImageAddModal();
        } catch (error) {
            console.error("Failed to upload image:", error);
            alert("이미지 업로드에 실패했습니다.");
        } finally {
            isUploadingImage = false;
        }
    }

    // Workflow Actions
    function handleDeleteWorkflow() {
        if (confirm("워크플로우 전체를 삭제하시겠습니까?")) {
            dispatch("deleteWorkflow");
        }
    }

    function handleClickOutside(event: MouseEvent) {
        if (popupRef && !popupRef.contains(event.target as Node)) {
            showAddStepPopup = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="border-b border-gray-200 bg-white flex flex-col {isExpanded ? 'flex-1 min-h-0' : ''}">
    <AccordionHeader
        icon="⚡"
        title="Workflow"
        {isExpanded}
        on:click={() => dispatch("toggleExpand")}
    >
        <svelte:fragment slot="actions">
            {#if isExpanded}
                <div class="flex items-center gap-1 mr-2">
                    <div class="flex bg-gray-100 p-0.5 rounded-md border border-gray-200">
                        <button
                            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode === 'list'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-400 hover:text-gray-700'}"
                            on:click|stopPropagation={() => (viewMode = "list")}
                        >
                            List
                        </button>
                        <button
                            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode === 'graph'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-400 hover:text-gray-700'}"
                            on:click|stopPropagation={() => (viewMode = "graph")}
                        >
                            Graph
                        </button>
                    </div>
                    <button
                        class="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                        on:click|stopPropagation={handleDeleteWorkflow}
                        title="전체 초기화"
                    >
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
            {/if}
        </svelte:fragment>
    </AccordionHeader>

    {#if isExpanded}
        <div
            transition:slide={{ duration: 200 }}
            class="flex-1 flex flex-col min-h-[400px] bg-gray-50/50 relative overflow-hidden"
        >
            {#if viewMode === "graph"}
                <TimelineGraph
                    {workflowData}
                    {workflowSteps}
                    onNodeClick={(stepId) => {
                        expandedStepId = stepId;
                        viewMode = "list";
                    }}
                />
            {:else}
                <!-- Add Step Button -->
                <div class="p-3 pb-0 bg-gray-50/50 border-b border-gray-100 relative">
                    <button
                        class="w-full py-2.5 border border-dashed border-gray-300 rounded-lg text-gray-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-center gap-1.5 group bg-white/80"
                        on:click|stopPropagation={() => (showAddStepPopup = !showAddStepPopup)}
                    >
                        <span class="text-xs font-medium">＋ 다음 스텝 연결</span>
                    </button>

                    {#if showAddStepPopup}
                        <div bind:this={popupRef}>
                            <StepDefinitionPopup
                                {workflowSteps}
                                {getStepUsageCount}
                                on:addStep={(e) => handleAddStep(e.detail)}
                                on:deleteStepDefinition={(e) => dispatch("deleteStepDefinition", e.detail)}
                                on:createStepDefinition={(e) => dispatch("createStepDefinition", e.detail)}
                                on:updateStepDefinition={(e) => dispatch("updateStepDefinition", e.detail)}
                                on:close={() => (showAddStepPopup = false)}
                            />
                        </div>
                    {/if}
                </div>

                <!-- Step List with Containers -->
                <div class="flex-1 overflow-y-auto p-3 space-y-3 relative flex flex-col">
                    {#if sortedContainers.length === 0}
                        <!-- No containers defined: show flat list -->
                        <div class="relative">
                            <div class="absolute left-[23px] top-0 bottom-0 w-px bg-gray-200 z-0"></div>
                            {#each workflowData.steps as step, index (step.id)}
                                {@const stepDef = getStepDefinition(step.stepId)}
                                {@const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}

                                <div
                                    class="mb-2"
                                    draggable="true"
                                    on:dragstart={(e) => dragDropHandlers.handleDragStart(e, index)}
                                    on:dragend={dragDropHandlers.handleDragEnd}
                                    on:drop={dragDropHandlers.handleDrop}
                                    on:dragover={(e) => dragDropHandlers.handleDragOver(e, index)}
                                >
                                    <WorkflowStepItem
                                        {step}
                                        {index}
                                        {stepDef}
                                        {color}
                                        {workflowSteps}
                                        isExpanded={expandedStepId === step.id}
                                        isCapturing={captureTargetStepId === step.id}
                                        isAddingAttachment={addingAttachmentToStepId === step.id}
                                        isBeingDragged={dragState.draggedIndex === index}
                                        showDropIndicatorTop={dragState.dropTargetIndex === index && dragState.draggedIndex !== index && dragState.draggedIndex !== index - 1}
                                        showDropIndicatorBottom={dragState.dropTargetIndex === index + 1 && index === workflowData.steps.length - 1 && dragState.draggedIndex !== index}
                                        isLastStep={index === workflowData.steps.length - 1}
                                        {attachmentTextInput}
                                        on:toggleExpand={() => toggleStepExpand(step.id)}
                                        on:startCapture={() => startCaptureForStep(step.id)}
                                        on:toggleAttachment={() => toggleAttachmentSection(step.id)}
                                        on:moveUp={() => moveStepUp(index)}
                                        on:moveDown={() => moveStepDown(index)}
                                        on:remove={() => handleRemoveStep(step.id)}
                                        on:removeCapture={(e) => removeCapture(step.id, e.detail.captureId)}
                                        on:openAttachmentModal={(e) => openAttachmentModal(step.id, e.detail.attachment)}
                                        on:addTextAttachment={() => addTextAttachment(step.id)}
                                        on:paste={(e) => handlePaste(e.detail, step.id)}
                                    />
                                </div>
                            {/each}
                        </div>
                    {:else}
                        <!-- With containers: show grouped view -->

                        <!-- Uncategorized Steps (always shown when containers exist) -->
                        <div
                            class="rounded-lg border transition-all {dropTargetContainerId === null && dragState.draggedIndex !== null ? 'border-blue-400 border-2 bg-blue-50/50' : 'border-gray-200 bg-white'}"
                            on:dragover={(e) => handleContainerDragOver(e, null)}
                            on:dragleave={handleContainerDragLeave}
                            on:drop={(e) => handleContainerDrop(e, null)}
                        >
                            <div class="px-3 py-2 bg-gray-100 border-b border-gray-200 rounded-t-lg">
                                <span class="text-xs font-medium text-gray-500">미분류</span>
                                <span class="text-xs text-gray-400 ml-1">({uncategorizedSteps.length})</span>
                            </div>
                            <div class="p-2 space-y-2 relative min-h-[40px]">
                                    {#if uncategorizedSteps.length > 0}
                                        <div class="absolute left-[23px] top-2 bottom-2 w-px bg-gray-200 z-0"></div>
                                    {/if}
                                    {#each uncategorizedSteps as step (step.id)}
                                        {@const index = workflowData.steps.findIndex(s => s.id === step.id)}
                                        {@const stepDef = getStepDefinition(step.stepId)}
                                        {@const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}

                                        <div
                                            draggable="true"
                                            on:dragstart={(e) => dragDropHandlers.handleDragStart(e, index)}
                                            on:dragend={() => { dragDropHandlers.handleDragEnd(); dropTargetContainerId = null; }}
                                            on:drop={(e) => handleStepDropWithContainer(e, undefined)}
                                            on:dragover={(e) => dragDropHandlers.handleDragOver(e, index)}
                                        >
                                            <WorkflowStepItem
                                                {step}
                                                {index}
                                                {stepDef}
                                                {color}
                                                {workflowSteps}
                                                isExpanded={expandedStepId === step.id}
                                                isCapturing={captureTargetStepId === step.id}
                                                isAddingAttachment={addingAttachmentToStepId === step.id}
                                                isBeingDragged={dragState.draggedIndex === index}
                                                showDropIndicatorTop={dragState.dropTargetIndex === index && dragState.draggedIndex !== index && dragState.draggedIndex !== index - 1}
                                                showDropIndicatorBottom={false}
                                                isLastStep={index === workflowData.steps.length - 1}
                                                {attachmentTextInput}
                                                on:toggleExpand={() => toggleStepExpand(step.id)}
                                                on:startCapture={() => startCaptureForStep(step.id)}
                                                on:toggleAttachment={() => toggleAttachmentSection(step.id)}
                                                on:moveUp={() => moveStepUp(index)}
                                                on:moveDown={() => moveStepDown(index)}
                                                on:remove={() => handleRemoveStep(step.id)}
                                                on:removeCapture={(e) => removeCapture(step.id, e.detail.captureId)}
                                                on:openAttachmentModal={(e) => openAttachmentModal(step.id, e.detail.attachment)}
                                                on:addTextAttachment={() => addTextAttachment(step.id)}
                                                on:paste={(e) => handlePaste(e.detail, step.id)}
                                            />
                                        </div>
                                    {/each}
                                    {#if uncategorizedSteps.length === 0}
                                        <div class="text-xs text-gray-400 text-center py-2">드래그하여 여기에 놓기</div>
                                    {/if}
                            </div>
                        </div>

                        <!-- Container Groups -->
                        {#each sortedContainers as container (container.id)}
                            {@const containerSteps = stepsByContainerId[container.id] || []}
                            {@const isCollapsed = collapsedContainers.has(container.id)}
                            <div
                                class="rounded-lg border transition-all {dropTargetContainerId === container.id && dragState.draggedIndex !== null ? 'border-blue-400 border-2 bg-blue-50/50' : 'border-gray-200 bg-white'}"
                                on:dragover={(e) => handleContainerDragOver(e, container.id)}
                                on:dragleave={handleContainerDragLeave}
                                on:drop={(e) => handleContainerDrop(e, container.id)}
                            >
                                <button
                                    class="w-full px-3 py-2 bg-gradient-to-r from-blue-50 to-white border-b border-gray-200 rounded-t-lg flex items-center gap-2 hover:bg-blue-100/50 transition-colors"
                                    on:click={() => toggleContainerCollapse(container.id)}
                                >
                                    <svg class="w-3.5 h-3.5 text-gray-500 transition-transform {isCollapsed ? '' : 'rotate-90'}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                    </svg>
                                    <span class="text-xs font-medium text-blue-700">{container.name}</span>
                                    <span class="text-xs text-gray-400">({containerSteps.length})</span>
                                </button>
                                {#if !isCollapsed}
                                    <div class="p-2 space-y-2 relative min-h-[40px]">
                                        {#if containerSteps.length > 0}
                                            <div class="absolute left-[23px] top-2 bottom-2 w-px bg-blue-200 z-0"></div>
                                        {/if}
                                        {#each containerSteps as step (step.id)}
                                            {@const index = workflowData.steps.findIndex(s => s.id === step.id)}
                                            {@const stepDef = getStepDefinition(step.stepId)}
                                            {@const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}

                                            <div
                                                draggable="true"
                                                on:dragstart={(e) => dragDropHandlers.handleDragStart(e, index)}
                                                on:dragend={() => { dragDropHandlers.handleDragEnd(); dropTargetContainerId = null; }}
                                                on:drop={(e) => handleStepDropWithContainer(e, container.id)}
                                                on:dragover={(e) => dragDropHandlers.handleDragOver(e, index)}
                                            >
                                                <WorkflowStepItem
                                                    {step}
                                                    {index}
                                                    {stepDef}
                                                    {color}
                                                    {workflowSteps}
                                                    isExpanded={expandedStepId === step.id}
                                                    isCapturing={captureTargetStepId === step.id}
                                                    isAddingAttachment={addingAttachmentToStepId === step.id}
                                                    isBeingDragged={dragState.draggedIndex === index}
                                                    showDropIndicatorTop={dragState.dropTargetIndex === index && dragState.draggedIndex !== index && dragState.draggedIndex !== index - 1}
                                                    showDropIndicatorBottom={false}
                                                    isLastStep={index === workflowData.steps.length - 1}
                                                    {attachmentTextInput}
                                                    on:toggleExpand={() => toggleStepExpand(step.id)}
                                                    on:startCapture={() => startCaptureForStep(step.id)}
                                                    on:toggleAttachment={() => toggleAttachmentSection(step.id)}
                                                    on:moveUp={() => moveStepUp(index)}
                                                    on:moveDown={() => moveStepDown(index)}
                                                    on:remove={() => handleRemoveStep(step.id)}
                                                    on:removeCapture={(e) => removeCapture(step.id, e.detail.captureId)}
                                                    on:openAttachmentModal={(e) => openAttachmentModal(step.id, e.detail.attachment)}
                                                    on:addTextAttachment={() => addTextAttachment(step.id)}
                                                    on:paste={(e) => handlePaste(e.detail, step.id)}
                                                />
                                            </div>
                                        {/each}
                                        {#if containerSteps.length === 0}
                                            <div class="text-xs text-gray-400 text-center py-2">드래그하여 여기에 놓기</div>
                                        {/if}
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    {/if}

                    {#if workflowData.steps.length === 0}
                        <div class="flex flex-col items-center justify-center text-gray-300 py-8">
                            <span class="text-xs opacity-50">스텝을 추가하세요</span>
                        </div>
                    {/if}

                    <!-- Drop Zone for End of List -->
                    <div class="flex-1 min-h-[20px]"></div>
                </div>

                <!-- Modals -->
                {#if showAttachmentModal && editingAttachment}
                    <AttachmentModal
                        attachment={editingAttachment}
                        caption={modalCaption}
                        on:save={(e) => {
                            modalCaption = e.detail.caption;
                            if (editingAttachment.type === "text") {
                                editingAttachment.data = e.detail.text;
                            }
                            saveAttachmentChanges();
                        }}
                        on:delete={deleteAttachmentFromModal}
                        on:close={closeAttachmentModal}
                    />
                {/if}

                {#if showImageAddModal && pendingImageData}
                    <ImageAddModal
                        imageData={pendingImageData}
                        caption={pendingImageCaption}
                        isUploading={isUploadingImage}
                        on:confirm={(e) => {
                            pendingImageCaption = e.detail.caption;
                            confirmAddImage();
                        }}
                        on:cancel={closeImageAddModal}
                    />
                {/if}
            {/if}
        </div>
    {/if}
</div>
