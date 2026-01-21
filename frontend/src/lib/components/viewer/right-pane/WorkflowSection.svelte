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
        LayoutRow,
        CoreStepsSettings,
        CoreStepDefinition,
        CoreStepInstance,
        CoreStepPresetValue,
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
        isStepSupporter,
        getMainFlowSteps,
        createCoreStepInstance,
    } from "$lib/types/workflow";
    import CoreStepInputModal from "./workflow/CoreStepInputModal.svelte";
    import CoreStepItem from "./workflow/CoreStepItem.svelte";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";
    import {
        uploadAttachmentImage,
        deleteAttachmentImage,
    } from "$lib/api/project";

    export let isExpanded = false;
    export let projectId: string = "";
    export let workflowData: ProjectWorkflowData = createEmptyWorkflowData();
    export let workflowSteps: WorkflowSteps = { columns: [], rows: [] };
    export let globalPhases: PhaseType[] = [];  // Global phases from settings
    export let coreStepsSettings: CoreStepsSettings = { definitions: [] };  // Core step definitions from settings
    export let savingWorkflow = false;
    export let captureMode = false;
    export let captureTargetStepId: string | null = null;
    export let workflowName: string = "Workflow";  // Name of current workflow for overlay labels
    export let workflows: { id: string; name: string }[] = [];  // Available workflows
    export let activeWorkflowId: string | null = null;  // Currently selected workflow

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

    // Drag & Drop State - Unified mode system
    // Only one drag mode is active at a time to avoid UI conflicts
    type DragMode = 'reorder' | 'support' | null;
    let dragMode: DragMode = null;
    let dragState: DragDropState = { draggedIndex: null, dropTargetIndex: null };

    // Support/Phase creation state
    let supportGuideTargetStepId: string | null = null;  // Target step for support placement
    let supportHoverTimer: ReturnType<typeof setTimeout> | null = null;
    const SUPPORT_GUIDE_DELAY = 300; // ms to wait before showing support guide (0.3 seconds)

    // Phase selection modal state
    let showPhaseSelectModal = false;
    let pendingSupport: { supporterStepId: string; targetStepId: string } | null = null;

    // Phase list popup state
    let showPhaseListPopup = false;
    let phaseListPopupRef: HTMLDivElement | null = null;

    // Core Step state
    let showCoreStepSelector = false;
    let showCoreStepInputModal = false;
    let selectedCoreStepDef: CoreStepDefinition | null = null;
    let expandedCoreStepId: string | null = null;
    let coreStepInputModalRef: CoreStepInputModal | null = null;
    let capturingForCoreStepPresetId: string | null = null;

    // Multi-selection state
    let selectedStepIds: Set<string> = new Set();
    let lastClickedStepId: string | null = null;
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
        selectionModeActive = false;
    }

    function selectAll() {
        workflowData.steps.forEach(step => selectedStepIds.add(step.id));
        selectedStepIds = selectedStepIds;
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
        if (dragMode === 'support') {
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

    function handleStepHoverForSupport(e: DragEvent, targetStepId: string, forceImmediate: boolean = false) {
        if (dragState.draggedIndex === null) return;

        const draggedStep = workflowData.steps[dragState.draggedIndex];

        // Can't support yourself
        if (draggedStep.id === targetStepId) {
            if (dragMode === 'support') clearSupportGuide();
            return;
        }

        // If already in support mode for this step, keep it active
        if (dragMode === 'support' && supportGuideTargetStepId === targetStepId) {
            return;  // Already active, maintain it
        }

        // Validate support creation
        const validationError = validateSupportCreation(
            draggedStep.id,
            targetStepId,
            workflowData.steps,
            workflowData.supportRelations
        );

        if (validationError) {
            if (dragMode === 'support') clearSupportGuide();
            return;
        }

        // If forceImmediate (Shift+drag), activate support mode immediately
        if (forceImmediate) {
            if (supportHoverTimer) {
                clearTimeout(supportHoverTimer);
                supportHoverTimer = null;
            }
            dragMode = 'support';
            supportGuideTargetStepId = targetStepId;
            return;
        }

        // If already targeting this step, skip
        if (supportGuideTargetStepId === targetStepId && supportHoverTimer) {
            return;  // Timer already running
        }

        // Clear previous timer and start new one
        if (supportHoverTimer) {
            clearTimeout(supportHoverTimer);
            supportHoverTimer = null;
        }

        supportHoverTimer = setTimeout(() => {
            dragMode = 'support';
            supportGuideTargetStepId = targetStepId;
        }, SUPPORT_GUIDE_DELAY);
    }

    function handleSupportDrop(e: DragEvent, targetStepId: string) {
        e.preventDefault();
        e.stopPropagation();

        if (dragState.draggedIndex === null || dragMode !== 'support' || !supportGuideTargetStepId) {
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
            workflowData.supportRelations
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
            alert("먼저 설정에서 위상을 추가해주세요. 메인 메뉴 > 설정 > 위상 (Phase)에서 추가할 수 있습니다.");
            clearAllDragGuides();
            dragState = { draggedIndex: null, dropTargetIndex: null };
            return;
        } else if (globalPhases.length === 1) {
            // Only one phase: auto-select
            workflowData = addSupportRelation(workflowData, draggedStep.id, targetStepId, globalPhases[0].id);
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
            phaseId
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
        globalPhases
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
        console.log('[WorkflowSection] getStepDefinition:', {
            stepId,
            found: found ? found.values : 'NOT FOUND',
            availableRows: workflowSteps.rows.map(r => ({ id: r.id, values: r.values }))
        });
        return found;
    }

    function getStepUsageCount(stepId: string): number {
        return workflowData.steps.filter((s) => s.stepId === stepId).length;
    }

    // Step Management
    function handleAddStep(stepRow: WorkflowStepRow) {
        console.log('[WorkflowSection] handleAddStep:', {
            stepRowId: stepRow.id,
            stepRowValues: stepRow.values,
            currentWorkflowStepsRows: workflowSteps.rows.map(r => ({ id: r.id, values: r.values }))
        });
        const newStep = createStepInstance(stepRow.id, workflowData.steps.length);
        console.log('[WorkflowSection] created newStep:', {
            newStepId: newStep.id,
            newStepStepId: newStep.stepId
        });
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
            // Clean up any orphaned support relations
            updatedWorkflow = cleanupOrphanedSupports(updatedWorkflow);
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

        // Build a map of step ID to display info based on layoutRows
        // This ensures overlay numbering matches the UI list exactly
        const stepDisplayMap = new Map<string, {
            displayNumber: number | string;  // number for main steps, phase name for supporters
            isSupporter: boolean;
            parentStepNumber?: number;
            phaseName?: string;
        }>();

        layoutRows.forEach((row, rowIndex) => {
            const mainStepNumber = rowIndex + 1;
            stepDisplayMap.set(row.mainStep.id, {
                displayNumber: mainStepNumber,
                isSupporter: false,
            });

            // Supporters get their parent's number + phase name
            row.supporters.forEach(supporter => {
                stepDisplayMap.set(supporter.step.id, {
                    displayNumber: supporter.phase?.name || '위상',
                    isSupporter: true,
                    parentStepNumber: mainStepNumber,
                    phaseName: supporter.phase?.name,
                });
            });
        });

        let colorIndex = 0;
        for (let stepIndex = 0; stepIndex < workflowData.steps.length; stepIndex++) {
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
                        ? displayInfo.parentStepNumber  // Use parent's number for supporters
                        : displayInfo?.displayNumber ?? (stepIndex + 1),
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

    // Core Step Management
    function openCoreStepSelector() {
        showCoreStepSelector = !showCoreStepSelector;
    }

    function selectCoreStepToAdd(coreStepDef: CoreStepDefinition) {
        selectedCoreStepDef = coreStepDef;
        showCoreStepSelector = false;
        showCoreStepInputModal = true;
    }

    function handleCoreStepConfirm(event: CustomEvent<{ presetValues: CoreStepPresetValue[] }>) {
        if (!selectedCoreStepDef) return;

        const order = (workflowData.coreStepInstances?.length ?? 0);
        const newInstance = createCoreStepInstance(
            selectedCoreStepDef.id,
            event.detail.presetValues,
            order
        );

        workflowData = {
            ...workflowData,
            coreStepInstances: [...(workflowData.coreStepInstances ?? []), newInstance],
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);

        showCoreStepInputModal = false;
        selectedCoreStepDef = null;
        expandedCoreStepId = newInstance.id;
    }

    function handleCoreStepCancel() {
        showCoreStepInputModal = false;
        selectedCoreStepDef = null;
        capturingForCoreStepPresetId = null;
    }

    function handleCoreStepStartCapture(event: CustomEvent<{ presetId: string }>) {
        capturingForCoreStepPresetId = event.detail.presetId;
        dispatch("toggleCaptureMode", { stepId: `coreStep:${event.detail.presetId}` });
    }

    // Called from parent when capture is completed for core step preset
    export function addCoreStepCapture(capture: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
    }) {
        if (!capturingForCoreStepPresetId || !coreStepInputModalRef) return;

        coreStepInputModalRef.setCaptureValue(capturingForCoreStepPresetId, capture);
        capturingForCoreStepPresetId = null;
        dispatch("toggleCaptureMode", { stepId: null });
    }

    function removeCoreStepInstance(instanceId: string) {
        if (confirm("이 Core Step을 삭제하시겠습니까?")) {
            workflowData = {
                ...workflowData,
                coreStepInstances: (workflowData.coreStepInstances ?? []).filter(i => i.id !== instanceId),
                updatedAt: new Date().toISOString(),
            };
            dispatch("workflowChange", workflowData);
        }
    }

    function moveCoreStepUp(index: number) {
        if (index === 0 || !workflowData.coreStepInstances) return;
        const instances = [...workflowData.coreStepInstances];
        [instances[index - 1], instances[index]] = [instances[index], instances[index - 1]];
        instances.forEach((inst, i) => inst.order = i);
        workflowData = { ...workflowData, coreStepInstances: instances, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function moveCoreStepDown(index: number) {
        if (!workflowData.coreStepInstances || index >= workflowData.coreStepInstances.length - 1) return;
        const instances = [...workflowData.coreStepInstances];
        [instances[index], instances[index + 1]] = [instances[index + 1], instances[index]];
        instances.forEach((inst, i) => inst.order = i);
        workflowData = { ...workflowData, coreStepInstances: instances, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function toggleCoreStepExpand(instanceId: string) {
        expandedCoreStepId = expandedCoreStepId === instanceId ? null : instanceId;
    }

    function getCoreStepDefinition(coreStepId: string): CoreStepDefinition | undefined {
        return coreStepsSettings.definitions.find(d => d.id === coreStepId);
    }

    function handleClickOutside(event: MouseEvent) {
        if (popupRef && !popupRef.contains(event.target as Node)) {
            showAddStepPopup = false;
        }
        if (phaseListPopupRef && !phaseListPopupRef.contains(event.target as Node)) {
            showPhaseListPopup = false;
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
                    {#if globalPhases.length > 0}
                        <div class="relative">
                            <button
                                class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-600 border border-purple-200 flex items-center gap-1 hover:bg-purple-200 transition-colors cursor-pointer"
                                title="클릭하여 위상 목록 보기"
                                on:click|stopPropagation={() => (showPhaseListPopup = !showPhaseListPopup)}
                            >
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                                </svg>
                                위상 {globalPhases.length}개
                                <svg class="w-2.5 h-2.5 ml-0.5 transition-transform {showPhaseListPopup ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>

                            <!-- Phase List Popup -->
                            {#if showPhaseListPopup}
                                <div
                                    bind:this={phaseListPopupRef}
                                    class="absolute top-full right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-2 min-w-[160px] z-50"
                                    on:click|stopPropagation
                                >
                                    <div class="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100 mb-1">
                                        정의된 위상
                                    </div>
                                    {#each globalPhases as phase, idx (phase.id)}
                                        <div class="px-3 py-1.5 flex items-center gap-2 text-xs text-gray-700 hover:bg-gray-50">
                                            <span
                                                class="w-3 h-3 rounded-full shrink-0"
                                                style="background-color: {phase.color}"
                                            ></span>
                                            <span class="truncate">{phase.name}</span>
                                        </div>
                                    {/each}
                                    <div class="border-t border-gray-100 mt-1 pt-1">
                                        <a
                                            href="/settings#section-phases"
                                            class="px-3 py-1.5 flex items-center gap-1.5 text-xs text-purple-600 hover:bg-purple-50"
                                            on:click={() => (showPhaseListPopup = false)}
                                        >
                                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
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
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                            </svg>
                            위상 추가
                        </a>
                    {/if}
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
            <!-- Workflow Tabs (inside accordion) -->
            {#if workflows.length > 0}
                <div class="flex border-b border-gray-200 bg-gray-50 px-2 pt-2 gap-1 overflow-x-auto shrink-0">
                    {#each workflows as workflow (workflow.id)}
                        <button
                            class="px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors whitespace-nowrap
                                {activeWorkflowId === workflow.id
                                    ? 'bg-white text-blue-600 border border-b-0 border-gray-200 -mb-px'
                                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'}"
                            on:click={() => dispatch("selectWorkflowTab", { workflowId: workflow.id })}
                        >
                            {workflow.name}
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

            {#if viewMode === "graph"}
                <D3WorkflowGraph
                    {workflowData}
                    {workflowSteps}
                    {globalPhases}
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
                    </div>
                {/if}

                <!-- Add Step Buttons -->
                <div class="p-3 pb-0 bg-gray-50/50 border-b border-gray-100 relative">
                    <div class="flex gap-2">
                        <!-- Regular Step Button -->
                        <button
                            class="flex-1 py-2.5 border border-dashed border-gray-300 rounded-lg text-gray-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-center gap-1.5 group bg-white/80"
                            on:click|stopPropagation={() => (showAddStepPopup = !showAddStepPopup)}
                        >
                            <span class="text-xs font-medium">＋ 스텝 연결</span>
                        </button>

                        <!-- Core Step Button (if core steps defined) -->
                        {#if coreStepsSettings.definitions.length > 0}
                            <button
                                class="flex-1 py-2.5 border border-dashed border-purple-300 rounded-lg text-purple-400 hover:border-purple-500 hover:text-purple-600 hover:bg-purple-50/50 transition-all flex items-center justify-center gap-1.5 group bg-white/80"
                                on:click|stopPropagation={openCoreStepSelector}
                            >
                                <span class="text-xs font-medium">＋ Core Step</span>
                            </button>
                        {/if}
                    </div>

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

                    <!-- Core Step Selector Popup -->
                    {#if showCoreStepSelector}
                        <div class="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 p-2 z-50">
                            <div class="text-xs font-medium text-gray-500 mb-2 px-2">Core Step 선택</div>
                            <div class="space-y-1 max-h-[200px] overflow-y-auto">
                                {#each coreStepsSettings.definitions as csDef (csDef.id)}
                                    <button
                                        class="w-full px-3 py-2 text-left text-sm rounded-lg hover:bg-purple-50 transition-colors flex items-center gap-2"
                                        on:click={() => selectCoreStepToAdd(csDef)}
                                    >
                                        <span class="w-5 h-5 rounded-full bg-purple-600 text-white text-xs flex items-center justify-center font-medium">C</span>
                                        <span class="flex-1 truncate">{csDef.name}</span>
                                        <span class="text-xs text-gray-400">{csDef.presets.length}개 필드</span>
                                    </button>
                                {/each}
                            </div>
                            <div class="border-t border-gray-100 mt-2 pt-2">
                                <a
                                    href="/settings#section-core_steps"
                                    class="block px-3 py-1.5 text-xs text-purple-600 hover:bg-purple-50 rounded-lg"
                                >
                                    설정에서 Core Step 관리
                                </a>
                            </div>
                        </div>
                    {/if}
                </div>

                <!-- Core Step Instances -->
                {#if workflowData.coreStepInstances && workflowData.coreStepInstances.length > 0}
                    <div class="px-3 pt-3 pb-1">
                        <div class="text-xs font-medium text-purple-600 mb-2 flex items-center gap-1">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                            </svg>
                            Core Steps ({workflowData.coreStepInstances.length})
                        </div>
                        <div class="space-y-2">
                            {#each workflowData.coreStepInstances.sort((a, b) => a.order - b.order) as instance, idx (instance.id)}
                                {@const csDef = getCoreStepDefinition(instance.coreStepId)}
                                {#if csDef}
                                    <CoreStepItem
                                        {instance}
                                        definition={csDef}
                                        displayNumber={idx + 1}
                                        isExpanded={expandedCoreStepId === instance.id}
                                        on:toggleExpand={() => toggleCoreStepExpand(instance.id)}
                                        on:remove={() => removeCoreStepInstance(instance.id)}
                                        on:moveUp={() => moveCoreStepUp(idx)}
                                        on:moveDown={() => moveCoreStepDown(idx)}
                                    />
                                {/if}
                            {/each}
                        </div>
                    </div>
                    <div class="border-b border-purple-100 mx-3"></div>
                {/if}

                <!-- Step List with Phase Support -->
                <div class="flex-1 overflow-y-auto p-3 space-y-3 relative flex flex-col">
                    <div class="relative">
                        <div class="absolute left-[23px] top-0 bottom-0 w-px bg-gray-200 z-0"></div>
                        {#each layoutRows as row, rowIndex (row.mainStep.id)}
                            {@const step = row.mainStep}
                            {@const index = workflowData.steps.findIndex(s => s.id === step.id)}
                            {@const stepDef = getStepDefinition(step.stepId)}
                            {@const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}
                            {@const showSupportGuide = dragMode === 'support' && supportGuideTargetStepId === step.id}
                            {@const mainStepNumber = rowIndex + 1}

                            <div class="relative mb-2">
                                <!-- Support creation guide -->
                                {#if showSupportGuide}
                                    <div class="absolute -right-1 top-1/2 -translate-y-1/2 z-20 pointer-events-none">
                                        <div class="support-guide-indicator">
                                            <div class="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center shadow-lg animate-bounce-right">
                                                <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 4v16m8-8H4" />
                                                </svg>
                                            </div>
                                            <span class="absolute left-full ml-1 top-1/2 -translate-y-1/2 whitespace-nowrap text-[10px] font-medium text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded shadow">
                                                위상 지원
                                            </span>
                                        </div>
                                    </div>
                                {/if}

                                <div
                                    draggable="true"
                                    on:dragstart={(e) => dragDropHandlers.handleDragStart(e, index)}
                                    on:dragend={() => { dragDropHandlers.handleDragEnd(); clearAllDragGuides(); }}
                                    on:drop={(e) => {
                                        if (dragMode === 'support' && supportGuideTargetStepId === step.id) {
                                            handleSupportDrop(e, step.id);
                                        } else {
                                            dragDropHandlers.handleDrop(e);
                                        }
                                    }}
                                    on:dragover={(e) => {
                                        dragDropHandlers.handleDragOver(e, index);
                                        handleStepHoverForSupport(e, step.id, e.shiftKey);
                                    }}
                                    on:dragleave={(e) => handleDragLeave(e, step.id)}
                                >
                                    <WorkflowStepItem
                                        {step}
                                        {index}
                                        {stepDef}
                                        {color}
                                        {workflowSteps}
                                        displayNumber={mainStepNumber}
                                        isExpanded={expandedStepId === step.id}
                                        isCapturing={captureTargetStepId === step.id}
                                        isAddingAttachment={addingAttachmentToStepId === step.id}
                                        isBeingDragged={dragState.draggedIndex === index}
                                        showDropIndicatorTop={dragState.dropTargetIndex === index && dragState.draggedIndex !== index && dragState.draggedIndex !== index - 1}
                                        showDropIndicatorBottom={dragState.dropTargetIndex === index + 1 && index === workflowData.steps.length - 1 && dragState.draggedIndex !== index}
                                        isLastStep={index === workflowData.steps.length - 1}
                                        bind:attachmentTextInput
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

                                <!-- Supporter steps (indented, with phase indicator) -->
                                {#if row.supporters.length > 0}
                                    <div class="ml-8 mt-1 space-y-1 border-l-2 border-purple-200 pl-2">
                                        {#each row.supporters as supporter, supLocalIdx (supporter.step.id)}
                                            {@const supStep = supporter.step}
                                            {@const supIndex = workflowData.steps.findIndex(s => s.id === supStep.id)}
                                            {@const supStepDef = getStepDefinition(supStep.stepId)}
                                            {@const supColor = EVIDENCE_COLORS[supIndex % EVIDENCE_COLORS.length]}
                                            {@const supporterDisplayNumber = supporter.phase?.name || '위상'}

                                            <div class="relative group">

                                                <div
                                                    draggable="true"
                                                    on:dragstart={(e) => dragDropHandlers.handleDragStart(e, supIndex)}
                                                    on:dragend={() => { dragDropHandlers.handleDragEnd(); clearAllDragGuides(); }}
                                                    on:drop={dragDropHandlers.handleDrop}
                                                    on:dragover={(e) => dragDropHandlers.handleDragOver(e, supIndex)}
                                                >
                                                    <WorkflowStepItem
                                                        step={supStep}
                                                        index={supIndex}
                                                        stepDef={supStepDef}
                                                        color={supColor}
                                                        {workflowSteps}
                                                        displayNumber={supporterDisplayNumber}
                                                        isExpanded={expandedStepId === supStep.id}
                                                        isCapturing={captureTargetStepId === supStep.id}
                                                        isAddingAttachment={addingAttachmentToStepId === supStep.id}
                                                        isBeingDragged={dragState.draggedIndex === supIndex}
                                                        showDropIndicatorTop={false}
                                                        showDropIndicatorBottom={false}
                                                        isLastStep={supIndex === workflowData.steps.length - 1}
                                                        bind:attachmentTextInput
                                                        isSelected={selectedStepIds.has(supStep.id)}
                                                        showSelectionCheckbox={selectionModeActive}
                                                        supportIndicator={true}
                                                        phaseColor={supporter.phase?.color}
                                                        phaseName={supporter.phase?.name}
                                                        on:toggleExpand={() => toggleStepExpand(supStep.id)}
                                                        on:startCapture={() => startCaptureForStep(supStep.id)}
                                                        on:toggleAttachment={() => toggleAttachmentSection(supStep.id)}
                                                        on:moveUp={() => moveStepUp(supIndex)}
                                                        on:moveDown={() => moveStepDown(supIndex)}
                                                        on:remove={() => handleRemoveStep(supStep.id)}
                                                        on:removeCapture={(e) => removeCapture(supStep.id, e.detail.captureId)}
                                                        on:openAttachmentModal={(e) => openAttachmentModal(supStep.id, e.detail.attachment)}
                                                        on:addTextAttachment={() => addTextAttachment(supStep.id)}
                                                        on:paste={(e) => handlePaste(e.detail, supStep.id)}
                                                        on:checkboxClick={(e) => handleCheckboxClick(supStep.id, e.detail)}
                                                        on:cardClick={(e) => handleCardCtrlClick(supStep.id, e.detail)}
                                                        on:removeSupport={() => handleRemoveSupport(supStep.id)}
                                                    />
                                                </div>
                                            </div>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    </div>

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

                <!-- Phase Selection Modal -->
                {#if showPhaseSelectModal && pendingSupport}
                    <div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" on:click={() => { showPhaseSelectModal = false; pendingSupport = null; }}>
                        <div class="bg-white rounded-lg shadow-xl p-4 min-w-[200px] max-w-[300px]" on:click|stopPropagation>
                            <h3 class="text-sm font-medium text-gray-800 mb-3">위상 선택</h3>
                            <div class="space-y-2">
                                {#each globalPhases as phase (phase.id)}
                                    <button
                                        class="w-full px-3 py-2 text-left text-sm rounded-lg border border-gray-200 hover:border-purple-400 hover:bg-purple-50 transition-colors flex items-center gap-2"
                                        on:click={() => handlePhaseSelect(phase.id)}
                                    >
                                        <span class="w-3 h-3 rounded-full" style="background-color: {phase.color}"></span>
                                        {phase.name}
                                    </button>
                                {/each}
                            </div>
                            <button
                                class="mt-3 w-full py-1.5 text-xs text-gray-500 hover:text-gray-700"
                                on:click={() => { showPhaseSelectModal = false; pendingSupport = null; }}
                            >
                                취소
                            </button>
                        </div>
                    </div>
                {/if}

                <!-- Core Step Input Modal -->
                {#if showCoreStepInputModal && selectedCoreStepDef}
                    <CoreStepInputModal
                        bind:this={coreStepInputModalRef}
                        coreStepDef={selectedCoreStepDef}
                        {projectId}
                        on:confirm={handleCoreStepConfirm}
                        on:cancel={handleCoreStepCancel}
                        on:startCapture={handleCoreStepStartCapture}
                    />
                {/if}

            {/if}
        </div>
    {/if}
</div>

<style>
    /* Support guide bounce animation - bounces horizontally to the right */
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

    /* Support guide indicator container */
    .support-guide-indicator {
        display: flex;
        align-items: center;
    }
</style>
