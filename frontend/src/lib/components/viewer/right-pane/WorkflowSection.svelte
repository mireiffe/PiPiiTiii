<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import AttachmentModal from "./workflow/AttachmentModal.svelte";
    import ImageAddModal from "./workflow/ImageAddModal.svelte";
    import D3WorkflowGraph from "./workflow/D3WorkflowGraph.svelte";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        ProjectWorkflowData,
        StepAttachment,
        PhaseType,
        CoreStepsSettings,
        CoreStepDefinition,
        CoreStepInstance,
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
        addSupportRelation,
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
        saveKeyStepLinks,
        confirmWorkflow,
        unconfirmWorkflow,
    } from "$lib/types/workflow";
    import KeyStepLinkingWizard from "./workflow/KeyStepLinkingWizard.svelte";
    import PhaseSelectModal from "./workflow/PhaseSelectModal.svelte";
    import SelectionToolbar from "./workflow/SelectionToolbar.svelte";
    import UndefinedWorkflowPanel from "./workflow/UndefinedWorkflowPanel.svelte";
    import CoreStepMissingIndicator from "./workflow/CoreStepMissingIndicator.svelte";
    import WorkflowTabBar from "./workflow/WorkflowTabBar.svelte";
    import AddStepButtonGroup from "./workflow/AddStepButtonGroup.svelte";
    import WorkflowHeader from "./workflow/WorkflowHeader.svelte";
    import UnifiedStepList from "./workflow/UnifiedStepList.svelte";
    import { toastStore } from "$lib/stores/toast";
    import { modalStore } from "$lib/stores/modal";
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
    export let phenomenonAttributes: string[] = [];
    export let availableAttributes: { key: string; display_name: string; attr_type: { variant: string } }[] = [];
    export let projectAttributeValues: Record<string, string> = {};
    export let selectedSlideIndices: number[] = [];

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

    // Support/Phase creation state
    let supportGuideTargetStepId: string | null = null; // Target step for support placement
    let supportHoverTimer: ReturnType<typeof setTimeout> | null = null;
    const SUPPORT_GUIDE_DELAY = 300; // ms to wait before showing support guide (0.3 seconds)

    // Phase selection modal state - now using modalStore
    // (showPhaseSelectModal and pendingSupport moved to modalStore)

    // Phase list popup state
    let showPhaseListPopup = false;
    let phaseListPopupRef: HTMLDivElement | null = null;

    // Core Step state
    let showCoreStepSelector = false;
    let expandedCoreStepId: string | null = null;
    let capturingForCoreStepPresetId: string | null = null;

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

    function handlePhaseSelect(event: CustomEvent<{ phaseId: string }>) {
        const { phaseId } = event.detail;
        const { supporterStepId, targetStepId } = $modalStore.phaseSelect;

        if (!supporterStepId || !targetStepId) return;

        workflowData = addSupportRelation(
            workflowData,
            supporterStepId,
            targetStepId,
            phaseId,
        );
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
                <WorkflowHeader
                    bind:showPhaseListPopup
                    {isWorkflowConfirmed}
                    {canConfirmWorkflow}
                    {viewMode}
                    {globalPhases}
                    on:confirm={handleConfirmWorkflow}
                    on:unconfirm={handleUnconfirmWorkflow}
                    on:delete={handleDeleteWorkflow}
                    on:viewModeChange={(e) => (viewMode = e.detail)}
                    on:phasePopupToggle={(e) => (showPhaseListPopup = e.detail)}
                />
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
                <WorkflowTabBar
                    {workflows}
                    {undefinedWorkflowIds}
                    {activeWorkflowId}
                    on:selectTab={(e) => dispatch("selectWorkflowTab", e.detail)}
                />

                <!-- Undefined Workflow Delete UI -->
                {#if isUndefinedWorkflow}
                    <UndefinedWorkflowPanel
                        workflowId={activeWorkflowId}
                        on:delete={(e) => dispatch("deleteUndefinedWorkflow", e.detail)}
                    />
                {:else if viewMode === "graph"}
                    <D3WorkflowGraph
                        {workflowData}
                        {workflowSteps}
                        {globalPhases}
                    />
                {:else}
                    <!-- Selection Toolbar (shown when items are selected) -->
                    <SelectionToolbar
                        allStepIds={workflowData.steps.map((s) => s.id)}
                    />

                    <!-- Missing Core Steps Indicator -->
                    <CoreStepMissingIndicator
                        missingDefinitions={coreStepStatus.missingDefinitions}
                        on:selectCoreStep={(e) => selectCoreStepToAdd(e.detail.definition)}
                    />

                    <!-- Add Step Buttons -->
                    <AddStepButtonGroup
                        {workflowSteps}
                        {coreStepsSettings}
                        {allCoreStepsAdded}
                        addedCoreStepIds={coreStepStatus.addedIds}
                        {getStepUsageCount}
                        on:addStep={(e) => handleAddStep(e.detail)}
                        on:selectCoreStep={(e) => selectCoreStepToAdd(e.detail.definition)}
                        on:deleteStepDefinition={(e) => dispatch("deleteStepDefinition", e.detail)}
                        on:createStepDefinition={(e) => dispatch("createStepDefinition", e.detail)}
                        on:updateStepDefinition={(e) => dispatch("updateStepDefinition", e.detail)}
                    />

                    <!-- ========== Unified Step List ========== -->
                    <UnifiedStepList
                        {sortedUnifiedSteps}
                        {workflowSteps}
                        {coreStepsSettings}
                        {projectId}
                        {slideWidth}
                        {slideHeight}
                        {allCoreStepsAdded}
                        {regularStepCount}
                        keyStepLinks={workflowData.keyStepLinks ?? []}
                        {phenomenonAttributes}
                        {availableAttributes}
                        {projectAttributeValues}
                        {selectedSlideIndices}
                        {expandedStepId}
                        {expandedCoreStepId}
                        {captureTargetStepId}
                        {addingAttachmentToStepId}
                        bind:attachmentTextInput
                        {selectedStepIds}
                        {selectionModeActive}
                        {dragMode}
                        {supportGuideTargetStepId}
                        bind:coreStepItemRefs
                        on:toggleCoreStepExpand={(e) => toggleCoreStepExpand(e.detail.instanceId)}
                        on:removeUnifiedStep={(e) => handleRemoveUnifiedStep(e.detail.stepId, e.detail.idx)}
                        on:unifiedMoveUp={(e) => handleUnifiedMoveUp(e.detail.idx)}
                        on:unifiedMoveDown={(e) => handleUnifiedMoveDown(e.detail.idx)}
                        on:unifiedCoreStepUpdate={(e) => handleUnifiedCoreStepUpdate(e.detail.event, e.detail.unifiedStepId)}
                        on:coreStepStartCapture={(e) => handleCoreStepStartCapture(e.detail.instanceId, e.detail.presetId)}
                        on:coreStepImagePaste={(e) => handleCoreStepImagePaste(e.detail.event, e.detail.instanceId)}
                        on:coreStepImageClick={(e) => handleCoreStepImageClick(e.detail.event, e.detail.instanceId)}
                        on:toggleStepExpand={(e) => toggleStepExpand(e.detail.stepId)}
                        on:startCaptureForStep={(e) => startCaptureForStep(e.detail.stepId)}
                        on:toggleAttachmentSection={(e) => toggleAttachmentSection(e.detail.stepId)}
                        on:removeUnifiedCapture={(e) => removeUnifiedCapture(e.detail.stepId, e.detail.captureId)}
                        on:openUnifiedAttachmentModal={(e) => openUnifiedAttachmentModal(e.detail.stepId, e.detail.attachment)}
                        on:updateUnifiedAttachment={(e) => updateUnifiedAttachment(e.detail.stepId, e.detail.attachmentId, e.detail.data)}
                        on:removeAttachment={(e) => removeAttachment(e.detail.stepId, e.detail.attachmentId)}
                        on:addUnifiedTextAttachment={(e) => addUnifiedTextAttachment(e.detail.stepId)}
                        on:handleUnifiedPaste={(e) => handleUnifiedPaste(e.detail.event, e.detail.stepId)}
                        on:checkboxClick={(e) => handleCheckboxClick(e.detail.stepId, e.detail.event)}
                        on:cardCtrlClick={(e) => handleCardCtrlClick(e.detail.stepId, e.detail.event)}
                        on:unifiedReorder={(e) => handleUnifiedReorder(e.detail.fromIndex, e.detail.toIndex)}
                    />

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
                    <PhaseSelectModal
                        {globalPhases}
                        on:select={handlePhaseSelect}
                    />
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
</style>
