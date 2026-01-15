<script lang="ts">
    import { slide, fade, fly } from "svelte/transition";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import AttachmentModal from "./workflow/AttachmentModal.svelte";
    import ImageAddModal from "./workflow/ImageAddModal.svelte";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        WorkflowStepInstance,
        ProjectWorkflowData,
        StepAttachment,
    } from "$lib/types/workflow";
    import {
        createEmptyWorkflowData,
        createStepInstance,
        createStepCapture,
        createAttachment,
        generateAttachmentId,
    } from "$lib/types/workflow";
    import TimelineGraph from "./workflow/TimelineGraph.svelte";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";
    import {
        uploadAttachmentImage,
        getAttachmentImageUrl,
        deleteAttachmentImage,
    } from "$lib/api/project";

    export let isExpanded = false;
    export let projectId: string = "";  // Required for image uploads
    export let workflowData: ProjectWorkflowData = createEmptyWorkflowData();
    export let workflowSteps: WorkflowSteps = { columns: [], rows: [] };
    export let savingWorkflow = false;
    export let captureMode = false;
    export let captureTargetStepId: string | null = null;

    const dispatch = createEventDispatcher();

    let viewMode: "list" | "graph" = "list";
    let showAddStepPopup = false;
    let searchQuery = "";
    let selectedCategoryTab = "all";
    let expandedStepId: string | null = null;
    let addingAttachmentToStepId: string | null = null;
    let attachmentTextInput = "";
    let popupRef: HTMLDivElement | null = null;

    // --- Attachment Modal State ---
    let showAttachmentModal = false;
    let editingAttachment: StepAttachment | null = null;
    let editingAttachmentStepId: string | null = null;
    let modalCaption = "";

    // --- Image Add Modal State ---
    let showImageAddModal = false;
    let pendingImageData: string | null = null;
    let pendingImageStepId: string | null = null;
    let pendingImageCaption = "";

    // --- Drag & Drop State ---
    let draggedIndex: number | null = null;
    let dropTargetIndex: number | null = null;

    function handleDragStart(event: DragEvent, index: number) {
        if (captureMode) exitCaptureMode();
        draggedIndex = index;
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            // Required for Firefox
            event.dataTransfer.setData("text/plain", index.toString());
        }
    }

    function handleDragOver(event: DragEvent, index: number) {
        event.preventDefault();
        event.stopPropagation();
        if (draggedIndex === null) return;

        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }

        // Calculate drop position based on mouse Y relative to target center
        const target = event.currentTarget as HTMLElement;
        const rect = target.getBoundingClientRect();
        const offsetY = event.clientY - rect.top;
        const isTopHalf = offsetY < rect.height / 2;

        dropTargetIndex = isTopHalf ? index : index + 1;
    }

    function handleDragLeave(event: DragEvent) {
        // Optional: clear if leaving the list entirely?
        // For now, keep the last valid target to prevent flickering
    }

    function handleContainerDragOver(event: DragEvent) {
        event.preventDefault();
        if (draggedIndex === null) return;
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }
        dropTargetIndex = workflowData.steps.length;
    }

    function handleContainerDrop(event: DragEvent) {
        event.preventDefault();
        if (draggedIndex === null) return;
        dropTargetIndex = workflowData.steps.length;
        handleDrop(event);
    }

    function handleDragEnd() {
        draggedIndex = null;
        dropTargetIndex = null;
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();

        if (draggedIndex !== null && dropTargetIndex !== null) {
            let target = dropTargetIndex;

            // Adjust target index if dragging downwards because removing the item shifts subsequent indices
            if (draggedIndex < target) {
                target -= 1;
            }

            // Only move if target position is different from current position
            if (target !== draggedIndex) {
                const steps = [...workflowData.steps];
                const [removed] = steps.splice(draggedIndex, 1);
                steps.splice(target, 0, removed);

                workflowData = {
                    ...workflowData,
                    steps,
                    updatedAt: new Date().toISOString(),
                };
                dispatch("workflowChange", workflowData);
            }
        }

        draggedIndex = null;
        dropTargetIndex = null;
    }

    // --- Helpers & Handlers ---

    function exitCaptureMode() {
        if (captureMode) {
            dispatch("toggleCaptureMode", { stepId: null });
        }
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            if (showAttachmentModal) {
                closeAttachmentModal();
            } else if (showImageAddModal) {
                closeImageAddModal();
            } else if (captureMode) {
                exitCaptureMode();
            }
        }
    }

    onMount(() => {
        window.addEventListener("keydown", handleKeyDown);
    });

    onDestroy(() => {
        window.removeEventListener("keydown", handleKeyDown);
    });

    $: categories = [
        ...new Set(
            workflowSteps.rows
                .map((r) => r.values["step_category"])
                .filter(Boolean),
        ),
    ];

    $: filteredSteps = workflowSteps.rows.filter((row) => {
        if (selectedCategoryTab !== "all") {
            if (row.values["step_category"] !== selectedCategoryTab)
                return false;
        }
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            return Object.values(row.values).some((v) =>
                v?.toLowerCase().includes(query),
            );
        }
        return true;
    });

    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find((r) => r.id === stepId);
    }

    function getStepDisplayText(step: WorkflowStepInstance): string {
        const def = getStepDefinition(step.stepId);
        if (!def) return "Unknown Step";
        return def.values["purpose"] || def.values["step_category"] || def.id;
    }

    function handleAddStep(stepRow: WorkflowStepRow) {
        const newStep = createStepInstance(
            stepRow.id,
            workflowData.steps.length,
        );
        workflowData = {
            ...workflowData,
            steps: [...workflowData.steps, newStep],
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
        showAddStepPopup = false;
        searchQuery = "";
        expandedStepId = newStep.id;
    }

    // Count how many times a step definition is used in current workflow
    function getStepUsageCount(stepId: string): number {
        return workflowData.steps.filter((s) => s.stepId === stepId).length;
    }

    // Handle delete from popup - only allowed for UNUSED step definitions
    function handleDeleteStepFromPopup(
        event: MouseEvent,
        stepRow: WorkflowStepRow,
    ) {
        event.stopPropagation();
        const usageCount = getStepUsageCount(stepRow.id);

        if (usageCount > 0) {
            alert(
                `이 스텝은 워크플로우에서 ${usageCount}번 사용 중입니다.\n설정 페이지에서 직접 삭제해주세요.`,
            );
            return;
        }

        // usageCount === 0 - can delete from settings
        if (
            confirm(
                "이 스텝 정의를 설정에서 삭제하시겠습니까?\n(모든 프로젝트에서 이 스텝을 사용할 수 없게 됩니다)",
            )
        ) {
            dispatch("deleteStepDefinition", { stepId: stepRow.id });
            showAddStepPopup = false;
        }
    }

    // State for adding new step
    let showNewStepForm = false;
    let newStepValues: Record<string, string> = {};

    // State for editing step definition
    let editingStepDefId: string | null = null;
    let editStepValues: Record<string, string> = {};

    function initNewStepForm() {
        newStepValues = {};
        workflowSteps.columns.forEach((col) => {
            newStepValues[col.id] = "";
        });
        showNewStepForm = true;
    }

    function handleAddNewStep() {
        // Check if purpose is filled (required)
        if (!newStepValues["purpose"]?.trim()) {
            alert("목적을 입력해주세요.");
            return;
        }

        // Trim all values
        const trimmedValues: Record<string, string> = {};
        Object.keys(newStepValues).forEach((key) => {
            trimmedValues[key] = newStepValues[key]?.trim() || "";
        });

        dispatch("createStepDefinition", { values: trimmedValues });

        // Reset form
        newStepValues = {};
        showNewStepForm = false;
    }

    function cancelNewStepForm() {
        newStepValues = {};
        showNewStepForm = false;
    }

    // --- Step Definition Edit Functions ---
    function initEditStepForm(stepRow: WorkflowStepRow, event: MouseEvent) {
        event.stopPropagation();
        editStepValues = { ...stepRow.values };
        editingStepDefId = stepRow.id;
        showNewStepForm = false; // Close new step form if open
    }

    function handleUpdateStepDef() {
        if (!editingStepDefId) return;

        // Check if purpose is filled (required)
        if (!editStepValues["purpose"]?.trim()) {
            alert("목적을 입력해주세요.");
            return;
        }

        // Trim all values
        const trimmedValues: Record<string, string> = {};
        Object.keys(editStepValues).forEach((key) => {
            trimmedValues[key] = editStepValues[key]?.trim() || "";
        });

        dispatch("updateStepDefinition", {
            stepId: editingStepDefId,
            values: trimmedValues,
        });

        // Reset form
        editStepValues = {};
        editingStepDefId = null;
    }

    function cancelEditStepForm() {
        editStepValues = {};
        editingStepDefId = null;
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

    function startCaptureForStep(stepId: string) {
        if (captureMode && captureTargetStepId === stepId) {
            exitCaptureMode();
        } else {
            dispatch("toggleCaptureMode", { stepId });
        }
    }

    function toggleAttachmentSection(stepId: string) {
        if (captureMode) exitCaptureMode();
        addingAttachmentToStepId =
            addingAttachmentToStepId === stepId ? null : stepId;
    }

    export function addCapture(capture: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
    }) {
        if (!captureTargetStepId) return;
        const stepIndex = workflowData.steps.findIndex(
            (s) => s.id === captureTargetStepId,
        );
        if (stepIndex === -1) return;

        const newCapture = createStepCapture(
            capture.slideIndex,
            capture.x,
            capture.y,
            capture.width,
            capture.height,
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
        workflowData.steps[stepIndex].captures = workflowData.steps[
            stepIndex
        ].captures.filter((c) => c.id !== captureId);
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
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
                reader.onload = () =>
                    addImageAttachment(stepId, reader.result as string);
                reader.readAsDataURL(blob);
                return;
            }
        }
    }

    function addImageAttachment(stepId: string, base64Data: string) {
        // Open modal for image caption input
        openImageAddModal(stepId, base64Data);
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

        // Find the attachment to check if it's an image
        const attachment = workflowData.steps[stepIndex].attachments.find(
            (a) => a.id === attachmentId,
        );

        // If it's an image attachment, delete from backend
        if (attachment?.type === "image" && attachment.imageId) {
            try {
                await deleteAttachmentImage(attachment.imageId);
            } catch (error) {
                console.error("Failed to delete image from backend:", error);
                // Continue with local removal even if backend deletion fails
            }
        }

        workflowData.steps[stepIndex].attachments = workflowData.steps[
            stepIndex
        ].attachments.filter((a) => a.id !== attachmentId);
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    // --- Attachment Modal Functions ---
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

        const stepIndex = workflowData.steps.findIndex(
            (s) => s.id === editingAttachmentStepId,
        );
        if (stepIndex === -1) return;

        const attachmentIndex = workflowData.steps[
            stepIndex
        ].attachments.findIndex((a) => a.id === editingAttachment!.id);
        if (attachmentIndex === -1) return;

        workflowData.steps[stepIndex].attachments[attachmentIndex] = {
            ...workflowData.steps[stepIndex].attachments[attachmentIndex],
            caption: modalCaption.trim() || undefined,
        };

        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
        closeAttachmentModal();
    }

    function updateAttachmentText(newText: string) {
        if (
            !editingAttachment ||
            !editingAttachmentStepId ||
            editingAttachment.type !== "text"
        )
            return;

        const stepIndex = workflowData.steps.findIndex(
            (s) => s.id === editingAttachmentStepId,
        );
        if (stepIndex === -1) return;

        const attachmentIndex = workflowData.steps[
            stepIndex
        ].attachments.findIndex((a) => a.id === editingAttachment!.id);
        if (attachmentIndex === -1) return;

        workflowData.steps[stepIndex].attachments[attachmentIndex] = {
            ...workflowData.steps[stepIndex].attachments[attachmentIndex],
            data: newText,
        };

        editingAttachment = { ...editingAttachment, data: newText };
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function deleteAttachmentFromModal() {
        if (!editingAttachment || !editingAttachmentStepId) return;
        if (confirm("이 첨부를 삭제하시겠습니까?")) {
            removeAttachment(editingAttachmentStepId, editingAttachment.id);
            closeAttachmentModal();
        }
    }

    // --- Image Add Modal Functions ---
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

    let isUploadingImage = false;

    async function confirmAddImage() {
        if (!pendingImageStepId || !pendingImageData || !projectId) return;

        const stepIndex = workflowData.steps.findIndex(
            (s) => s.id === pendingImageStepId,
        );
        if (stepIndex === -1) return;

        isUploadingImage = true;
        try {
            // Generate a unique image ID
            const imageId = generateAttachmentId();

            // Upload image to backend
            const response = await uploadAttachmentImage(
                imageId,
                projectId,
                pendingImageData,
            );

            if (!response.ok) {
                throw new Error("Failed to upload image");
            }

            // Create attachment with imageId reference (not base64 data)
            const attachment = createAttachment(
                "image",
                imageId,  // Now stores imageId, not base64
                pendingImageCaption.trim() || undefined,
            );
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

    export function getCaptureOverlays() {
        const overlays: any[] = [];
        let colorIndex = 0;
        for (const step of workflowData.steps) {
            const color = EVIDENCE_COLORS[colorIndex % EVIDENCE_COLORS.length];
            for (const capture of step.captures) {
                overlays.push({
                    ...capture,
                    stepId: step.id,
                    color,
                    colorIndex,
                });
            }
            colorIndex++;
        }
        return overlays;
    }

    function handleDeleteWorkflow() {
        if (confirm("워크플로우 전체를 삭제하시겠습니까?")) {
            dispatch("deleteWorkflow");
        }
    }

    function moveStepUp(index: number) {
        if (index === 0) return;
        const steps = [...workflowData.steps];
        [steps[index - 1], steps[index]] = [steps[index], steps[index - 1]];
        workflowData = {
            ...workflowData,
            steps,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    function moveStepDown(index: number) {
        if (index === workflowData.steps.length - 1) return;
        const steps = [...workflowData.steps];
        [steps[index], steps[index + 1]] = [steps[index + 1], steps[index]];
        workflowData = {
            ...workflowData,
            steps,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    function handleClickOutside(event: MouseEvent) {
        if (popupRef && !popupRef.contains(event.target as Node)) {
            showAddStepPopup = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div
    class="border-b border-gray-200 bg-white flex flex-col {isExpanded
        ? 'flex-1 min-h-0'
        : ''}"
>
    <AccordionHeader
        icon="⚡"
        title="Workflow"
        {isExpanded}
        on:click={() => dispatch("toggleExpand")}
    >
        <svelte:fragment slot="actions">
            {#if isExpanded}
                <div class="flex items-center gap-1 mr-2">
                    <div
                        class="flex bg-gray-100 p-0.5 rounded-md border border-gray-200"
                    >
                        <button
                            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode ===
                            'list'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-400 hover:text-gray-700'}"
                            on:click|stopPropagation={() => (viewMode = "list")}
                        >
                            List
                        </button>
                        <button
                            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode ===
                            'graph'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-400 hover:text-gray-700'}"
                            on:click|stopPropagation={() =>
                                (viewMode = "graph")}
                        >
                            Graph
                        </button>
                    </div>
                    <button
                        class="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                        on:click|stopPropagation={handleDeleteWorkflow}
                        title="전체 초기화"
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
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
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
                <!-- Add Step Button - Fixed at top -->
                <div
                    class="p-3 pb-0 bg-gray-50/50 border-b border-gray-100 relative"
                >
                    <button
                        class="w-full py-2.5 border border-dashed border-gray-300 rounded-lg text-gray-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-center gap-1.5 group bg-white/80"
                        on:click|stopPropagation={() =>
                            (showAddStepPopup = !showAddStepPopup)}
                    >
                        <span class="text-xs font-medium"
                            >＋ 다음 스텝 연결</span
                        >
                    </button>

                    {#if showAddStepPopup}
                        <div
                            bind:this={popupRef}
                            class="absolute top-full left-3 right-3 mt-1 bg-white rounded-lg shadow-xl border border-gray-200 z-50 flex flex-col max-h-[600px] overflow-hidden"
                            transition:fly={{ y: -10, duration: 150 }}
                            on:click|stopPropagation
                        >
                            <div
                                class="p-2 border-b border-gray-100 bg-gray-50/80 backdrop-blur sticky top-0"
                            >
                                <div class="relative mb-1.5">
                                    <svg
                                        class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                                        /></svg
                                    >
                                    <input
                                        type="text"
                                        bind:value={searchQuery}
                                        placeholder="작업 검색..."
                                        class="w-full pl-8 pr-2 py-1.5 text-xs bg-white border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                                        autoFocus
                                    />
                                </div>
                                <div
                                    class="flex gap-1 overflow-x-auto no-scrollbar pb-0.5"
                                >
                                    <button
                                        class="px-2 py-0.5 text-[10px] font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab ===
                                        'all'
                                            ? 'bg-gray-700 text-white'
                                            : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}"
                                        on:click={() =>
                                            (selectedCategoryTab = "all")}
                                    >
                                        All
                                    </button>
                                    {#each categories as category}
                                        <button
                                            class="px-2 py-0.5 text-[10px] font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab ===
                                            category
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}"
                                            on:click={() =>
                                                (selectedCategoryTab =
                                                    category)}
                                        >
                                            {category}
                                        </button>
                                    {/each}
                                </div>
                            </div>

                            <div
                                class="flex-1 overflow-y-auto p-2 bg-gray-50/50 space-y-1.5"
                            >
                                <!-- New Step Form -->
                                {#if showNewStepForm}
                                    <div
                                        class="p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-2.5"
                                        transition:slide={{ duration: 150 }}
                                    >
                                        <div
                                            class="text-xs font-medium text-blue-700"
                                        >
                                            새 스텝 추가
                                        </div>
                                        <div class="space-y-2">
                                            {#each workflowSteps.columns as column (column.id)}
                                                <div
                                                    class="flex items-center gap-2"
                                                >
                                                    <label
                                                        class="text-[10px] text-gray-500 w-16 shrink-0 text-right"
                                                    >
                                                        {column.name}
                                                        {#if column.id === "purpose"}
                                                            <span
                                                                class="text-red-500"
                                                                >*</span
                                                            >
                                                        {/if}
                                                    </label>
                                                    <input
                                                        type="text"
                                                        bind:value={
                                                            newStepValues[
                                                                column.id
                                                            ]
                                                        }
                                                        placeholder={column.name}
                                                        class="flex-1 px-2 py-1 text-xs border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400 bg-white"
                                                        on:keypress={(e) =>
                                                            e.key === "Enter" &&
                                                            handleAddNewStep()}
                                                    />
                                                </div>
                                            {/each}
                                        </div>
                                        <div
                                            class="flex justify-end gap-2 pt-1"
                                        >
                                            <button
                                                class="px-2.5 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                                                on:click={cancelNewStepForm}
                                            >
                                                취소
                                            </button>
                                            <button
                                                class="px-2.5 py-1 text-[10px] bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors font-medium"
                                                on:click={handleAddNewStep}
                                            >
                                                추가
                                            </button>
                                        </div>
                                    </div>
                                {:else}
                                    <button
                                        class="w-full p-2 border border-dashed border-blue-300 rounded-lg text-blue-500 hover:bg-blue-50 hover:border-blue-400 transition-all flex items-center justify-center gap-1 text-xs"
                                        on:click={initNewStepForm}
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
                                                d="M12 4v16m8-8H4"
                                            />
                                        </svg>
                                        새 스텝 정의 추가
                                    </button>
                                {/if}

                                {#if filteredSteps.length === 0 && !showNewStepForm}
                                    <div class="py-6 text-center text-gray-400">
                                        <p class="text-[10px]">
                                            일치하는 스텝이 없습니다
                                        </p>
                                    </div>
                                {:else}
                                    {#each filteredSteps as step, idx (step.id)}
                                        {@const usageCount = getStepUsageCount(
                                            step.id,
                                        )}
                                        {@const isEditing = editingStepDefId === step.id}

                                        {#if isEditing}
                                            <!-- Edit Step Form -->
                                            <div
                                                class="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-2.5"
                                                transition:slide={{ duration: 150 }}
                                                on:click|stopPropagation
                                            >
                                                <div
                                                    class="text-xs font-medium text-amber-700 flex items-center gap-1.5"
                                                >
                                                    <svg
                                                        class="w-3.5 h-3.5"
                                                        viewBox="0 0 24 24"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        stroke-width="2"
                                                    >
                                                        <path
                                                            d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"
                                                        />
                                                        <path
                                                            d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"
                                                        />
                                                    </svg>
                                                    스텝 정의 편집
                                                </div>
                                                <div class="space-y-2">
                                                    {#each workflowSteps.columns as column (column.id)}
                                                        <div
                                                            class="flex items-center gap-2"
                                                        >
                                                            <label
                                                                class="text-[10px] text-gray-500 w-16 shrink-0 text-right"
                                                            >
                                                                {column.name}
                                                                {#if column.id === "purpose"}
                                                                    <span
                                                                        class="text-red-500"
                                                                        >*</span
                                                                    >
                                                                {/if}
                                                            </label>
                                                            <input
                                                                type="text"
                                                                bind:value={
                                                                    editStepValues[
                                                                        column.id
                                                                    ]
                                                                }
                                                                placeholder={column.name}
                                                                class="flex-1 px-2 py-1 text-xs border border-amber-200 rounded focus:outline-none focus:ring-1 focus:ring-amber-400 bg-white"
                                                                on:keypress={(e) =>
                                                                    e.key === "Enter" &&
                                                                    handleUpdateStepDef()}
                                                            />
                                                        </div>
                                                    {/each}
                                                </div>
                                                <div
                                                    class="flex justify-end gap-2 pt-1"
                                                >
                                                    <button
                                                        class="px-2.5 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                                                        on:click={cancelEditStepForm}
                                                    >
                                                        취소
                                                    </button>
                                                    <button
                                                        class="px-2.5 py-1 text-[10px] bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors font-medium"
                                                        on:click={handleUpdateStepDef}
                                                    >
                                                        저장
                                                    </button>
                                                </div>
                                            </div>
                                        {:else}
                                        <div
                                            class="w-full text-left p-2.5 bg-white hover:bg-blue-50/80 rounded-lg group transition-all flex items-start gap-2.5 cursor-pointer border border-gray-100 hover:border-blue-200 hover:shadow-sm"
                                            on:click={() => handleAddStep(step)}
                                        >
                                            <!-- Index number -->
                                            <div
                                                class="shrink-0 w-5 h-5 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center text-[10px] font-semibold group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors"
                                            >
                                                {idx + 1}
                                            </div>

                                            <div class="flex-1 min-w-0">
                                                <div
                                                    class="flex items-start gap-1.5 mb-1"
                                                >
                                                    <span
                                                        class="inline-flex items-center justify-center px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-bold tracking-tight shrink-0 step-category-badge"
                                                    >
                                                        {step.values[
                                                            "step_category"
                                                        ] || "ETC"}
                                                    </span>
                                                    <span
                                                        class="text-xs font-medium text-gray-800 group-hover:text-blue-700 break-words leading-snug flex-1"
                                                    >
                                                        {step.values[
                                                            "purpose"
                                                        ] || "목적 없음"}
                                                    </span>
                                                </div>
                                                <div
                                                    class="text-[10px] text-gray-400 pl-0.5 break-words leading-snug line-clamp-2"
                                                >
                                                    {step.values["system"] ||
                                                        step.values[
                                                            "expected_result"
                                                        ] ||
                                                        "-"}
                                                </div>
                                            </div>

                                            <div
                                                class="flex items-center gap-1.5 shrink-0 self-center"
                                            >
                                                {#if usageCount > 0}
                                                    <span
                                                        class="text-[9px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-medium whitespace-nowrap"
                                                    >
                                                        {usageCount}회 사용
                                                    </span>
                                                {/if}
                                                <!-- Edit button -->
                                                <button
                                                    class="p-1 hover:bg-blue-100 rounded text-gray-300 hover:text-blue-500 transition-colors"
                                                    on:click={(e) =>
                                                        initEditStepForm(
                                                            step,
                                                            e,
                                                        )}
                                                    title="스텝 정의 편집"
                                                >
                                                    <svg
                                                        class="w-3 h-3"
                                                        viewBox="0 0 24 24"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        stroke-width="2"
                                                    >
                                                        <path
                                                            d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"
                                                        />
                                                        <path
                                                            d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"
                                                        />
                                                    </svg>
                                                </button>
                                                <!-- Delete button -->
                                                {#if usageCount > 0}
                                                    <span
                                                        class="p-1 text-gray-200 cursor-not-allowed"
                                                        title="사용 중인 스텝은 설정에서 삭제해주세요"
                                                    >
                                                        <svg
                                                            class="w-3 h-3"
                                                            viewBox="0 0 24 24"
                                                            fill="none"
                                                            stroke="currentColor"
                                                            stroke-width="2"
                                                        >
                                                            <path
                                                                d="M12 15v2m0 0v2m0-2h2m-2 0H10m9.364-9.364l-2.829 2.829m0 0L14.5 12.5m2.036-2.035a3 3 0 10-4.07 4.07m4.07-4.07l-4.07 4.07M5.636 5.636l2.829 2.829m0 0l2.035 2.035m-2.035-2.035a3 3 0 104.07 4.07"
                                                            />
                                                        </svg>
                                                    </span>
                                                {:else}
                                                    <button
                                                        class="p-1 hover:bg-red-100 rounded text-gray-300 hover:text-red-500 transition-colors"
                                                        on:click={(e) =>
                                                            handleDeleteStepFromPopup(
                                                                e,
                                                                step,
                                                            )}
                                                        title="스텝 정의 삭제"
                                                    >
                                                        <svg
                                                            class="w-3 h-3"
                                                            viewBox="0 0 24 24"
                                                            fill="none"
                                                            stroke="currentColor"
                                                            stroke-width="2"
                                                        >
                                                            <path
                                                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                                            />
                                                        </svg>
                                                    </button>
                                                {/if}
                                            </div>
                                        </div>
                                        {/if}
                                    {/each}
                                {/if}
                            </div>
                        </div>
                    {/if}
                </div>

                <div
                    class="flex-1 overflow-y-auto p-3 space-y-2 relative flex flex-col"
                >
                    <div
                        class="absolute left-[23px] top-3 bottom-3 w-px bg-gray-200 z-0"
                    ></div>

                    {#each workflowData.steps as step, index (step.id)}
                        {@const stepDef = getStepDefinition(step.stepId)}
                        {@const color =
                            EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}
                        {@const isCapturing = captureTargetStepId === step.id}
                        {@const isAddingAttach =
                            addingAttachmentToStepId === step.id}
                        {@const stepTransform = ""}
                        {@const isBeingDragged = draggedIndex === index}
                        {@const showDropIndicatorTop =
                            dropTargetIndex === index}
                        {@const showDropIndicatorBottom =
                            dropTargetIndex === index + 1}

                        <div
                            class="step-item relative z-10 pl-7 transition-all duration-200"
                            style={isBeingDragged ? "opacity: 0.5;" : ""}
                            draggable="true"
                            on:dragstart={(e) => handleDragStart(e, index)}
                            on:dragend={handleDragEnd}
                            on:drop={handleDrop}
                            on:dragover={(e) => handleDragOver(e, index)}
                        >
                            {#if showDropIndicatorTop && draggedIndex !== index && draggedIndex !== index - 1}
                                <!-- Visual polish: don't show if moving to self position -->
                                <div
                                    class="absolute top-0 left-7 right-0 h-0.5 bg-blue-500 rounded-full z-50 pointer-events-none transform -translate-y-1/2 shadow-sm"
                                ></div>
                            {/if}

                            <!-- Special case: logic for bottom indicator is needed only for the last item or we rely on top indicators of next items. 
                                 But since we render a list, the 'bottom' of item N is the 'top' of item N+1.
                                 Exception: Last item.
                            -->
                            {#if showDropIndicatorBottom && index === workflowData.steps.length - 1 && draggedIndex !== index}
                                <div
                                    class="absolute bottom-0 left-7 right-0 h-0.5 bg-blue-500 rounded-full z-50 pointer-events-none transform translate-y-1/2 shadow-sm"
                                ></div>
                            {/if}

                            <div
                                class="absolute left-0 top-2.5 w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold shadow-sm transition-all duration-200"
                                style="background-color: {color.border}; color: white;"
                            >
                                {index + 1}
                            </div>

                            <div
                                class="bg-white rounded-lg border shadow-sm overflow-hidden transition-all duration-200 group
                                {expandedStepId === step.id
                                    ? 'ring-1 ring-blue-500/20 shadow-md border-blue-300'
                                    : 'border-gray-200 hover:border-blue-300'}
                                {isBeingDragged
                                    ? 'shadow-none border-blue-200 bg-blue-50/20 ring-0'
                                    : ''}"
                            >
                                <div
                                    class="p-2 cursor-pointer hover:bg-gray-50/50 flex items-start justify-between gap-2"
                                    on:click={() => toggleStepExpand(step.id)}
                                >
                                    <!-- Drag Handle -->
                                    <div
                                        class="flex items-center pr-1 cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity self-center"
                                    >
                                        <svg
                                            class="w-3 h-3"
                                            viewBox="0 0 24 24"
                                            fill="currentColor"
                                        >
                                            <circle
                                                cx="9"
                                                cy="6"
                                                r="2"
                                            /><circle cx="15" cy="6" r="2" />
                                            <circle
                                                cx="9"
                                                cy="12"
                                                r="2"
                                            /><circle cx="15" cy="12" r="2" />
                                            <circle
                                                cx="9"
                                                cy="18"
                                                r="2"
                                            /><circle cx="15" cy="18" r="2" />
                                        </svg>
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div
                                            class="flex items-center flex-wrap gap-1.5 mb-0.5"
                                        >
                                            {#if stepDef?.values["step_category"]}
                                                <span
                                                    class="inline-flex px-1.5 py-px rounded text-[10px] font-semibold tracking-tight bg-gray-100 text-gray-500 border border-gray-100"
                                                >
                                                    {stepDef.values[
                                                        "step_category"
                                                    ]}
                                                </span>
                                            {/if}
                                            <h4
                                                class="text-xs font-medium text-gray-800 leading-tight break-words flex-1"
                                            >
                                                {getStepDisplayText(step)}
                                            </h4>
                                        </div>

                                        {#if step.captures.length > 0 || step.attachments.length > 0}
                                            <div class="flex gap-2 mt-1">
                                                {#if step.captures.length > 0}
                                                    <span
                                                        class="text-[9px] text-blue-600 flex items-center gap-0.5 opacity-80"
                                                    >
                                                        📷 {step.captures
                                                            .length}
                                                    </span>
                                                {/if}
                                                {#if step.attachments.length > 0}
                                                    <span
                                                        class="text-[9px] text-amber-600 flex items-center gap-0.5 opacity-80"
                                                    >
                                                        📎 {step.attachments
                                                            .length}
                                                    </span>
                                                {/if}
                                            </div>
                                        {/if}
                                    </div>

                                    <div
                                        class="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity {expandedStepId ===
                                        step.id
                                            ? 'opacity-100'
                                            : ''}"
                                    >
                                        <button
                                            class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500 disabled:opacity-10"
                                            on:click|stopPropagation={() =>
                                                moveStepUp(index)}
                                            disabled={index === 0}
                                        >
                                            <svg
                                                class="w-2.5 h-2.5"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                                ><path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    stroke-width="2"
                                                    d="M5 15l7-7 7 7"
                                                /></svg
                                            >
                                        </button>
                                        <button
                                            class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500 disabled:opacity-10"
                                            on:click|stopPropagation={() =>
                                                moveStepDown(index)}
                                            disabled={index ===
                                                workflowData.steps.length - 1}
                                        >
                                            <svg
                                                class="w-2.5 h-2.5"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                                ><path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    stroke-width="2"
                                                    d="M19 9l-7 7-7-7"
                                                /></svg
                                            >
                                        </button>
                                    </div>
                                </div>

                                {#if expandedStepId === step.id}
                                    <div
                                        class="px-2 pb-2 space-y-2"
                                        transition:slide|local={{
                                            duration: 150,
                                        }}
                                    >
                                        {#if stepDef}
                                            <div
                                                class="bg-gray-50 rounded-lg p-3 border border-gray-100 flex flex-wrap gap-x-4 gap-y-3"
                                            >
                                                {#each workflowSteps.columns.filter((col) => stepDef.values[col.id]) as col}
                                                    <div
                                                        class="flex flex-col gap-0.5 min-w-[120px] flex-1"
                                                    >
                                                        <span
                                                            class="font-bold text-gray-400 text-[9px] uppercase tracking-wider"
                                                            >{col.name}</span
                                                        >
                                                        <span
                                                            class="text-[11px] text-gray-700 leading-relaxed whitespace-pre-wrap break-words"
                                                            >{stepDef.values[
                                                                col.id
                                                            ]}</span
                                                        >
                                                    </div>
                                                {/each}
                                            </div>
                                        {/if}

                                        <div class="grid grid-cols-2 gap-2">
                                            <button
                                                class="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-[11px] font-medium border transition-all
                                                {isCapturing
                                                    ? 'bg-blue-50 border-blue-200 text-blue-700 shadow-inner'
                                                    : 'bg-white border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600 hover:shadow-sm'}"
                                                on:click|stopPropagation={() =>
                                                    startCaptureForStep(
                                                        step.id,
                                                    )}
                                            >
                                                <span
                                                    >{isCapturing
                                                        ? "📷"
                                                        : "📷"}</span
                                                >
                                                {isCapturing
                                                    ? "캡처 중..."
                                                    : "영역 캡처"}
                                            </button>

                                            <button
                                                class="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-[11px] font-medium border transition-all
                                                {isAddingAttach
                                                    ? 'bg-amber-50 border-amber-200 text-amber-700 shadow-inner'
                                                    : 'bg-white border-gray-200 text-gray-600 hover:border-amber-300 hover:text-amber-600 hover:shadow-sm'}"
                                                on:click|stopPropagation={() =>
                                                    toggleAttachmentSection(
                                                        step.id,
                                                    )}
                                            >
                                                <span>📎</span>
                                                첨부 추가
                                            </button>
                                        </div>

                                        {#if isAddingAttach}
                                            <div
                                                class="bg-amber-50/50 border border-amber-100 rounded p-1.5"
                                                transition:slide={{
                                                    duration: 150,
                                                }}
                                            >
                                                <div
                                                    class="relative flex items-center"
                                                >
                                                    <input
                                                        type="text"
                                                        bind:value={
                                                            attachmentTextInput
                                                        }
                                                        class="w-full pl-2 pr-8 py-1.5 text-[11px] border border-amber-200 rounded focus:outline-none focus:ring-1 focus:ring-amber-400 bg-white"
                                                        placeholder="내용 입력 또는 이미지 붙여넣기 (Ctrl+V)"
                                                        on:keypress={(e) =>
                                                            e.key === "Enter" &&
                                                            addTextAttachment(
                                                                step.id,
                                                            )}
                                                        on:paste={(e) =>
                                                            handlePaste(
                                                                e,
                                                                step.id,
                                                            )}
                                                        autoFocus
                                                    />
                                                    <button
                                                        class="absolute right-1 px-1.5 py-0.5 text-[10px] font-bold text-amber-600 hover:bg-amber-100 rounded"
                                                        disabled={!attachmentTextInput.trim()}
                                                        on:click={() =>
                                                            addTextAttachment(
                                                                step.id,
                                                            )}
                                                    >
                                                        ↵
                                                    </button>
                                                </div>
                                            </div>
                                        {/if}

                                        {#if step.captures.length > 0 || step.attachments.length > 0}
                                            <div
                                                class="pt-1 border-t border-gray-50 flex flex-col gap-1.5"
                                            >
                                                {#if step.captures.length > 0}
                                                    <div
                                                        class="flex flex-wrap gap-1"
                                                    >
                                                        {#each step.captures as capture (capture.id)}
                                                            <div
                                                                class="group inline-flex items-center gap-1 pl-1.5 pr-1 py-0.5 bg-blue-50/50 border border-blue-100 rounded text-[10px] text-blue-700"
                                                            >
                                                                <span
                                                                    class="opacity-80"
                                                                    >슬라이드 {capture.slideIndex +
                                                                        1}</span
                                                                >
                                                                <button
                                                                    class="p-px hover:bg-blue-200 rounded-full text-blue-400 hover:text-blue-600"
                                                                    on:click={() =>
                                                                        removeCapture(
                                                                            step.id,
                                                                            capture.id,
                                                                        )}
                                                                >
                                                                    <svg
                                                                        class="w-2.5 h-2.5"
                                                                        viewBox="0 0 24 24"
                                                                        fill="none"
                                                                        stroke="currentColor"
                                                                        stroke-width="3"
                                                                        ><path
                                                                            d="M18 6L6 18M6 6l12 12"
                                                                        /></svg
                                                                    >
                                                                </button>
                                                            </div>
                                                        {/each}
                                                    </div>
                                                {/if}

                                                {#if step.attachments.length > 0}
                                                    <div
                                                        class="grid grid-cols-2 gap-1.5"
                                                    >
                                                        {#each step.attachments as attachment (attachment.id)}
                                                            <button
                                                                class="relative group bg-gray-50 rounded border border-gray-100 overflow-hidden flex items-center text-left hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer"
                                                                on:click={() =>
                                                                    openAttachmentModal(
                                                                        step.id,
                                                                        attachment,
                                                                    )}
                                                            >
                                                                {#if attachment.type === "image" && attachment.imageId}
                                                                    <img
                                                                        src={getAttachmentImageUrl(attachment.imageId)}
                                                                        alt="att"
                                                                        class="w-full h-12 object-cover"
                                                                    />
                                                                    <div
                                                                        class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center"
                                                                    >
                                                                        <span
                                                                            class="opacity-0 group-hover:opacity-100 text-white text-[10px] font-medium bg-black/50 px-1.5 py-0.5 rounded transition-opacity"
                                                                        >
                                                                            클릭하여
                                                                            보기
                                                                        </span>
                                                                    </div>
                                                                    {#if attachment.caption}
                                                                        <div
                                                                            class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[9px] px-1 py-0.5 truncate"
                                                                        >
                                                                            {attachment.caption}
                                                                        </div>
                                                                    {/if}
                                                                {:else}
                                                                    <div
                                                                        class="p-1.5 text-[10px] text-gray-600 leading-snug break-words w-full line-clamp-2"
                                                                    >
                                                                        {attachment.data}
                                                                    </div>
                                                                {/if}
                                                            </button>
                                                        {/each}
                                                    </div>
                                                {/if}
                                            </div>
                                        {/if}

                                        <div
                                            class="pt-1 border-t border-gray-50 flex justify-end"
                                        >
                                            <button
                                                class="text-[10px] text-red-300 hover:text-red-500 px-1.5 py-0.5 rounded hover:bg-red-50 transition-colors"
                                                on:click={() =>
                                                    handleRemoveStep(step.id)}
                                            >
                                                삭제
                                            </button>
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/each}

                    {#if workflowData.steps.length === 0}
                        <div
                            class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 pointer-events-none pb-8"
                        >
                            <span class="text-xs opacity-50"
                                >스텝을 추가하세요</span
                            >
                        </div>
                    {/if}

                    <!-- Drop Zone for End of List -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <div
                        class="flex-1 min-h-[50px]"
                        on:dragover={handleContainerDragOver}
                        on:drop={handleContainerDrop}
                    ></div>
                </div>

                <!-- Attachment View/Edit Modal -->
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

                <!-- Image Add Modal (with caption) -->
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

<style>
    /* Custom Scrollbar for popup chips */
    .no-scrollbar::-webkit-scrollbar {
        display: none;
    }
    .no-scrollbar {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }

    /* Step category badge */
    .step-category-badge {
        font-size: 9px;
        white-space: nowrap;
    }

    /* Drag cursor for step items */
    .step-item {
        cursor: grab;
    }

    .step-item:active {
        cursor: grabbing;
    }
</style>
