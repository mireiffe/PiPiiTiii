<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import AttachmentModal from "./workflow/AttachmentModal.svelte";
    import ImageAddModal from "./workflow/ImageAddModal.svelte";
    import StepDefinitionPopup from "./workflow/StepDefinitionPopup.svelte";
    import WorkflowStepItem from "./workflow/WorkflowStepItem.svelte";
    import D3WorkflowGraph from "./workflow/D3WorkflowGraph.svelte";
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
        PhaseType,
        CoreStepsSettings,
        CoreStepDefinition,
        CoreStepInstance,
        UnifiedStepItem,
        KeyStepLink,
        KeyStepLinkingData,
    } from "$lib/types/workflow";
    import {
        createEmptyWorkflowData,
        createStepInstance,
        createStepCapture,
        createAttachment,
        generateAttachmentId,
        getLayoutRows,
        validateSupportCreation,
        addSupportRelation,
        removeSupportByStepId,
        cleanupOrphanedSupports,
        createCoreStepInstance,
        // Unified step system
        checkCoreStepCompletion,
        validateReorder,
        validateDeletion,
        createUnifiedCoreStep,
        createUnifiedRegularStep,
        syncUnifiedToLegacy,
        // Key step linking
        checkKeyStepLinkingComplete,
        saveKeyStepLinks,
        confirmWorkflow,
        unconfirmWorkflow,
    } from "$lib/types/workflow";
    import CoreStepItem from "./workflow/CoreStepItem.svelte";
    import KeyStepLinkingWizard from "./workflow/KeyStepLinkingWizard.svelte";
    import { toastStore } from "$lib/stores/toast";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";
    import {
        uploadAttachmentImage,
        deleteAttachmentImage,
        getAttachmentImageUrl,
    } from "$lib/api/project";

    export let isExpanded = false;
    export let projectId: string = "";
    export let workflowData: ProjectWorkflowData = createEmptyWorkflowData();
    export let workflowSteps: WorkflowSteps = { columns: [], rows: [] };
    export let globalPhases: PhaseType[] = []; // Global phases from settings
    export let coreStepsSettings: CoreStepsSettings = { definitions: [] }; // Core step definitions from settings
    export let savingWorkflow = false;
    export let captureMode = false;
    export let captureTargetStepId: string | null = null;
    export let workflowName: string = "Workflow"; // Name of current workflow for overlay labels
    export let workflows: { id: string; name: string }[] = []; // Available workflows
    export let activeWorkflowId: string | null = null; // Currently selected workflow
    export let allWorkflowsData: Record<string, any> = {}; // All workflows data for this project
    export let slideWidth: number = 960; // Original slide width for capture preview
    export let slideHeight: number = 540; // Original slide height for capture preview

    const dispatch = createEventDispatcher();

    // Find undefined workflows (exist in allWorkflowsData but not in workflows definitions)
    $: undefinedWorkflowIds = Object.keys(allWorkflowsData).filter(
        (wfId) => !workflows.some((w) => w.id === wfId),
    );

    // Check if current active workflow is undefined
    $: isUndefinedWorkflow =
        activeWorkflowId !== null &&
        undefinedWorkflowIds.includes(activeWorkflowId);

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

    // Drag & Drop State - Unified mode system
    // Only one drag mode is active at a time to avoid UI conflicts
    type DragMode = "reorder" | "support" | null;
    let dragMode: DragMode = null;
    let dragState: DragDropState = {
        draggedIndex: null,
        dropTargetIndex: null,
    };

    // Support/Phase creation state
    let supportGuideTargetStepId: string | null = null; // Target step for support placement
    let supportHoverTimer: ReturnType<typeof setTimeout> | null = null;
    const SUPPORT_GUIDE_DELAY = 300; // ms to wait before showing support guide (0.3 seconds)

    // Phase selection modal state
    let showPhaseSelectModal = false;
    let pendingSupport: {
        supporterStepId: string;
        targetStepId: string;
    } | null = null;

    // Phase list popup state
    let showPhaseListPopup = false;
    let phaseListPopupRef: HTMLDivElement | null = null;

    // Core Step state
    let showCoreStepSelector = false;
    let expandedCoreStepId: string | null = null;
    let capturingForCoreStepPresetId: string | null = null;

    // Core Step Drag & Drop state
    let coreStepDraggedIdx: number | null = null;
    let coreStepDropTargetIdx: number | null = null;

    // Core Step Image Modal State
    let showCoreStepImageModal = false;
    let coreStepImagePresetId: string | null = null;
    let coreStepImageInstanceId: string | null = null;
    let coreStepPendingImageData: string | null = null;
    let coreStepImageCaption = "";
    let coreStepImageIsEditing = false; // true if editing existing image caption
    let coreStepImageIsUploading = false;
    let coreStepItemRefs: Record<string, any> = {}; // Reference to CoreStepItem components

    // ========== Workflow Confirmation & Key Step Linking ==========
    let showKeyStepLinkingWizard = false;

    // Get Core Steps that require key step linking
    $: coreStepsRequiringLinking = (workflowData.unifiedSteps ?? [])
        .filter((s) => s.type === "core")
        .filter((s) => {
            const def = coreStepsSettings.definitions.find(
                (d) => d.id === s.coreStepId,
            );
            return def?.requiresKeyStepLinking;
        })
        .sort((a, b) => a.order - b.order);

    // Check workflow confirmation status
    $: isWorkflowConfirmed = workflowData.isConfirmed ?? false;

    // Check if we can show the confirm button
    $: canConfirmWorkflow =
        allCoreStepsAdded &&
        sortedUnifiedSteps.length > 0 &&
        !isWorkflowConfirmed;

    // ========== Unified Step System ==========
    // Check if all Core Steps have been added
    $: coreStepStatus = checkCoreStepCompletion(
        workflowData.unifiedSteps ?? [],
        coreStepsSettings.definitions,
    );
    $: allCoreStepsAdded =
        coreStepsSettings.definitions.length === 0 || coreStepStatus.isComplete;

    // Get unified steps sorted by order
    $: sortedUnifiedSteps = [...(workflowData.unifiedSteps ?? [])].sort(
        (a, b) => a.order - b.order,
    );

    // Count of regular steps (for display when hidden)
    $: regularStepCount = sortedUnifiedSteps.filter(
        (s) => s.type === "regular",
    ).length;

    // Unified drag & drop state
    let unifiedDraggedIdx: number | null = null;
    let unifiedDropTargetIdx: number | null = null;

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
        item: UnifiedStepItem,
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

    // Multi-selection state
    let selectedStepIds: Set<string> = new Set();
    let lastClickedStepId: string | null = null;
    let selectionModeActive = false; // 체크박스 표시 여부

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
                const stepIds = workflowData.steps.map((s) => s.id);
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
        selectionModeActive = false;
    }

    function selectAll() {
        workflowData.steps.forEach((step) => selectedStepIds.add(step.id));
        selectedStepIds = selectedStepIds;
    }

    const dragDropHandlers = createDragDropHandlers(
        () => dragState,
        (newState) => (dragState = { ...dragState, ...newState }),
        (fromIndex, toIndex) => {
            const steps = [...workflowData.steps];
            const [removed] = steps.splice(fromIndex, 1);
            steps.splice(toIndex, 0, removed);
            workflowData = {
                ...workflowData,
                steps,
                updatedAt: new Date().toISOString(),
            };
            dispatch("workflowChange", workflowData);
        },
        () => captureMode && exitCaptureMode(),
    );

    // Clear all drag guides and reset mode
    function clearAllDragGuides() {
        // Clear support guide
        if (supportHoverTimer) {
            clearTimeout(supportHoverTimer);
            supportHoverTimer = null;
        }
        supportGuideTargetStepId = null;

        // Reset mode
        dragMode = null;
    }

    function clearSupportGuide() {
        if (supportHoverTimer) {
            clearTimeout(supportHoverTimer);
            supportHoverTimer = null;
        }
        supportGuideTargetStepId = null;
        if (dragMode === "support") {
            dragMode = null;
        }
    }

    // Handle dragleave - only clear if actually leaving the element (not moving to child)
    function handleDragLeave(e: DragEvent, stepId: string) {
        const currentTarget = e.currentTarget as HTMLElement;
        const relatedTarget = e.relatedTarget as Node | null;

        // If moving to a child element, don't clear
        if (relatedTarget && currentTarget.contains(relatedTarget)) {
            return;
        }

        // Only clear if this was the target step
        if (supportGuideTargetStepId === stepId) {
            clearSupportGuide();
        }
    }

    function handleStepHoverForSupport(
        e: DragEvent,
        targetStepId: string,
        forceImmediate: boolean = false,
    ) {
        if (dragState.draggedIndex === null) return;

        const draggedStep = workflowData.steps[dragState.draggedIndex];

        // Can't support yourself
        if (draggedStep.id === targetStepId) {
            if (dragMode === "support") clearSupportGuide();
            return;
        }

        // If already in support mode for this step, keep it active
        if (
            dragMode === "support" &&
            supportGuideTargetStepId === targetStepId
        ) {
            return; // Already active, maintain it
        }

        // Validate support creation
        const validationError = validateSupportCreation(
            draggedStep.id,
            targetStepId,
            workflowData.steps,
            workflowData.supportRelations,
        );

        if (validationError) {
            if (dragMode === "support") clearSupportGuide();
            return;
        }

        // If forceImmediate (Shift+drag), activate support mode immediately
        if (forceImmediate) {
            if (supportHoverTimer) {
                clearTimeout(supportHoverTimer);
                supportHoverTimer = null;
            }
            dragMode = "support";
            supportGuideTargetStepId = targetStepId;
            return;
        }

        // If already targeting this step, skip
        if (supportGuideTargetStepId === targetStepId && supportHoverTimer) {
            return; // Timer already running
        }

        // Clear previous timer and start new one
        if (supportHoverTimer) {
            clearTimeout(supportHoverTimer);
            supportHoverTimer = null;
        }

        supportHoverTimer = setTimeout(() => {
            dragMode = "support";
            supportGuideTargetStepId = targetStepId;
        }, SUPPORT_GUIDE_DELAY);
    }

    function handleSupportDrop(e: DragEvent, targetStepId: string) {
        e.preventDefault();
        e.stopPropagation();

        if (
            dragState.draggedIndex === null ||
            dragMode !== "support" ||
            !supportGuideTargetStepId
        ) {
            clearAllDragGuides();
            dragState = { draggedIndex: null, dropTargetIndex: null };
            return;
        }

        const draggedStep = workflowData.steps[dragState.draggedIndex];

        // Validate support creation
        const validationError = validateSupportCreation(
            draggedStep.id,
            targetStepId,
            workflowData.steps,
            workflowData.supportRelations,
        );

        if (validationError) {
            alert(validationError);
            clearAllDragGuides();
            dragState = { draggedIndex: null, dropTargetIndex: null };
            return;
        }

        // Check if there are global phases defined (from settings)
        if (globalPhases.length === 0) {
            // No phases: prompt user to add phases in settings
            alert(
                "먼저 설정에서 위상을 추가해주세요. 메인 메뉴 > 설정 > 위상 (Phase)에서 추가할 수 있습니다.",
            );
            clearAllDragGuides();
            dragState = { draggedIndex: null, dropTargetIndex: null };
            return;
        } else if (globalPhases.length === 1) {
            // Only one phase: auto-select
            workflowData = addSupportRelation(
                workflowData,
                draggedStep.id,
                targetStepId,
                globalPhases[0].id,
            );
            dispatch("workflowChange", workflowData);
            clearAllDragGuides();
            dragState = { draggedIndex: null, dropTargetIndex: null };
        } else {
            // Multiple phases: show selection modal
            pendingSupport = { supporterStepId: draggedStep.id, targetStepId };
            showPhaseSelectModal = true;
            clearAllDragGuides();
            dragState = { draggedIndex: null, dropTargetIndex: null };
        }
    }

    function handlePhaseSelect(phaseId: string) {
        if (!pendingSupport) return;

        workflowData = addSupportRelation(
            workflowData,
            pendingSupport.supporterStepId,
            pendingSupport.targetStepId,
            phaseId,
        );
        dispatch("workflowChange", workflowData);

        showPhaseSelectModal = false;
        pendingSupport = null;
    }

    function handleRemoveSupport(stepId: string) {
        workflowData = removeSupportByStepId(workflowData, stepId);
        dispatch("workflowChange", workflowData);
    }

    // Calculate layout rows for phase/support layout
    $: layoutRows = getLayoutRows(
        workflowData.steps,
        workflowData.supportRelations,
        globalPhases,
    );

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
            else if (showCoreStepImageModal) closeCoreStepImageModal();
            else if (captureMode) exitCaptureMode();
        }
    }

    onMount(() => window.addEventListener("keydown", handleKeyDown));
    onDestroy(() => {
        window.removeEventListener("keydown", handleKeyDown);
        if (supportHoverTimer) clearTimeout(supportHoverTimer);
    });

    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        const found = workflowSteps.rows.find((r) => r.id === stepId);
        console.log("[WorkflowSection] getStepDefinition:", {
            stepId,
            found: found ? found.values : "NOT FOUND",
            availableRows: workflowSteps.rows.map((r) => ({
                id: r.id,
                values: r.values,
            })),
        });
        return found;
    }

    function getStepUsageCount(stepId: string): number {
        return workflowData.steps.filter((s) => s.stepId === stepId).length;
    }

    // Step Management
    function handleAddStep(stepRow: WorkflowStepRow) {
        // Check if all Core Steps are added before allowing regular step addition
        if (!allCoreStepsAdded) {
            toastStore.warning("먼저 모든 Core Step을 추가해주세요.");
            showAddStepPopup = false;
            return;
        }

        console.log("[WorkflowSection] handleAddStep:", {
            stepRowId: stepRow.id,
            stepRowValues: stepRow.values,
            currentWorkflowStepsRows: workflowSteps.rows.map((r) => ({
                id: r.id,
                values: r.values,
            })),
        });

        // Create unified step for regular step
        const currentUnifiedSteps = workflowData.unifiedSteps ?? [];

        // Find the position to insert: before the last core step
        // Rule: first and last items must be core steps, so insert before the last one
        let insertIndex = currentUnifiedSteps.length;

        // Find the last core step's index
        for (let i = currentUnifiedSteps.length - 1; i >= 0; i--) {
            if (currentUnifiedSteps[i].type === "core") {
                insertIndex = i; // Insert before this core step
                break;
            }
        }

        // If there's only one core step (or none), just append to the end
        // This handles the edge case mentioned by the user
        const coreStepCount = currentUnifiedSteps.filter(
            (s) => s.type === "core",
        ).length;
        if (coreStepCount <= 1) {
            insertIndex = currentUnifiedSteps.length;
        }

        const newUnifiedStep = createUnifiedRegularStep(
            stepRow.id,
            insertIndex,
        );

        // Also create legacy step for backward compatibility
        const newLegacyStep = createStepInstance(
            stepRow.id,
            workflowData.steps.length,
        );

        console.log("[WorkflowSection] created newStep:", {
            newStepId: newUnifiedStep.id,
            newStepStepId: newUnifiedStep.stepId,
            insertIndex,
        });

        // Insert at the correct position and update order values
        const updatedUnifiedSteps = [...currentUnifiedSteps];
        updatedUnifiedSteps.splice(insertIndex, 0, newUnifiedStep);
        updatedUnifiedSteps.forEach((s, i) => (s.order = i));

        workflowData = {
            ...workflowData,
            unifiedSteps: updatedUnifiedSteps,
            steps: [...workflowData.steps, newLegacyStep],
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
        showAddStepPopup = false;
        expandedStepId = newUnifiedStep.id;
    }

    function handleRemoveStep(stepId: string) {
        if (confirm("이 스텝을 정말 삭제하시겠습니까?")) {
            if (captureTargetStepId === stepId) {
                dispatch("toggleCaptureMode", { stepId: null });
            }
            const filteredUnifiedSteps = (workflowData.unifiedSteps ?? [])
                .filter((s) => s.id !== stepId)
                .map((s, i) => ({ ...s, order: i }));

            let updatedWorkflow: ProjectWorkflowData = {
                ...workflowData,
                steps: workflowData.steps.filter((s) => s.id !== stepId),
                unifiedSteps: filteredUnifiedSteps,
                updatedAt: new Date().toISOString(),
            };
            // Clean up any orphaned support relations
            updatedWorkflow = cleanupOrphanedSupports(updatedWorkflow);
            workflowData = updatedWorkflow;
            dispatch("workflowChange", workflowData);
        }
    }

    // ========== Unified Step Reorder with Validation ==========
    function handleUnifiedReorder(fromIndex: number, toIndex: number) {
        if (fromIndex === toIndex) return;

        const steps = workflowData.unifiedSteps ?? [];

        // Validate the reorder before committing
        const validation = validateReorder(steps, fromIndex, toIndex);
        if (!validation.isValid) {
            toastStore.warning(validation.errorMessage!);
            return;
        }

        // Perform the reorder
        const updatedSteps = [...steps];
        const [removed] = updatedSteps.splice(fromIndex, 1);
        updatedSteps.splice(toIndex, 0, removed);

        // Update order values
        updatedSteps.forEach((s, i) => (s.order = i));

        // Sync to legacy arrays
        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
        dispatch("workflowChange", workflowData);
    }

    // Remove a unified step by ID with validation
    function handleRemoveUnifiedStep(stepId: string, stepIndex: number) {
        const steps = workflowData.unifiedSteps ?? [];
        const step = steps.find((s) => s.id === stepId);

        if (!step) return;

        // Check if this is a Core Step
        if (step.type === "core") {
            // Check if this Core Step has a valid definition
            const csDef = getCoreStepDefinition(step.coreStepId!);
            const isOrphanCoreStep = !csDef;

            // Skip validation for orphan Core Steps (definition deleted) - they should always be deletable
            if (!isOrphanCoreStep) {
                // Validate deletion only for valid Core Steps
                const validation = validateDeletion(steps, stepIndex);
                if (!validation.isValid) {
                    toastStore.warning(validation.errorMessage!);
                    return;
                }
            }
        }

        // Determine the confirmation message
        let confirmMessage = "이 스텝을 정말 삭제하시겠습니까?";
        if (step.type === "core") {
            const csDef = getCoreStepDefinition(step.coreStepId!);
            confirmMessage = csDef
                ? "이 Core Step을 삭제하시겠습니까?"
                : "삭제된 Core Step입니다. 정리하시겠습니까?";
        }

        if (confirm(confirmMessage)) {
            if (captureTargetStepId === stepId) {
                dispatch("toggleCaptureMode", { stepId: null });
            }

            const updatedSteps = steps
                .filter((s) => s.id !== stepId)
                .map((s, i) => ({ ...s, order: i }));

            // Sync to legacy arrays
            const syncedData = syncUnifiedToLegacy({
                ...workflowData,
                unifiedSteps: updatedSteps,
                updatedAt: new Date().toISOString(),
            });

            // Also clean up orphaned support relations
            const cleanedData = cleanupOrphanedSupports(syncedData);
            workflowData = cleanedData;
            dispatch("workflowChange", workflowData);
        }
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
                const steps = workflowData.unifiedSteps ?? [];

                // Validate the reorder before committing
                const validation = validateReorder(
                    steps,
                    unifiedDraggedIdx,
                    toIndex,
                );
                if (!validation.isValid) {
                    toastStore.warning(validation.errorMessage!);
                } else {
                    // Perform the reorder
                    const updatedSteps = [...steps];
                    const [removed] = updatedSteps.splice(unifiedDraggedIdx, 1);
                    updatedSteps.splice(toIndex, 0, removed);
                    updatedSteps.forEach((s, i) => (s.order = i));

                    // Sync to legacy arrays
                    const syncedData = syncUnifiedToLegacy({
                        ...workflowData,
                        unifiedSteps: updatedSteps,
                        updatedAt: new Date().toISOString(),
                    });

                    workflowData = syncedData;
                    dispatch("workflowChange", workflowData);
                }
            }
        }

        unifiedDraggedIdx = null;
        unifiedDropTargetIdx = null;
    }

    function handleUnifiedMoveUp(idx: number) {
        if (idx === 0) return;

        const steps = workflowData.unifiedSteps ?? [];
        const validation = validateReorder(steps, idx, idx - 1);

        if (!validation.isValid) {
            toastStore.warning(validation.errorMessage!);
            return;
        }

        const updatedSteps = [...steps];
        [updatedSteps[idx - 1], updatedSteps[idx]] = [
            updatedSteps[idx],
            updatedSteps[idx - 1],
        ];
        updatedSteps.forEach((s, i) => (s.order = i));

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
        dispatch("workflowChange", workflowData);
    }

    function handleUnifiedMoveDown(idx: number) {
        const steps = workflowData.unifiedSteps ?? [];
        if (idx >= steps.length - 1) return;

        const validation = validateReorder(steps, idx, idx + 1);

        if (!validation.isValid) {
            toastStore.warning(validation.errorMessage!);
            return;
        }

        const updatedSteps = [...steps];
        [updatedSteps[idx], updatedSteps[idx + 1]] = [
            updatedSteps[idx + 1],
            updatedSteps[idx],
        ];
        updatedSteps.forEach((s, i) => (s.order = i));

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
        dispatch("workflowChange", workflowData);
    }

    // Update Core Step in unified list
    function handleUnifiedCoreStepUpdate(
        event: CustomEvent<{ instance: CoreStepInstance }>,
        unifiedStepId: string,
    ) {
        const updatedInstance = event.detail.instance;
        const steps = workflowData.unifiedSteps ?? [];
        const updatedSteps = steps.map((s) => {
            if (s.id === unifiedStepId && s.type === "core") {
                return {
                    ...s,
                    presetValues: updatedInstance.presetValues,
                };
            }
            return s;
        });

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
        dispatch("workflowChange", workflowData);
    }

    // ========== Unified Regular Step Helpers ==========
    function removeUnifiedCapture(stepId: string, captureId: string) {
        const steps = workflowData.unifiedSteps ?? [];
        const updatedSteps = steps.map((s) => {
            if (s.id === stepId && s.type === "regular") {
                return {
                    ...s,
                    captures: (s.captures ?? []).filter(
                        (c) => c.id !== captureId,
                    ),
                };
            }
            return s;
        });

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
        dispatch("workflowChange", workflowData);
    }

    function openUnifiedAttachmentModal(
        stepId: string,
        attachment: StepAttachment,
    ) {
        editingAttachmentStepId = stepId;
        editingAttachment = attachment;
        modalCaption = attachment.caption || "";
        showAttachmentModal = true;
    }

    function addUnifiedTextAttachment(stepId: string) {
        if (!attachmentTextInput.trim()) return;

        const newAttachment = createAttachment(
            "text",
            attachmentTextInput.trim(),
        );
        const steps = workflowData.unifiedSteps ?? [];
        const updatedSteps = steps.map((s) => {
            if (s.id === stepId && s.type === "regular") {
                return {
                    ...s,
                    attachments: [...(s.attachments ?? []), newAttachment],
                };
            }
            return s;
        });

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
        dispatch("workflowChange", workflowData);
        attachmentTextInput = "";
        addingAttachmentToStepId = null;
    }

    function handleUnifiedPaste(event: ClipboardEvent, stepId: string) {
        const items = event.clipboardData?.items;
        if (!items) return;

        for (const item of items) {
            if (item.type.startsWith("image/")) {
                const blob = item.getAsFile();
                if (blob) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        pendingImageData = e.target?.result as string;
                        pendingImageStepId = stepId;
                        pendingImageCaption = "";
                        showImageAddModal = true;
                    };
                    reader.readAsDataURL(blob);
                }
                break;
            }
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

        const newCapture = createStepCapture(
            capture.slideIndex,
            capture.x,
            capture.y,
            capture.width,
            capture.height,
        );

        // Update unifiedSteps and sync to legacy arrays
        const steps = workflowData.unifiedSteps ?? [];
        const updatedSteps = steps.map((s) => {
            if (s.id === captureTargetStepId && s.type === "regular") {
                return {
                    ...s,
                    captures: [...(s.captures ?? []), newCapture],
                };
            }
            return s;
        });

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
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

    export function getCaptureOverlays() {
        const overlays: any[] = [];

        // Build a map of step ID to display info based on layoutRows
        // This ensures overlay numbering matches the UI list exactly
        const stepDisplayMap = new Map<
            string,
            {
                displayNumber: number | string; // number for main steps, phase name for supporters
                isSupporter: boolean;
                parentStepNumber?: number;
                phaseName?: string;
            }
        >();

        layoutRows.forEach((row, rowIndex) => {
            const mainStepNumber = rowIndex + 1;
            stepDisplayMap.set(row.mainStep.id, {
                displayNumber: mainStepNumber,
                isSupporter: false,
            });

            // Supporters get their parent's number + phase name
            row.supporters.forEach((supporter) => {
                stepDisplayMap.set(supporter.step.id, {
                    displayNumber: supporter.phase?.name || "위상",
                    isSupporter: true,
                    parentStepNumber: mainStepNumber,
                    phaseName: supporter.phase?.name,
                });
            });
        });

        let colorIndex = 0;
        for (
            let stepIndex = 0;
            stepIndex < workflowData.steps.length;
            stepIndex++
        ) {
            const step = workflowData.steps[stepIndex];
            const displayInfo = stepDisplayMap.get(step.id);
            const color = EVIDENCE_COLORS[colorIndex % EVIDENCE_COLORS.length];
            let captureIndexInStep = 0;

            for (const capture of step.captures) {
                overlays.push({
                    ...capture,
                    stepId: step.id,
                    workflowName,
                    stepNumber: displayInfo?.isSupporter
                        ? displayInfo.parentStepNumber // Use parent's number for supporters
                        : (displayInfo?.displayNumber ?? stepIndex + 1),
                    captureIndexInStep,
                    color,
                    colorIndex,
                    isSupporter: displayInfo?.isSupporter ?? false,
                    phaseName: displayInfo?.phaseName,
                });
                captureIndexInStep++;
            }
            colorIndex++;
        }

        // Add Core Step captures
        if (workflowData.coreStepInstances) {
            const coreStepColor = "#9333ea"; // purple-600
            workflowData.coreStepInstances.forEach((instance, instanceIdx) => {
                const csDef = getCoreStepDefinition(instance.coreStepId);
                if (!csDef) return;

                instance.presetValues.forEach((pv) => {
                    if (pv.type === "capture" && pv.captureValue) {
                        const presetDef = csDef.presets.find(
                            (p) => p.id === pv.presetId,
                        );
                        const presetName = presetDef?.name || "";
                        overlays.push({
                            ...pv.captureValue,
                            id: `${instance.id}_${pv.presetId}`,
                            stepId: instance.id,
                            workflowName,
                            stepNumber: `C${instanceIdx + 1}-${presetName}`,
                            captureIndexInStep: 0,
                            color: coreStepColor,
                            colorIndex: colorIndex + instanceIdx,
                            isCoreStep: true,
                            coreStepName: csDef.name,
                            presetName,
                        });
                    }
                });
            });
        }

        return overlays;
    }

    // Attachment Management
    function toggleAttachmentSection(stepId: string) {
        if (captureMode) exitCaptureMode();
        addingAttachmentToStepId =
            addingAttachmentToStepId === stepId ? null : stepId;
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
                    openImageAddModal(stepId, reader.result as string);
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
        const steps = workflowData.unifiedSteps ?? [];
        const step = steps.find((s) => s.id === stepId);
        if (!step) return;

        const attachment = (step.attachments ?? []).find(
            (a) => a.id === attachmentId,
        );
        if (attachment?.type === "image" && attachment.imageId) {
            try {
                await deleteAttachmentImage(attachment.imageId);
            } catch (error) {
                console.error("Failed to delete image from backend:", error);
            }
        }

        const updatedSteps = steps.map((s) => {
            if (s.id === stepId) {
                return {
                    ...s,
                    attachments: (s.attachments ?? []).filter(
                        (a) => a.id !== attachmentId,
                    ),
                };
            }
            return s;
        });

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
        dispatch("workflowChange", workflowData);
    }

    function updateUnifiedAttachment(
        stepId: string,
        attachmentId: string,
        data: string,
    ) {
        const steps = workflowData.unifiedSteps ?? [];
        const updatedSteps = steps.map((s) => {
            if (s.id === stepId) {
                return {
                    ...s,
                    attachments: (s.attachments ?? []).map((a) => {
                        if (a.id === attachmentId) {
                            return { ...a, data };
                        }
                        return a;
                    }),
                };
            }
            return s;
        });

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
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

        const steps = workflowData.unifiedSteps ?? [];
        const updatedSteps = steps.map((s) => {
            if (s.id === editingAttachmentStepId) {
                return {
                    ...s,
                    attachments: (s.attachments ?? []).map((a) => {
                        if (a.id === editingAttachment!.id) {
                            return {
                                ...a,
                                caption: modalCaption.trim() || undefined,
                                data:
                                    editingAttachment!.type === "text"
                                        ? editingAttachment!.data
                                        : a.data,
                            };
                        }
                        return a;
                    }),
                };
            }
            return s;
        });

        const syncedData = syncUnifiedToLegacy({
            ...workflowData,
            unifiedSteps: updatedSteps,
            updatedAt: new Date().toISOString(),
        });

        workflowData = syncedData;
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

        const steps = workflowData.unifiedSteps ?? [];
        const stepIndex = steps.findIndex((s) => s.id === pendingImageStepId);
        if (stepIndex === -1) return;

        isUploadingImage = true;
        try {
            const imageId = generateAttachmentId();
            const response = await uploadAttachmentImage(
                imageId,
                projectId,
                pendingImageData,
            );

            if (!response.ok) throw new Error("Failed to upload image");

            const attachment = createAttachment(
                "image",
                imageId,
                pendingImageCaption.trim() || undefined,
            );

            const updatedSteps = steps.map((s) => {
                if (s.id === pendingImageStepId) {
                    return {
                        ...s,
                        attachments: [...(s.attachments ?? []), attachment],
                    };
                }
                return s;
            });

            const syncedData = syncUnifiedToLegacy({
                ...workflowData,
                unifiedSteps: updatedSteps,
                updatedAt: new Date().toISOString(),
            });

            workflowData = syncedData;
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
        if (!activeWorkflowId) return;

        const currentWorkflow = workflows.find(
            (w) => w.id === activeWorkflowId,
        );
        const workflowName = currentWorkflow?.name || activeWorkflowId;

        if (
            confirm(
                `"${workflowName}" 워크플로우의 데이터를 삭제하시겠습니까?\n삭제된 데이터는 복구할 수 없습니다.`,
            )
        ) {
            dispatch("deleteWorkflow", { workflowId: activeWorkflowId });
        }
    }

    // Core Step Management
    function openCoreStepSelector() {
        showCoreStepSelector = !showCoreStepSelector;
    }

    function selectCoreStepToAdd(coreStepDef: CoreStepDefinition) {
        showCoreStepSelector = false;

        // Check if this Core Step is already added (can only add each Core Step once)
        if (coreStepStatus.addedIds.has(coreStepDef.id)) {
            toastStore.warning("이미 추가된 Core Step입니다.");
            return;
        }

        // Create unified step item for Core Step
        const currentSteps = workflowData.unifiedSteps ?? [];
        const order = currentSteps.length;
        const newStep = createUnifiedCoreStep(coreStepDef.id, [], order);

        const updatedSteps = [...currentSteps, newStep];

        // Also update legacy coreStepInstances for backward compatibility
        const newLegacyInstance = createCoreStepInstance(
            coreStepDef.id,
            [],
            workflowData.coreStepInstances?.length ?? 0,
        );

        workflowData = {
            ...workflowData,
            unifiedSteps: updatedSteps,
            coreStepInstances: [
                ...(workflowData.coreStepInstances ?? []),
                newLegacyInstance,
            ],
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);

        // Auto-expand the new instance for editing
        expandedCoreStepId = newStep.id;
    }

    function handleCoreStepUpdate(
        event: CustomEvent<{ instance: CoreStepInstance }>,
    ) {
        const updatedInstance = event.detail.instance;
        workflowData = {
            ...workflowData,
            coreStepInstances: (workflowData.coreStepInstances ?? []).map(
                (inst) =>
                    inst.id === updatedInstance.id ? updatedInstance : inst,
            ),
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    function handleCoreStepStartCapture(instanceId: string, presetId: string) {
        capturingForCoreStepPresetId = presetId;
        capturingCoreStepInstanceId = instanceId;
        dispatch("toggleCaptureMode", {
            stepId: `coreStep:${instanceId}:${presetId}`,
        });
    }

    // Track which core step instance is being captured for
    let capturingCoreStepInstanceId: string | null = null;

    // Called from parent when capture is completed for core step preset
    export function addCoreStepCapture(capture: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
    }) {
        if (!capturingForCoreStepPresetId || !capturingCoreStepInstanceId)
            return;

        // Find and update the unified step (primary data source)
        const steps = workflowData.unifiedSteps ?? [];
        const stepIdx = steps.findIndex(
            (s) => s.id === capturingCoreStepInstanceId && s.type === "core",
        );

        if (stepIdx >= 0) {
            const step = steps[stepIdx];
            const presetValues = step.presetValues ?? [];
            const presetIdx = presetValues.findIndex(
                (pv) => pv.presetId === capturingForCoreStepPresetId,
            );

            let updatedPresetValues;
            if (presetIdx >= 0) {
                updatedPresetValues = presetValues.map((pv, i) =>
                    i === presetIdx ? { ...pv, captureValue: capture } : pv,
                );
            } else {
                updatedPresetValues = [
                    ...presetValues,
                    {
                        presetId: capturingForCoreStepPresetId,
                        type: "capture" as const,
                        captureValue: capture,
                    },
                ];
            }

            const updatedSteps = steps.map((s, i) =>
                i === stepIdx ? { ...s, presetValues: updatedPresetValues } : s,
            );

            const syncedData = syncUnifiedToLegacy({
                ...workflowData,
                unifiedSteps: updatedSteps,
                updatedAt: new Date().toISOString(),
            });

            workflowData = syncedData;
            dispatch("workflowChange", workflowData);
        }

        capturingForCoreStepPresetId = null;
        capturingCoreStepInstanceId = null;
        dispatch("toggleCaptureMode", { stepId: null });
    }

    function removeCoreStepInstance(instanceId: string) {
        if (confirm("이 Core Step을 삭제하시겠습니까?")) {
            workflowData = {
                ...workflowData,
                coreStepInstances: (
                    workflowData.coreStepInstances ?? []
                ).filter((i) => i.id !== instanceId),
                updatedAt: new Date().toISOString(),
            };
            dispatch("workflowChange", workflowData);
        }
    }

    function moveCoreStepUp(index: number) {
        if (index === 0 || !workflowData.coreStepInstances) return;
        const instances = [...workflowData.coreStepInstances];
        [instances[index - 1], instances[index]] = [
            instances[index],
            instances[index - 1],
        ];
        instances.forEach((inst, i) => (inst.order = i));
        workflowData = {
            ...workflowData,
            coreStepInstances: instances,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    function moveCoreStepDown(index: number) {
        if (
            !workflowData.coreStepInstances ||
            index >= workflowData.coreStepInstances.length - 1
        )
            return;
        const instances = [...workflowData.coreStepInstances];
        [instances[index], instances[index + 1]] = [
            instances[index + 1],
            instances[index],
        ];
        instances.forEach((inst, i) => (inst.order = i));
        workflowData = {
            ...workflowData,
            coreStepInstances: instances,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    // Core Step Drag & Drop handlers
    function handleCoreStepDragStart(e: DragEvent, index: number) {
        coreStepDraggedIdx = index;
        coreStepDropTargetIdx = null;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", `coreStep:${index}`);
        }
    }

    function handleCoreStepDragOver(e: DragEvent, index: number) {
        e.preventDefault();
        if (coreStepDraggedIdx === null) return;
        if (coreStepDraggedIdx === index) {
            coreStepDropTargetIdx = null;
            return;
        }
        coreStepDropTargetIdx = index;
    }

    function handleCoreStepDragEnd() {
        coreStepDraggedIdx = null;
        coreStepDropTargetIdx = null;
    }

    function handleCoreStepDrop(e: DragEvent) {
        e.preventDefault();
        if (coreStepDraggedIdx === null || coreStepDropTargetIdx === null) {
            handleCoreStepDragEnd();
            return;
        }
        if (!workflowData.coreStepInstances) {
            handleCoreStepDragEnd();
            return;
        }

        const sortedInstances = [...workflowData.coreStepInstances].sort(
            (a, b) => a.order - b.order,
        );
        const [removed] = sortedInstances.splice(coreStepDraggedIdx, 1);
        sortedInstances.splice(coreStepDropTargetIdx, 0, removed);
        sortedInstances.forEach((inst, i) => (inst.order = i));

        workflowData = {
            ...workflowData,
            coreStepInstances: sortedInstances,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
        handleCoreStepDragEnd();
    }

    function toggleCoreStepExpand(instanceId: string) {
        expandedCoreStepId =
            expandedCoreStepId === instanceId ? null : instanceId;
    }

    function getCoreStepDefinition(
        coreStepId: string,
    ): CoreStepDefinition | undefined {
        return coreStepsSettings.definitions.find((d) => d.id === coreStepId);
    }

    // Core Step Image Modal Handlers
    function handleCoreStepImagePaste(
        event: CustomEvent<{ presetId: string; imageData: string }>,
        instanceId: string,
    ) {
        coreStepImageInstanceId = instanceId;
        coreStepImagePresetId = event.detail.presetId;
        coreStepPendingImageData = event.detail.imageData;
        coreStepImageCaption = "";
        coreStepImageIsEditing = false;
        showCoreStepImageModal = true;
    }

    function handleCoreStepImageClick(
        event: CustomEvent<{
            presetId: string;
            imageId: string;
            caption?: string;
        }>,
        instanceId: string,
    ) {
        coreStepImageInstanceId = instanceId;
        coreStepImagePresetId = event.detail.presetId;
        // For editing existing image, we'll get the image URL to show in modal
        const instance = (workflowData.coreStepInstances ?? []).find(
            (i) => i.id === instanceId,
        );
        if (instance) {
            const presetValue = instance.presetValues.find(
                (pv) => pv.presetId === event.detail.presetId,
            );
            if (presetValue?.imageId) {
                coreStepPendingImageData = getAttachmentImageUrl(
                    presetValue.imageId,
                );
                coreStepImageCaption = event.detail.caption || "";
                coreStepImageIsEditing = true;
                showCoreStepImageModal = true;
            }
        }
    }

    function closeCoreStepImageModal() {
        showCoreStepImageModal = false;
        coreStepPendingImageData = null;
        coreStepImagePresetId = null;
        coreStepImageInstanceId = null;
        coreStepImageCaption = "";
        coreStepImageIsEditing = false;
    }

    async function confirmCoreStepImage() {
        if (!coreStepImageInstanceId || !coreStepImagePresetId || !projectId)
            return;

        const coreStepItemRef = coreStepItemRefs[coreStepImageInstanceId];
        if (!coreStepItemRef) return;

        if (coreStepImageIsEditing) {
            // Just updating caption for existing image
            coreStepItemRef.updateImageCaption(
                coreStepImagePresetId,
                coreStepImageCaption.trim() || undefined,
            );
            closeCoreStepImageModal();
        } else {
            // Uploading new image
            if (!coreStepPendingImageData) return;

            coreStepImageIsUploading = true;
            try {
                const imageId = generateAttachmentId();
                const response = await uploadAttachmentImage(
                    imageId,
                    projectId,
                    coreStepPendingImageData,
                );

                if (!response.ok) throw new Error("Failed to upload image");

                coreStepItemRef.setImage(
                    coreStepImagePresetId,
                    imageId,
                    coreStepImageCaption.trim() || undefined,
                );
                closeCoreStepImageModal();
            } catch (error) {
                console.error("Failed to upload image:", error);
                alert("이미지 업로드에 실패했습니다.");
            } finally {
                coreStepImageIsUploading = false;
            }
        }
    }

    function handleClickOutside(event: MouseEvent) {
        if (popupRef && !popupRef.contains(event.target as Node)) {
            showAddStepPopup = false;
        }
        if (
            phaseListPopupRef &&
            !phaseListPopupRef.contains(event.target as Node)
        ) {
            showPhaseListPopup = false;
        }
    }

    // ========== Workflow Confirmation Functions ==========
    function handleConfirmWorkflow() {
        if (coreStepsRequiringLinking.length > 0) {
            // Open key step linking wizard
            showKeyStepLinkingWizard = true;
        } else {
            // No linking needed, confirm directly
            doConfirmWorkflow();
        }
    }

    function doConfirmWorkflow() {
        workflowData = confirmWorkflow(workflowData);
        workflowData = syncUnifiedToLegacy(workflowData);
        dispatch("workflowChange", workflowData);
        toastStore.success("워크플로우가 확정되었습니다.");
    }

    function handleUnconfirmWorkflow() {
        if (
            confirm(
                "워크플로우 확정을 취소하시겠습니까? 수정 모드로 전환됩니다.",
            )
        ) {
            workflowData = unconfirmWorkflow(workflowData);
            workflowData = syncUnifiedToLegacy(workflowData);
            dispatch("workflowChange", workflowData);
            toastStore.info("워크플로우 확정이 취소되었습니다.");
        }
    }

    function handleKeyStepLinkingSaveLinks(
        event: CustomEvent<{
            coreStepInstanceId: string;
            linkedSteps: KeyStepLink[];
        }>,
    ) {
        const { coreStepInstanceId, linkedSteps } = event.detail;
        workflowData = saveKeyStepLinks(
            workflowData,
            coreStepInstanceId,
            linkedSteps,
        );
        workflowData = syncUnifiedToLegacy(workflowData);
        dispatch("workflowChange", workflowData);
    }

    function handleKeyStepLinkingComplete(
        event: CustomEvent<{ links: KeyStepLinkingData[] }>,
    ) {
        showKeyStepLinkingWizard = false;
        // All links have been saved via saveLinks events, now confirm workflow
        doConfirmWorkflow();
    }

    function handleKeyStepLinkingClose() {
        showKeyStepLinkingWizard = false;
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
                    <!-- Workflow Confirmation Status / Button -->
                    {#if isWorkflowConfirmed}
                        <div class="flex items-center gap-1">
                            <span
                                class="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-medium rounded-full flex items-center gap-1"
                            >
                                <svg
                                    class="w-3 h-3"
                                    fill="currentColor"
                                    viewBox="0 0 20 20"
                                >
                                    <path
                                        fill-rule="evenodd"
                                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                        clip-rule="evenodd"
                                    />
                                </svg>
                                확정됨
                            </span>
                            <button
                                class="px-1.5 py-0.5 text-[10px] text-gray-400 hover:text-gray-600 hover:underline transition-colors"
                                on:click|stopPropagation={handleUnconfirmWorkflow}
                                title="확정 취소 - 수정 모드로 전환"
                            >
                                취소
                            </button>
                        </div>
                    {:else if canConfirmWorkflow}
                        <button
                            class="px-2 py-1 bg-green-600 text-white text-[10px] font-medium rounded-md
                                   hover:bg-green-700 transition-colors flex items-center gap-1"
                            on:click|stopPropagation={handleConfirmWorkflow}
                            title="워크플로우 확정"
                        >
                            <svg
                                class="w-3 h-3"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M5 13l4 4L19 7"
                                />
                            </svg>
                            확정
                        </button>
                    {/if}

                    <div class="w-px h-4 bg-gray-200 mx-1"></div>

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
                    {#if globalPhases.length > 0}
                        <div class="relative">
                            <button
                                class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-600 border border-purple-200 flex items-center gap-1 hover:bg-purple-200 transition-colors cursor-pointer"
                                title="클릭하여 위상 목록 보기"
                                on:click|stopPropagation={() =>
                                    (showPhaseListPopup = !showPhaseListPopup)}
                            >
                                <svg
                                    class="w-3 h-3"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                                    />
                                </svg>
                                위상 {globalPhases.length}개
                                <svg
                                    class="w-2.5 h-2.5 ml-0.5 transition-transform {showPhaseListPopup
                                        ? 'rotate-180'
                                        : ''}"
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

                            <!-- Phase List Popup -->
                            {#if showPhaseListPopup}
                                <div
                                    bind:this={phaseListPopupRef}
                                    class="absolute top-full right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-2 min-w-[160px] z-50"
                                    on:click|stopPropagation
                                >
                                    <div
                                        class="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100 mb-1"
                                    >
                                        정의된 위상
                                    </div>
                                    {#each globalPhases as phase, idx (phase.id)}
                                        <div
                                            class="px-3 py-1.5 flex items-center gap-2 text-xs text-gray-700 hover:bg-gray-50"
                                        >
                                            <span
                                                class="w-3 h-3 rounded-full shrink-0"
                                                style="background-color: {phase.color}"
                                            ></span>
                                            <span class="truncate"
                                                >{phase.name}</span
                                            >
                                        </div>
                                    {/each}
                                    <div
                                        class="border-t border-gray-100 mt-1 pt-1"
                                    >
                                        <a
                                            href="/settings#section-phases"
                                            class="px-3 py-1.5 flex items-center gap-1.5 text-xs text-purple-600 hover:bg-purple-50"
                                            on:click={() =>
                                                (showPhaseListPopup = false)}
                                        >
                                            <svg
                                                class="w-3 h-3"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    stroke-width="2"
                                                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                                                />
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    stroke-width="2"
                                                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                                />
                                            </svg>
                                            설정에서 관리
                                        </a>
                                    </div>
                                </div>
                            {/if}
                        </div>
                    {:else}
                        <a
                            href="/settings#section-phases"
                            class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-400 hover:text-purple-600 hover:bg-purple-50 border border-gray-200 flex items-center gap-1"
                            title="설정에서 위상 추가"
                        >
                            <svg
                                class="w-3 h-3"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                                />
                            </svg>
                            위상 추가
                        </a>
                    {/if}
                    <button
                        class="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                        on:click|stopPropagation={handleDeleteWorkflow}
                        title="현재 워크플로우 데이터 삭제"
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
            transition:slide={{ duration: 200, axis: "y" }}
            class="border-t border-gray-100 bg-gray-50/50 flex-1 flex flex-col min-h-0"
        >
            <div class="flex-1 flex flex-col min-h-0 overflow-hidden relative">
                <!-- Workflow Tabs (inside accordion) -->
                {#if workflows.length > 0}
                    <div
                        class="flex border-b border-gray-200 bg-gray-50 px-2 pt-2 gap-1 overflow-x-auto shrink-0"
                    >
                        {#each workflows as workflow (workflow.id)}
                            <button
                                class="px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors whitespace-nowrap
                                {activeWorkflowId === workflow.id
                                    ? 'bg-white text-blue-600 border border-b-0 border-gray-200 -mb-px'
                                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'}"
                                on:click={() =>
                                    dispatch("selectWorkflowTab", {
                                        workflowId: workflow.id,
                                    })}
                            >
                                {workflow.name}
                            </button>
                        {/each}
                        <!-- Undefined Workflow Tabs (deleted from settings but still have data) -->
                        {#each undefinedWorkflowIds as undefinedWfId (undefinedWfId)}
                            <button
                                class="px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors whitespace-nowrap flex items-center gap-1.5
                                {activeWorkflowId === undefinedWfId
                                    ? 'bg-red-50 text-red-600 border border-b-0 border-red-200 -mb-px'
                                    : 'text-red-400 hover:text-red-600 hover:bg-red-50 border border-transparent'}"
                                on:click={() =>
                                    dispatch("selectWorkflowTab", {
                                        workflowId: undefinedWfId,
                                    })}
                                title="정의되지 않은 워크플로우 - 클릭하여 삭제"
                            >
                                <svg
                                    class="w-3 h-3"
                                    fill="currentColor"
                                    viewBox="0 0 20 20"
                                >
                                    <path
                                        fill-rule="evenodd"
                                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                                        clip-rule="evenodd"
                                    />
                                </svg>
                                정의되지 않음
                            </button>
                        {/each}
                        <a
                            href="/settings#section-workflows"
                            class="px-2 py-1.5 text-xs text-gray-400 hover:text-blue-500 transition-colors"
                            title="워크플로우 추가"
                        >
                            +
                        </a>
                    </div>
                {/if}

                <!-- Undefined Workflow Delete UI -->
                {#if isUndefinedWorkflow}
                    <div
                        class="flex-1 flex flex-col items-center justify-center p-8 bg-red-50/50"
                    >
                        <div class="text-center max-w-sm">
                            <div
                                class="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center"
                            >
                                <svg
                                    class="w-8 h-8 text-red-500"
                                    fill="currentColor"
                                    viewBox="0 0 20 20"
                                >
                                    <path
                                        fill-rule="evenodd"
                                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                                        clip-rule="evenodd"
                                    />
                                </svg>
                            </div>
                            <h3
                                class="text-lg font-semibold text-gray-900 mb-2"
                            >
                                정의되지 않은 워크플로우
                            </h3>
                            <p class="text-sm text-gray-600 mb-6">
                                이 워크플로우는 설정에서 삭제되었지만 프로젝트에
                                데이터가 남아 있습니다.
                                <br />더 이상 필요하지 않다면 삭제할 수
                                있습니다.
                            </p>
                            <div class="flex flex-col gap-2">
                                <button
                                    type="button"
                                    class="w-full px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                                    on:click={() => {
                                        if (
                                            confirm(
                                                "이 워크플로우 데이터를 삭제하시겠습니까?\n삭제된 데이터는 복구할 수 없습니다.",
                                            )
                                        ) {
                                            dispatch(
                                                "deleteUndefinedWorkflow",
                                                {
                                                    workflowId:
                                                        activeWorkflowId,
                                                },
                                            );
                                        }
                                    }}
                                >
                                    <svg
                                        class="w-4 h-4"
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
                                    워크플로우 데이터 삭제
                                </button>
                                <p class="text-xs text-gray-500 mt-2">
                                    워크플로우 ID: <code
                                        class="bg-gray-200 px-1 rounded"
                                        >{activeWorkflowId}</code
                                    >
                                </p>
                            </div>
                        </div>
                    </div>
                {:else if viewMode === "graph"}
                    <D3WorkflowGraph
                        {workflowData}
                        {workflowSteps}
                        {globalPhases}
                    />
                {:else}
                    <!-- Selection Toolbar (shown when items are selected) -->
                    {#if selectedStepIds.size > 0}
                        <div
                            class="px-3 py-2 bg-blue-50 border-b border-blue-200 flex items-center gap-2 flex-wrap"
                        >
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
                        </div>
                    {/if}

                    <!-- Missing Core Steps Indicator -->
                    {#if coreStepsSettings.definitions.length > 0 && !allCoreStepsAdded}
                        <div
                            class="px-3 pt-3 pb-2 bg-amber-50/80 border-b border-amber-200"
                        >
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
                                {#each coreStepStatus.missingDefinitions as def (def.id)}
                                    <button
                                        class="px-3 py-1.5 bg-white border border-amber-300 rounded-lg text-xs font-medium text-amber-700 hover:bg-amber-100 hover:border-amber-400 transition-colors flex items-center gap-1.5 shadow-sm"
                                        on:click={() =>
                                            selectCoreStepToAdd(def)}
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

                    <!-- Add Step Buttons -->
                    <div
                        class="p-3 pb-0 bg-gray-50/50 border-b border-gray-100 relative"
                    >
                        <div class="flex gap-2">
                            <!-- Regular Step Button (disabled if core steps not complete) -->
                            <button
                                class="flex-1 py-2.5 border border-dashed rounded-lg transition-all flex items-center justify-center gap-1.5 group bg-white/80
                                {allCoreStepsAdded
                                    ? 'border-gray-300 text-gray-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50'
                                    : 'border-gray-200 text-gray-300 cursor-not-allowed opacity-60'}"
                                on:click|stopPropagation={() =>
                                    allCoreStepsAdded &&
                                    (showAddStepPopup = !showAddStepPopup)}
                                disabled={!allCoreStepsAdded}
                                title={allCoreStepsAdded
                                    ? "일반 스텝 추가"
                                    : "먼저 모든 Core Step을 추가하세요"}
                            >
                                <span class="text-xs font-medium"
                                    >＋ 스텝 연결</span
                                >
                            </button>

                            <!-- Core Step Button (if any core steps are missing) -->
                            {#if coreStepsSettings.definitions.length > 0 && !allCoreStepsAdded}
                                <button
                                    class="flex-1 py-2.5 border border-dashed border-purple-300 rounded-lg text-purple-400 hover:border-purple-500 hover:text-purple-600 hover:bg-purple-50/50 transition-all flex items-center justify-center gap-1.5 group bg-white/80"
                                    on:click|stopPropagation={openCoreStepSelector}
                                >
                                    <span class="text-xs font-medium"
                                        >＋ Core Step</span
                                    >
                                </button>
                            {/if}
                        </div>

                        {#if showAddStepPopup && allCoreStepsAdded}
                            <div bind:this={popupRef}>
                                <StepDefinitionPopup
                                    {workflowSteps}
                                    {getStepUsageCount}
                                    on:addStep={(e) => handleAddStep(e.detail)}
                                    on:deleteStepDefinition={(e) =>
                                        dispatch(
                                            "deleteStepDefinition",
                                            e.detail,
                                        )}
                                    on:createStepDefinition={(e) =>
                                        dispatch(
                                            "createStepDefinition",
                                            e.detail,
                                        )}
                                    on:updateStepDefinition={(e) =>
                                        dispatch(
                                            "updateStepDefinition",
                                            e.detail,
                                        )}
                                    on:close={() => (showAddStepPopup = false)}
                                />
                            </div>
                        {/if}

                        <!-- Core Step Selector Popup (only shows missing ones) -->
                        {#if showCoreStepSelector}
                            <div
                                class="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 p-2 z-50"
                            >
                                <div
                                    class="text-xs font-medium text-gray-500 mb-2 px-2"
                                >
                                    Core Step 선택
                                </div>
                                <div
                                    class="space-y-1 max-h-[200px] overflow-y-auto"
                                >
                                    {#each coreStepsSettings.definitions as csDef (csDef.id)}
                                        {@const isAlreadyAdded =
                                            coreStepStatus.addedIds.has(
                                                csDef.id,
                                            )}
                                        <button
                                            class="w-full px-3 py-2 text-left text-sm rounded-lg transition-colors flex items-center gap-2
                                            {isAlreadyAdded
                                                ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                                                : 'hover:bg-purple-50'}"
                                            on:click={() =>
                                                !isAlreadyAdded &&
                                                selectCoreStepToAdd(csDef)}
                                            disabled={isAlreadyAdded}
                                        >
                                            <span
                                                class="w-5 h-5 rounded-full text-white text-xs flex items-center justify-center font-medium {isAlreadyAdded
                                                    ? 'bg-gray-400'
                                                    : 'bg-purple-600'}"
                                            >
                                                {isAlreadyAdded ? "✓" : "C"}
                                            </span>
                                            <span class="flex-1 truncate"
                                                >{csDef.name}</span
                                            >
                                            {#if isAlreadyAdded}
                                                <span
                                                    class="text-xs text-gray-400"
                                                    >추가됨</span
                                                >
                                            {:else}
                                                <span
                                                    class="text-xs text-gray-400"
                                                    >{csDef.presets.length}개
                                                    필드</span
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

                    <!-- ========== Unified Step List ========== -->
                    <div
                        class="flex-1 overflow-y-auto p-3 space-y-2 relative flex flex-col"
                    >
                        <div class="relative">
                            <div
                                class="absolute left-[18px] top-0 bottom-0 w-px bg-gray-200 z-0"
                            ></div>

                            {#each sortedUnifiedSteps as unifiedStep, idx (unifiedStep.id)}
                                {@const isBeingDragged =
                                    unifiedDraggedIdx === idx}
                                {@const showDropIndicator =
                                    unifiedDropTargetIdx === idx &&
                                    unifiedDraggedIdx !== idx}

                                <!-- Core Step Item -->
                                {#if unifiedStep.type === "core"}
                                    {@const csDef = getCoreStepDefinition(
                                        unifiedStep.coreStepId!,
                                    )}
                                    {#if csDef}
                                        <div
                                            class="relative mb-2"
                                            style={isBeingDragged
                                                ? "opacity: 0.5;"
                                                : ""}
                                            draggable="true"
                                            on:dragstart={(e) =>
                                                handleUnifiedDragStart(e, idx)}
                                            on:dragend={handleUnifiedDragEnd}
                                            on:dragover={(e) =>
                                                handleUnifiedDragOver(e, idx)}
                                            on:drop={handleUnifiedDrop}
                                        >
                                            {#if showDropIndicator}
                                                <div
                                                    class="absolute top-0 left-6 right-0 h-0.5 bg-purple-500 rounded-full z-50 pointer-events-none transform -translate-y-1/2 shadow-sm"
                                                ></div>
                                            {/if}
                                            <CoreStepItem
                                                bind:this={
                                                    coreStepItemRefs[
                                                        unifiedStep.id
                                                    ]
                                                }
                                                instance={asCoreStepInstance(
                                                    unifiedStep,
                                                )}
                                                definition={csDef}
                                                displayNumber={idx + 1}
                                                isExpanded={expandedCoreStepId ===
                                                    unifiedStep.id}
                                                {projectId}
                                                {slideWidth}
                                                {slideHeight}
                                                keyStepLinks={workflowData.keyStepLinks ??
                                                    []}
                                                allSteps={sortedUnifiedSteps}
                                                coreStepDefinitions={coreStepsSettings.definitions}
                                                {workflowSteps}
                                                on:toggleExpand={() =>
                                                    toggleCoreStepExpand(
                                                        unifiedStep.id,
                                                    )}
                                                on:remove={() =>
                                                    handleRemoveUnifiedStep(
                                                        unifiedStep.id,
                                                        idx,
                                                    )}
                                                on:moveUp={() =>
                                                    handleUnifiedMoveUp(idx)}
                                                on:moveDown={() =>
                                                    handleUnifiedMoveDown(idx)}
                                                on:update={(e) =>
                                                    handleUnifiedCoreStepUpdate(
                                                        e,
                                                        unifiedStep.id,
                                                    )}
                                                on:startCapture={(e) =>
                                                    handleCoreStepStartCapture(
                                                        unifiedStep.id,
                                                        e.detail.presetId,
                                                    )}
                                                on:imagePaste={(e) =>
                                                    handleCoreStepImagePaste(
                                                        e,
                                                        unifiedStep.id,
                                                    )}
                                                on:imageClick={(e) =>
                                                    handleCoreStepImageClick(
                                                        e,
                                                        unifiedStep.id,
                                                    )}
                                            />
                                        </div>
                                    {:else}
                                        <!-- Orphan Core Step - definition이 삭제됨 -->
                                        <div
                                            class="relative mb-2 pl-6"
                                            style={isBeingDragged
                                                ? "opacity: 0.5;"
                                                : ""}
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
                                                        <div
                                                            class="flex items-center gap-2"
                                                        >
                                                            <span
                                                                class="text-xs font-medium text-red-600 bg-red-100 px-1.5 py-0.5 rounded"
                                                            >
                                                                삭제됨
                                                            </span>
                                                            <span
                                                                class="text-sm font-medium text-gray-500 truncate"
                                                            >
                                                                Core Step (정의
                                                                없음)
                                                            </span>
                                                        </div>
                                                        <p
                                                            class="text-xs text-red-500 mt-1"
                                                        >
                                                            설정에서 삭제된 Core
                                                            Step입니다.
                                                            삭제해주세요.
                                                        </p>
                                                    </div>
                                                    <button
                                                        class="px-2 py-1 text-xs text-red-600 hover:text-white bg-red-50 hover:bg-red-500 border border-red-200 hover:border-red-500 rounded transition-colors"
                                                        on:click={() =>
                                                            handleRemoveUnifiedStep(
                                                                unifiedStep.id,
                                                                idx,
                                                            )}
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
                                        {@const stepDef = getStepDefinition(
                                            unifiedStep.stepId!,
                                        )}
                                        {@const color =
                                            EVIDENCE_COLORS[
                                                idx % EVIDENCE_COLORS.length
                                            ]}
                                        {@const showSupportGuide =
                                            dragMode === "support" &&
                                            supportGuideTargetStepId ===
                                                unifiedStep.id}

                                        <div
                                            class="relative mb-2"
                                            style={isBeingDragged
                                                ? "opacity: 0.5;"
                                                : ""}
                                            draggable="true"
                                            on:dragstart={(e) =>
                                                handleUnifiedDragStart(e, idx)}
                                            on:dragend={handleUnifiedDragEnd}
                                            on:dragover={(e) =>
                                                handleUnifiedDragOver(e, idx)}
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
                                                    <div
                                                        class="support-guide-indicator"
                                                    >
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
                                                step={asWorkflowStepInstance(
                                                    unifiedStep,
                                                )}
                                                index={idx}
                                                {stepDef}
                                                {color}
                                                {workflowSteps}
                                                {projectId}
                                                {slideWidth}
                                                {slideHeight}
                                                displayNumber={idx + 1}
                                                isExpanded={expandedStepId ===
                                                    unifiedStep.id}
                                                isCapturing={captureTargetStepId ===
                                                    unifiedStep.id}
                                                isAddingAttachment={addingAttachmentToStepId ===
                                                    unifiedStep.id}
                                                {isBeingDragged}
                                                showDropIndicatorTop={false}
                                                showDropIndicatorBottom={false}
                                                isLastStep={idx ===
                                                    sortedUnifiedSteps.length -
                                                        1}
                                                bind:attachmentTextInput
                                                isSelected={selectedStepIds.has(
                                                    unifiedStep.id,
                                                )}
                                                showSelectionCheckbox={selectionModeActive}
                                                on:toggleExpand={() =>
                                                    toggleStepExpand(
                                                        unifiedStep.id,
                                                    )}
                                                on:startCapture={() =>
                                                    startCaptureForStep(
                                                        unifiedStep.id,
                                                    )}
                                                on:toggleAttachment={() =>
                                                    toggleAttachmentSection(
                                                        unifiedStep.id,
                                                    )}
                                                on:moveUp={() =>
                                                    handleUnifiedMoveUp(idx)}
                                                on:moveDown={() =>
                                                    handleUnifiedMoveDown(idx)}
                                                on:remove={() =>
                                                    handleRemoveUnifiedStep(
                                                        unifiedStep.id,
                                                        idx,
                                                    )}
                                                on:removeCapture={(e) =>
                                                    removeUnifiedCapture(
                                                        unifiedStep.id,
                                                        e.detail.captureId,
                                                    )}
                                                on:openAttachmentModal={(e) =>
                                                    openUnifiedAttachmentModal(
                                                        unifiedStep.id,
                                                        e.detail.attachment,
                                                    )}
                                                on:updateAttachment={(e) =>
                                                    updateUnifiedAttachment(
                                                        unifiedStep.id,
                                                        e.detail.attachmentId,
                                                        e.detail.data,
                                                    )}
                                                on:removeAttachment={(e) =>
                                                    removeAttachment(
                                                        unifiedStep.id,
                                                        e.detail.attachmentId,
                                                    )}
                                                on:addTextAttachment={() =>
                                                    addUnifiedTextAttachment(
                                                        unifiedStep.id,
                                                    )}
                                                on:paste={(e) =>
                                                    handleUnifiedPaste(
                                                        e.detail,
                                                        unifiedStep.id,
                                                    )}
                                                on:checkboxClick={(e) =>
                                                    handleCheckboxClick(
                                                        unifiedStep.id,
                                                        e.detail,
                                                    )}
                                                on:cardClick={(e) =>
                                                    handleCardCtrlClick(
                                                        unifiedStep.id,
                                                        e.detail,
                                                    )}
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
                                    {regularStepCount}개의 일반 스텝이 숨겨져
                                    있습니다
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

                    <!-- Modals -->
                    {#if showAttachmentModal && editingAttachment}
                        <AttachmentModal
                            attachment={editingAttachment}
                            caption={modalCaption}
                            on:save={(e) => {
                                modalCaption = e.detail.caption;
                                if (
                                    editingAttachment &&
                                    editingAttachment.type === "text"
                                ) {
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

                    <!-- Core Step Image Modal -->
                    {#if showCoreStepImageModal && coreStepPendingImageData}
                        <ImageAddModal
                            imageData={coreStepPendingImageData}
                            caption={coreStepImageCaption}
                            isUploading={coreStepImageIsUploading}
                            on:confirm={(e) => {
                                coreStepImageCaption = e.detail.caption;
                                confirmCoreStepImage();
                            }}
                            on:cancel={closeCoreStepImageModal}
                        />
                    {/if}

                    <!-- Phase Selection Modal -->
                    {#if showPhaseSelectModal && pendingSupport}
                        <div
                            class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
                            on:click={() => {
                                showPhaseSelectModal = false;
                                pendingSupport = null;
                            }}
                        >
                            <div
                                class="bg-white rounded-lg shadow-xl p-4 min-w-[200px] max-w-[300px]"
                                on:click|stopPropagation
                            >
                                <h3
                                    class="text-sm font-medium text-gray-800 mb-3"
                                >
                                    위상 선택
                                </h3>
                                <div class="space-y-2">
                                    {#each globalPhases as phase (phase.id)}
                                        <button
                                            class="w-full px-3 py-2 text-left text-sm rounded-lg border border-gray-200 hover:border-purple-400 hover:bg-purple-50 transition-colors flex items-center gap-2"
                                            on:click={() =>
                                                handlePhaseSelect(phase.id)}
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
                                    on:click={() => {
                                        showPhaseSelectModal = false;
                                        pendingSupport = null;
                                    }}
                                >
                                    취소
                                </button>
                            </div>
                        </div>
                    {/if}
                {/if}
            </div>
        </div>
    {/if}
</div>

<!-- Key Step Linking Wizard -->
<KeyStepLinkingWizard
    isOpen={showKeyStepLinkingWizard}
    coreStepsToLink={coreStepsRequiringLinking}
    allSteps={sortedUnifiedSteps}
    coreStepDefinitions={coreStepsSettings.definitions}
    {workflowSteps}
    existingLinks={workflowData.keyStepLinks ?? []}
    on:close={handleKeyStepLinkingClose}
    on:complete={handleKeyStepLinkingComplete}
    on:saveLinks={handleKeyStepLinkingSaveLinks}
/>

<style>
    /* Support guide bounce animation - bounces horizontally to the right */
    :global(.animate-bounce-right) {
        animation: bounce-right 0.6s ease-in-out infinite;
    }

    @keyframes bounce-right {
        0%,
        100% {
            transform: translateX(0);
        }
        50% {
            transform: translateX(4px);
        }
    }

    /* Support guide indicator container */
    .support-guide-indicator {
        display: flex;
        align-items: center;
    }

    /* Core step item cursor for drag */
    .core-step-item {
        cursor: grab;
    }
    .core-step-item:active {
        cursor: grabbing;
    }
</style>
