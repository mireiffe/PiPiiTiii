<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import AttachmentModal from "./workflow/AttachmentModal.svelte";
    import ImageAddModal from "./workflow/ImageAddModal.svelte";
    import StepDefinitionPopup from "./workflow/StepDefinitionPopup.svelte";
    import WorkflowStepItem from "./workflow/WorkflowStepItem.svelte";
    import TimelineGraph from "./workflow/TimelineGraph.svelte";
    import ContainerGraph from "./workflow/ContainerGraph.svelte";
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
        ContainerBranch,
        ContainerColumn,
    } from "$lib/types/workflow";
    import {
        createEmptyWorkflowData,
        createStepInstance,
        createStepCapture,
        createAttachment,
        generateAttachmentId,
        getContainerColumns,
        validateBranchCreation,
        addBranch,
        removeBranch,
        cleanupOrphanedBranches,
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

    // Insert guide state (for long hover insertion)
    let hoverStepId: string | null = null;
    let hoverStartTime: number = 0;
    let insertGuideIndex: number | null = null;
    let insertGuideContainerId: string | null | undefined = null;
    let insertGuidePosition: 'top' | 'bottom' | null = null;
    const INSERT_GUIDE_DELAY = 500; // ms to wait before showing insert guide
    let hoverCheckTimer: ReturnType<typeof setTimeout> | null = null;

    // Branch creation state (for multi-column flow)
    let branchHoverStepId: string | null = null;  // Step being hovered for branch creation
    let branchHoverSide: 'left' | 'right' | null = null;  // Which side of the step
    let branchHoverStartTime: number = 0;
    let branchGuideVisible = false;  // Show the branch creation guide
    let branchGuideTargetStepId: string | null = null;  // Target step for branch placement
    let branchHoverTimer: ReturnType<typeof setTimeout> | null = null;
    const BRANCH_GUIDE_DELAY = 600; // ms to wait before showing branch guide (slightly longer)

    // Multi-selection state
    let selectedStepIds: Set<string> = new Set();
    let lastClickedStepId: string | null = null;
    let showMoveToContainerDropdown = false;
    let moveDropdownPosition = { top: 0, left: 0 };
    let selectionModeActive = false;  // 체크박스 표시 여부

    // Selection helpers
    // 체크박스 직접 클릭: 항상 토글 (중복 선택)
    function handleCheckboxClick(stepId: string, event: MouseEvent) {
        event.stopPropagation();

        if (selectedStepIds.has(stepId)) {
            selectedStepIds.delete(stepId);
        } else {
            selectedStepIds.add(stepId);
        }
        selectedStepIds = selectedStepIds;
        lastClickedStepId = stepId;

        // 선택이 모두 해제되면 선택 모드 종료
        if (selectedStepIds.size === 0) {
            selectionModeActive = false;
        }
    }

    // 카드 본문 클릭 처리 (Ctrl 키 여부에 따라 다르게 동작)
    function handleCardCtrlClick(stepId: string, event: MouseEvent) {
        if (event.ctrlKey || event.metaKey) {
            event.stopPropagation();
            event.preventDefault();

            // 선택 모드 활성화
            selectionModeActive = true;

            // Shift+Ctrl: 범위 선택
            if (event.shiftKey && lastClickedStepId) {
                const stepIds = workflowData.steps.map(s => s.id);
                const lastIndex = stepIds.indexOf(lastClickedStepId);
                const currentIndex = stepIds.indexOf(stepId);

                if (lastIndex !== -1 && currentIndex !== -1) {
                    const start = Math.min(lastIndex, currentIndex);
                    const end = Math.max(lastIndex, currentIndex);

                    for (let i = start; i <= end; i++) {
                        selectedStepIds.add(stepIds[i]);
                    }
                    selectedStepIds = selectedStepIds;
                }
            } else {
                // Ctrl 클릭: 토글 선택
                if (selectedStepIds.has(stepId)) {
                    selectedStepIds.delete(stepId);
                } else {
                    selectedStepIds.add(stepId);
                }
                selectedStepIds = selectedStepIds;
                lastClickedStepId = stepId;
            }

            // 선택이 모두 해제되면 선택 모드 종료
            if (selectedStepIds.size === 0) {
                selectionModeActive = false;
            }

            return true; // handled
        }

        // 선택 모드에서 일반 클릭: 단일 선택
        if (selectionModeActive) {
            event.stopPropagation();
            event.preventDefault();

            selectedStepIds = new Set([stepId]);
            lastClickedStepId = stepId;

            return true; // handled
        }

        return false; // not handled, let normal expand happen
    }

    function clearSelection() {
        selectedStepIds.clear();
        selectedStepIds = selectedStepIds;
        lastClickedStepId = null;
        showMoveToContainerDropdown = false;
        selectionModeActive = false;
    }

    function selectAll() {
        workflowData.steps.forEach(step => selectedStepIds.add(step.id));
        selectedStepIds = selectedStepIds;
    }

    function openMoveDropdown(event: MouseEvent) {
        const button = event.currentTarget as HTMLElement;
        const rect = button.getBoundingClientRect();
        moveDropdownPosition = {
            top: rect.bottom + 4,
            left: rect.left
        };
        showMoveToContainerDropdown = true;
    }

    function moveSelectedToContainer(targetContainerId: string | null) {
        if (selectedStepIds.size === 0) return;

        const steps = [...workflowData.steps];

        // Update containerId for all selected steps
        steps.forEach((step, index) => {
            if (selectedStepIds.has(step.id)) {
                steps[index] = {
                    ...step,
                    containerId: targetContainerId || undefined
                };
            }
        });

        workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);

        clearSelection();
    }

    // Close dropdown when clicking outside
    function handleDropdownClickOutside(event: MouseEvent) {
        if (showMoveToContainerDropdown) {
            const target = event.target as HTMLElement;
            if (!target.closest('.move-dropdown')) {
                showMoveToContainerDropdown = false;
            }
        }
    }

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
        clearInsertGuide();
    }

    function clearInsertGuide() {
        if (hoverCheckTimer) {
            clearTimeout(hoverCheckTimer);
            hoverCheckTimer = null;
        }
        hoverStepId = null;
        hoverStartTime = 0;
        insertGuideIndex = null;
        insertGuideContainerId = null;
        insertGuidePosition = null;
    }

    // Branch creation handlers
    function clearBranchGuide() {
        if (branchHoverTimer) {
            clearTimeout(branchHoverTimer);
            branchHoverTimer = null;
        }
        branchHoverStepId = null;
        branchHoverSide = null;
        branchHoverStartTime = 0;
        branchGuideVisible = false;
        branchGuideTargetStepId = null;
    }

    function handleStepHoverForBranch(e: DragEvent, targetStepId: string, targetContainerId: string | undefined) {
        if (dragState.draggedIndex === null) return;

        const draggedStep = workflowData.steps[dragState.draggedIndex];
        const draggedContainerId = draggedStep.containerId ?? '__uncategorized__';
        const targetContainerKey = targetContainerId ?? '__uncategorized__';

        // Only allow branch creation within the same container
        if (draggedContainerId !== targetContainerKey) {
            clearBranchGuide();
            return;
        }

        const target = e.currentTarget as HTMLElement;
        const rect = target.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const isRightSide = offsetX > rect.width * 0.7;  // Right 30% of the card

        // Only show branch guide when hovering on right side
        if (!isRightSide) {
            clearBranchGuide();
            return;
        }

        // Validate: dragged step must come AFTER target step (left-to-right order)
        const validationError = validateBranchCreation(
            draggedStep.id,
            targetStepId,
            targetContainerId,
            workflowData.steps
        );

        if (validationError) {
            clearBranchGuide();
            return;
        }

        // If already hovering this step on right side, check if timer should fire
        if (branchHoverStepId === targetStepId && branchHoverSide === 'right') {
            return;  // Timer already running
        }

        // Start new hover
        clearBranchGuide();
        branchHoverStepId = targetStepId;
        branchHoverSide = 'right';
        branchHoverStartTime = Date.now();

        branchHoverTimer = setTimeout(() => {
            // Show branch guide with bounce animation
            branchGuideVisible = true;
            branchGuideTargetStepId = targetStepId;
        }, BRANCH_GUIDE_DELAY);
    }

    function handleBranchDrop(e: DragEvent, targetStepId: string, targetContainerId: string | undefined) {
        e.preventDefault();
        e.stopPropagation();

        if (dragState.draggedIndex === null || !branchGuideVisible) {
            clearBranchGuide();
            return;
        }

        const draggedStep = workflowData.steps[dragState.draggedIndex];

        // Create the branch
        const validationError = validateBranchCreation(
            draggedStep.id,
            targetStepId,
            targetContainerId,
            workflowData.steps
        );

        if (validationError) {
            alert(validationError);
            clearBranchGuide();
            dragState = { draggedIndex: null, dropTargetIndex: null };
            return;
        }

        // Add branch
        workflowData = addBranch(workflowData, targetContainerId, draggedStep.id, targetStepId);
        dispatch("workflowChange", workflowData);

        // Reset state
        clearBranchGuide();
        dragState = { draggedIndex: null, dropTargetIndex: null };
        dropTargetContainerId = null;
    }

    function handleRemoveBranch(containerId: string | undefined, branchId: string) {
        workflowData = removeBranch(workflowData, containerId, branchId);
        dispatch("workflowChange", workflowData);
    }

    function handleStepHoverForInsert(e: DragEvent, stepId: string, stepIndex: number, stepContainerId: string | undefined) {
        // Only track hover for cross-container drags
        if (dragState.draggedIndex === null) return;
        const draggedStep = workflowData.steps[dragState.draggedIndex];
        const isCrossContainer = (draggedStep.containerId ?? null) !== (stepContainerId ?? null);
        if (!isCrossContainer) {
            clearInsertGuide();
            return;
        }

        const target = e.currentTarget as HTMLElement;
        const rect = target.getBoundingClientRect();
        const offsetY = e.clientY - rect.top;
        const isTopHalf = offsetY < rect.height / 2;
        const position = isTopHalf ? 'top' : 'bottom';

        // If hovering a different step or position, reset timer
        if (hoverStepId !== stepId || insertGuidePosition !== position) {
            clearInsertGuide();
            hoverStepId = stepId;
            hoverStartTime = Date.now();
            insertGuidePosition = position;

            hoverCheckTimer = setTimeout(() => {
                // Show insert guide after delay
                insertGuideIndex = position === 'top' ? stepIndex : stepIndex + 1;
                insertGuideContainerId = stepContainerId;
            }, INSERT_GUIDE_DELAY);
        }
    }

    function handleContainerDrop(e: DragEvent, containerId: string | null) {
        e.preventDefault();
        if (dragState.draggedIndex === null) return;

        const draggedStep = workflowData.steps[dragState.draggedIndex];
        const sourceContainerId = draggedStep.containerId ?? null;

        // Same container - no action
        if (sourceContainerId === containerId) {
            dragState = { draggedIndex: null, dropTargetIndex: null };
            dropTargetContainerId = null;
            clearInsertGuide();
            return;
        }

        // Check if insert guide is active - use specific position
        if (insertGuideIndex !== null && insertGuideContainerId === (containerId ?? undefined)) {
            const steps = [...workflowData.steps];
            const [removed] = steps.splice(dragState.draggedIndex, 1);

            let adjustedIndex = insertGuideIndex;
            if (dragState.draggedIndex < insertGuideIndex) {
                adjustedIndex -= 1;
            }

            removed.containerId = containerId || undefined;
            steps.splice(adjustedIndex, 0, removed);

            workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
            dispatch("workflowChange", workflowData);

            dragState = { draggedIndex: null, dropTargetIndex: null };
            dropTargetContainerId = null;
            clearInsertGuide();
            return;
        }

        // Default behavior: position based on container order
        // Get container orders (uncategorized = -1)
        const sourceOrder = sourceContainerId
            ? sortedContainers.find(c => c.id === sourceContainerId)?.order ?? -1
            : -1;
        const targetOrder = containerId
            ? sortedContainers.find(c => c.id === containerId)?.order ?? -1
            : -1;

        // Calculate target position based on container order
        let newIndex: number;
        if (targetOrder > sourceOrder) {
            // Moving to higher order container -> first position of that container
            const targetContainerSteps = containerId
                ? workflowData.steps.filter(s => s.containerId === containerId)
                : workflowData.steps.filter(s => !s.containerId);

            if (targetContainerSteps.length > 0) {
                // Insert before the first step of target container
                newIndex = workflowData.steps.findIndex(s => s.id === targetContainerSteps[0].id);
            } else {
                // Empty container - find insertion point based on container order
                // Find first step from a higher-order container
                const higherContainerIds = sortedContainers
                    .filter(c => c.order > targetOrder)
                    .map(c => c.id);
                const nextStep = workflowData.steps.find(s =>
                    s.containerId && higherContainerIds.includes(s.containerId)
                );
                newIndex = nextStep
                    ? workflowData.steps.findIndex(s => s.id === nextStep.id)
                    : workflowData.steps.length;
            }
        } else {
            // Moving to lower order container -> last position of that container
            const targetContainerSteps = containerId
                ? workflowData.steps.filter(s => s.containerId === containerId)
                : workflowData.steps.filter(s => !s.containerId);

            if (targetContainerSteps.length > 0) {
                // Insert after the last step of target container
                const lastStep = targetContainerSteps[targetContainerSteps.length - 1];
                newIndex = workflowData.steps.findIndex(s => s.id === lastStep.id) + 1;
            } else {
                // Empty container - find insertion point
                // Find first step from a higher-order container than target
                const higherContainerIds = sortedContainers
                    .filter(c => c.order > targetOrder)
                    .map(c => c.id);
                const nextStep = workflowData.steps.find(s =>
                    s.containerId && higherContainerIds.includes(s.containerId)
                );
                newIndex = nextStep
                    ? workflowData.steps.findIndex(s => s.id === nextStep.id)
                    : workflowData.steps.length;
            }
        }

        // Build new steps array
        const steps = [...workflowData.steps];
        const [removed] = steps.splice(dragState.draggedIndex, 1);

        // Adjust target index if needed after removal
        let adjustedIndex = newIndex;
        if (dragState.draggedIndex < newIndex) {
            adjustedIndex -= 1;
        }

        // Update container and insert at new position
        removed.containerId = containerId || undefined;
        steps.splice(adjustedIndex, 0, removed);

        workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);

        dragState = { draggedIndex: null, dropTargetIndex: null };
        dropTargetContainerId = null;
        clearInsertGuide();
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

    // Calculate columns for each container (for multi-column branch layout)
    $: containerColumnsMap = (() => {
        const map: Record<string, ContainerColumn[]> = {};

        // Uncategorized
        map['__uncategorized__'] = getContainerColumns(
            undefined,
            workflowData.steps,
            workflowData.containerBranches
        );

        // Named containers
        sortedContainers.forEach(container => {
            map[container.id] = getContainerColumns(
                container.id,
                workflowData.steps,
                workflowData.containerBranches
            );
        });

        return map;
    })();

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
    onDestroy(() => {
        window.removeEventListener("keydown", handleKeyDown);
        if (hoverCheckTimer) clearTimeout(hoverCheckTimer);
        if (branchHoverTimer) clearTimeout(branchHoverTimer);
    });

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
            let updatedWorkflow = {
                ...workflowData,
                steps: workflowData.steps.filter((s) => s.id !== stepId),
                updatedAt: new Date().toISOString(),
            };
            // Clean up any orphaned branches
            updatedWorkflow = cleanupOrphanedBranches(updatedWorkflow);
            workflowData = updatedWorkflow;
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

<svelte:window on:click={handleClickOutside} on:click={handleDropdownClickOutside} />

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
                <ContainerGraph
                    {workflowData}
                    {workflowSteps}
                    {stepContainers}
                />
            {:else}
                <!-- Selection Toolbar (shown when items are selected) -->
                {#if selectedStepIds.size > 0}
                    <div class="px-3 py-2 bg-blue-50 border-b border-blue-200 flex items-center gap-2 flex-wrap">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-medium text-blue-700">
                                {selectedStepIds.size}개 선택됨
                            </span>
                            <button
                                class="text-xs text-blue-500 hover:text-blue-700 underline"
                                on:click={selectAll}
                            >
                                전체 선택
                            </button>
                            <button
                                class="text-xs text-gray-500 hover:text-gray-700 underline"
                                on:click={clearSelection}
                            >
                                선택 해제
                            </button>
                        </div>
                        <div class="flex-1"></div>
                        {#if sortedContainers.length > 0}
                            <div class="relative move-dropdown">
                                <button
                                    class="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors shadow-sm"
                                    on:click={openMoveDropdown}
                                >
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                                    </svg>
                                    Container로 이동
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </button>

                                {#if showMoveToContainerDropdown}
                                    <div
                                        class="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[180px] z-50 max-h-[300px] overflow-y-auto"
                                    >
                                        <button
                                            class="w-full px-3 py-2 text-left text-xs hover:bg-gray-100 flex items-center gap-2"
                                            on:click={() => moveSelectedToContainer(null)}
                                        >
                                            <span class="w-2 h-2 rounded-full bg-gray-400"></span>
                                            미분류
                                        </button>
                                        <div class="border-t border-gray-100 my-1"></div>
                                        {#each sortedContainers as container}
                                            <button
                                                class="w-full px-3 py-2 text-left text-xs hover:bg-blue-50 flex items-center gap-2"
                                                on:click={() => moveSelectedToContainer(container.id)}
                                            >
                                                <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                                                {container.name}
                                            </button>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}

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

                        <!-- Uncategorized Steps (only shown when there are uncategorized items) -->
                        {#if uncategorizedSteps.length > 0}
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
                                    <div class="absolute left-[23px] top-2 bottom-2 w-px bg-gray-200 z-0"></div>
                                    {#each uncategorizedSteps as step, localIndex (step.id)}
                                        {@const index = workflowData.steps.findIndex(s => s.id === step.id)}
                                        {@const stepDef = getStepDefinition(step.stepId)}
                                        {@const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}
                                        {@const showInsertGuideTop = insertGuideIndex === index && insertGuideContainerId === undefined && localIndex === 0}
                                        {@const showInsertGuideBottom = insertGuideIndex === index + 1 && insertGuideContainerId === undefined}

                                        <!-- Insert guide indicator (top) -->
                                        {#if showInsertGuideTop}
                                            <div class="relative h-1 -mt-1 mb-1">
                                                <div class="absolute inset-x-0 h-1 bg-green-500 rounded-full animate-pulse shadow-sm shadow-green-300"></div>
                                            </div>
                                        {/if}

                                        <div
                                            draggable="true"
                                            on:dragstart={(e) => dragDropHandlers.handleDragStart(e, index)}
                                            on:dragend={() => { dragDropHandlers.handleDragEnd(); dropTargetContainerId = null; clearInsertGuide(); }}
                                            on:drop={(e) => handleStepDropWithContainer(e, undefined)}
                                            on:dragover={(e) => { dragDropHandlers.handleDragOver(e, index); handleStepHoverForInsert(e, step.id, index, undefined); }}
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
                                                isSelected={selectedStepIds.has(step.id)}
                                                showSelectionCheckbox={selectionModeActive}
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
                                                on:checkboxClick={(e) => handleCheckboxClick(step.id, e.detail)}
                                                on:cardClick={(e) => handleCardCtrlClick(step.id, e.detail)}
                                            />
                                        </div>

                                        <!-- Insert guide indicator (bottom) -->
                                        {#if showInsertGuideBottom}
                                            <div class="relative h-1 mt-1 -mb-1">
                                                <div class="absolute inset-x-0 h-1 bg-green-500 rounded-full animate-pulse shadow-sm shadow-green-300"></div>
                                            </div>
                                        {/if}
                                    {/each}
                                </div>
                            </div>
                        {/if}

                        <!-- Container Groups -->
                        {#each sortedContainers as container (container.id)}
                            {@const containerSteps = stepsByContainerId[container.id] || []}
                            {@const columns = containerColumnsMap[container.id] || []}
                            {@const hasMultipleColumns = columns.length > 1}
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
                                    {#if hasMultipleColumns}
                                        <span class="ml-1 px-1.5 py-0.5 bg-purple-100 text-purple-600 text-[10px] font-medium rounded">
                                            {columns.length} branches
                                        </span>
                                    {/if}
                                </button>
                                {#if !isCollapsed}
                                    <div class="p-2 min-h-[40px]">
                                        {#if hasMultipleColumns}
                                            <!-- Multi-column layout -->
                                            <div class="flex gap-2">
                                                {#each columns as column, colIdx (column.columnIndex)}
                                                    <div class="flex-1 min-w-0 relative">
                                                        <!-- Column header with branch info -->
                                                        {#if colIdx > 0 && column.branchInfo}
                                                            <div class="mb-2 flex items-center justify-between">
                                                                <span class="text-[10px] font-medium text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">
                                                                    분기 {colIdx}
                                                                </span>
                                                                <button
                                                                    class="text-gray-400 hover:text-red-500 p-0.5 rounded transition-colors"
                                                                    title="분기 해제"
                                                                    on:click={() => handleRemoveBranch(container.id, column.branchInfo?.id ?? '')}
                                                                >
                                                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                                    </svg>
                                                                </button>
                                                            </div>
                                                        {/if}
                                                        <!-- Vertical connection line -->
                                                        {#if column.steps.length > 0}
                                                            <div class="absolute left-[23px] top-6 bottom-2 w-px bg-blue-200 z-0"></div>
                                                        {/if}
                                                        <!-- Steps in column -->
                                                        <div class="space-y-2">
                                                            {#each column.steps as step, localIndex (step.id)}
                                                                {@const index = workflowData.steps.findIndex(s => s.id === step.id)}
                                                                {@const stepDef = getStepDefinition(step.stepId)}
                                                                {@const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}
                                                                {@const showBranchGuide = branchGuideVisible && branchGuideTargetStepId === step.id}

                                                                <div class="relative">
                                                                    <!-- Branch creation guide (bounce animation) -->
                                                                    {#if showBranchGuide}
                                                                        <div class="absolute -right-1 top-1/2 -translate-y-1/2 z-20 pointer-events-none">
                                                                            <div class="branch-guide-indicator">
                                                                                <div class="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center shadow-lg animate-bounce-right">
                                                                                    <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M9 5l7 7-7 7" />
                                                                                    </svg>
                                                                                </div>
                                                                                <span class="absolute left-full ml-1 top-1/2 -translate-y-1/2 whitespace-nowrap text-[10px] font-medium text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded shadow">
                                                                                    여기 배치
                                                                                </span>
                                                                            </div>
                                                                        </div>
                                                                    {/if}

                                                                    <div
                                                                        draggable="true"
                                                                        on:dragstart={(e) => dragDropHandlers.handleDragStart(e, index)}
                                                                        on:dragend={() => { dragDropHandlers.handleDragEnd(); dropTargetContainerId = null; clearInsertGuide(); clearBranchGuide(); }}
                                                                        on:drop={(e) => {
                                                                            if (branchGuideVisible && branchGuideTargetStepId === step.id) {
                                                                                handleBranchDrop(e, step.id, container.id);
                                                                            } else {
                                                                                handleStepDropWithContainer(e, container.id);
                                                                            }
                                                                        }}
                                                                        on:dragover={(e) => {
                                                                            dragDropHandlers.handleDragOver(e, index);
                                                                            handleStepHoverForInsert(e, step.id, index, container.id);
                                                                            handleStepHoverForBranch(e, step.id, container.id);
                                                                        }}
                                                                        on:dragleave={() => clearBranchGuide()}
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
                                                                            isSelected={selectedStepIds.has(step.id)}
                                                                            showSelectionCheckbox={selectionModeActive}
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
                                                                            on:checkboxClick={(e) => handleCheckboxClick(step.id, e.detail)}
                                                                            on:cardClick={(e) => handleCardCtrlClick(step.id, e.detail)}
                                                                        />
                                                                    </div>
                                                                </div>
                                                            {/each}
                                                        </div>
                                                    </div>
                                                {/each}
                                            </div>
                                        {:else}
                                            <!-- Single column layout (original) -->
                                            <div class="space-y-2 relative">
                                                {#if containerSteps.length > 0}
                                                    <div class="absolute left-[23px] top-2 bottom-2 w-px bg-blue-200 z-0"></div>
                                                {/if}
                                                {#each containerSteps as step, localIndex (step.id)}
                                                    {@const index = workflowData.steps.findIndex(s => s.id === step.id)}
                                                    {@const stepDef = getStepDefinition(step.stepId)}
                                                    {@const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}
                                                    {@const showInsertGuideTop = insertGuideIndex === index && insertGuideContainerId === container.id && localIndex === 0}
                                                    {@const showInsertGuideBottom = insertGuideIndex === index + 1 && insertGuideContainerId === container.id}
                                                    {@const showBranchGuide = branchGuideVisible && branchGuideTargetStepId === step.id}

                                                    <!-- Insert guide indicator (top) -->
                                                    {#if showInsertGuideTop}
                                                        <div class="relative h-1 -mt-1 mb-1">
                                                            <div class="absolute inset-x-0 h-1 bg-green-500 rounded-full animate-pulse shadow-sm shadow-green-300"></div>
                                                        </div>
                                                    {/if}

                                                    <div class="relative">
                                                        <!-- Branch creation guide (bounce animation) -->
                                                        {#if showBranchGuide}
                                                            <div class="absolute -right-1 top-1/2 -translate-y-1/2 z-20 pointer-events-none">
                                                                <div class="branch-guide-indicator">
                                                                    <div class="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center shadow-lg animate-bounce-right">
                                                                        <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M9 5l7 7-7 7" />
                                                                        </svg>
                                                                    </div>
                                                                    <span class="absolute left-full ml-1 top-1/2 -translate-y-1/2 whitespace-nowrap text-[10px] font-medium text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded shadow">
                                                                        여기에 분기 생성
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        {/if}

                                                        <div
                                                            draggable="true"
                                                            on:dragstart={(e) => dragDropHandlers.handleDragStart(e, index)}
                                                            on:dragend={() => { dragDropHandlers.handleDragEnd(); dropTargetContainerId = null; clearInsertGuide(); clearBranchGuide(); }}
                                                            on:drop={(e) => {
                                                                if (branchGuideVisible && branchGuideTargetStepId === step.id) {
                                                                    handleBranchDrop(e, step.id, container.id);
                                                                } else {
                                                                    handleStepDropWithContainer(e, container.id);
                                                                }
                                                            }}
                                                            on:dragover={(e) => {
                                                                dragDropHandlers.handleDragOver(e, index);
                                                                handleStepHoverForInsert(e, step.id, index, container.id);
                                                                handleStepHoverForBranch(e, step.id, container.id);
                                                            }}
                                                            on:dragleave={() => clearBranchGuide()}
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
                                                                isSelected={selectedStepIds.has(step.id)}
                                                                showSelectionCheckbox={selectionModeActive}
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
                                                                on:checkboxClick={(e) => handleCheckboxClick(step.id, e.detail)}
                                                                on:cardClick={(e) => handleCardCtrlClick(step.id, e.detail)}
                                                            />
                                                        </div>
                                                    </div>

                                                    <!-- Insert guide indicator (bottom) -->
                                                    {#if showInsertGuideBottom}
                                                        <div class="relative h-1 mt-1 -mb-1">
                                                            <div class="absolute inset-x-0 h-1 bg-green-500 rounded-full animate-pulse shadow-sm shadow-green-300"></div>
                                                        </div>
                                                    {/if}
                                                {/each}
                                            </div>
                                        {/if}
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

<style>
    /* Branch guide bounce animation - bounces horizontally to the right */
    :global(.animate-bounce-right) {
        animation: bounce-right 0.6s ease-in-out infinite;
    }

    @keyframes bounce-right {
        0%, 100% {
            transform: translateX(0);
        }
        50% {
            transform: translateX(4px);
        }
    }

    /* Branch guide indicator container */
    .branch-guide-indicator {
        display: flex;
        align-items: center;
    }
</style>
