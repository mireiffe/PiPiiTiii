<script lang="ts">
    import { page } from "$app/stores";
    import { onMount, tick } from "svelte";
    import { marked } from "marked";
    import { goto } from "$app/navigation";
    import ViewerToolbar from "$lib/components/viewer/ViewerToolbar.svelte";
    import ViewerSidebar from "$lib/components/viewer/ViewerSidebar.svelte";
    import ViewerCanvas from "$lib/components/viewer/ViewerCanvas.svelte";
    import ViewerRightPane from "$lib/components/viewer/ViewerRightPane.svelte";
    import Toast from "$lib/components/ui/Toast.svelte";
    import {
        createEmptyWorkflowData,
        migrateToUnifiedSteps,
        type ProjectWorkflowData,
    } from "$lib/types/workflow";

    import {
        fetchProject,
        fetchSettings,
        fetchProjectSummary,
        fetchProjectWorkflows,
    } from "$lib/api/project";
    import {
        ENABLE_REPARSE_ALL,
        ENABLE_REPARSE_SLIDE,
        ENABLE_DOWNLOAD,
    } from "$lib/api/client";

    // Configure marked options
    marked.setOptions({
        breaks: true,
        gfm: true,
    });

    const projectId = $page.params.id;

    // TUTORIAL MODE - All changes are temporary and not saved
    const isTutorialMode = true;

    let project = null;
    let originalProject = null; // Store original for reset
    let currentSlideIndex = 0;
    let loading = true;
    let saving = false;
    let downloading = false;

    // Thumbnail toggle
    let useThumbnails = false;
    let loadingSettings = false;

    // Left pane toggle
    let leftPaneExpanded = true;

    // Scale factor
    let scale = 1;
    let containerWidth = 0;

    // Drag state
    let draggingId = null;
    let startX = 0;
    let startY = 0;
    let initialLeft = 0;
    let initialTop = 0;

    // Undo/Redo History
    let history = [];
    let historyIndex = -1;
    let isDirty = false;

    // Selection & Sidebar
    let selectedShapeId = null;
    let editingDescription = "";

    let otherShapesExpanded = false;

    // Always allow edit in tutorial mode
    let allowEdit = true;

    // Resizable pane
    let rightPaneWidth = 600;
    let isResizing = false;

    // Settings and summary (in-memory copies for tutorial)
    let settings = {
        summary_fields: [],
        workflow_steps: { columns: [], rows: [] },
    };
    let summaryData = {};
    let summaryDataLLM = {};
    let savingSummary = false;

    // Workflow state (in-memory for tutorial)
    let workflowData = createEmptyWorkflowData();
    let allWorkflowsData: Record<string, any> = {};
    let activeWorkflowId: string | null = null;
    let savingWorkflow = false;
    let captureMode = false;
    let captureTargetStepId = null;
    let workflowSectionRef;
    let captureOverlays = [];
    let showCaptureOverlays = true;

    // Accordion state
    let expandedSection = "workflow";

    // LLM state (disabled in tutorial)
    let generatingFieldIds = new Set();
    let generatingAll = false;
    let selectedSlideIndices = [];
    let showSlideSelector = false;

    // Version comparison
    let comparingFieldId = null;
    let editingFieldId = null;

    // Right pane fullscreen
    let rightPaneFullscreen = false;

    $: if (project && selectedSlideIndices.length === 0) {
        selectedSlideIndices = project.slides
            .slice(0, 3)
            .map((s) => s.slide_index);
    }

    $: imageShapes = allShapes.filter(
        (s) =>
            s.image_path ||
            s.type_code === "picture" ||
            s.type_code === "image" ||
            s.type_code === 13,
    );

    $: otherShapes = allShapes.filter(
        (s) =>
            !s.image_path &&
            s.type_code !== "picture" &&
            s.type_code !== "image" &&
            s.type_code !== 13,
    );

    $: if (workflowData) {
        tick().then(() => {
            if (workflowSectionRef) {
                updateCaptureOverlays();
            }
        });
    }

    onMount(async () => {
        const savedLeftPaneState = localStorage.getItem("viewer-left-pane-expanded");
        if (savedLeftPaneState !== null) {
            leftPaneExpanded = savedLeftPaneState === "true";
        }

        const calculatedWidth = Math.min(
            800,
            Math.max(600, window.innerWidth * 0.35),
        );
        rightPaneWidth = calculatedWidth;

        await loadProject();
        await loadSettings();
        await loadSummary();
        await loadWorkflow();
        window.addEventListener("resize", updateScale);
        window.addEventListener("keydown", handleKeyDown);
        return () => {
            window.removeEventListener("resize", updateScale);
            window.removeEventListener("keydown", handleKeyDown);
        };
    });

    async function loadProject() {
        try {
            const res = await fetchProject(projectId);
            if (res.ok) {
                const data = await res.json();
                // Deep clone for tutorial mode
                originalProject = JSON.parse(JSON.stringify(data));
                project = data;

                const slideParam = $page.url.searchParams.get("slide");
                if (slideParam) {
                    const idx = parseInt(slideParam) - 1;
                    if (
                        !isNaN(idx) &&
                        idx >= 0 &&
                        idx < project.slides.length
                    ) {
                        currentSlideIndex = idx;
                    }
                }

                await tick();
                updateScale();
                resetHistory();
                scrollToSlide(currentSlideIndex);

                if (canvasComponent) {
                    canvasComponent.scrollToSlide(currentSlideIndex);
                }
            }
        } catch (e) {
            console.error(e);
        } finally {
            loading = false;
        }
    }

    async function loadSettings() {
        try {
            const res = await fetchSettings();
            if (res.ok) {
                settings = await res.json();
                useThumbnails = settings.use_thumbnails || false;

                const workflows = settings.workflow_settings?.workflows || [];
                if (workflows.length > 0 && !activeWorkflowId) {
                    activeWorkflowId = workflows[0].id;
                }
            }
        } catch (e) {
            console.error("Failed to load settings", e);
        }
    }

    function toggleThumbnailView() {
        // In tutorial mode, just toggle locally without saving
        useThumbnails = !useThumbnails;
    }

    async function loadSummary() {
        try {
            const res = await fetchProjectSummary(projectId);
            if (res.ok) {
                const data = await res.json();
                summaryData = data.user || {};
                summaryDataLLM = data.llm || {};
            }
        } catch (e) {
            console.error("Failed to load summary", e);
        }
    }

    async function loadWorkflow() {
        try {
            const res = await fetchProjectWorkflows(projectId);
            if (res.ok) {
                const data = await res.json();
                const workflows = data.workflows || {};

                allWorkflowsData = {};
                for (const [wfId, wfData] of Object.entries(workflows)) {
                    if (wfData && typeof wfData === "object" && Array.isArray((wfData as any).steps)) {
                        allWorkflowsData[wfId] = migrateToUnifiedSteps(wfData as ProjectWorkflowData);
                    } else {
                        allWorkflowsData[wfId] = createEmptyWorkflowData();
                    }
                }

                if (activeWorkflowId && allWorkflowsData[activeWorkflowId]) {
                    workflowData = allWorkflowsData[activeWorkflowId];
                } else {
                    const firstWfId = Object.keys(allWorkflowsData)[0];
                    workflowData = firstWfId ? allWorkflowsData[firstWfId] : createEmptyWorkflowData();
                }
            }
        } catch (e) {
            console.error("Failed to load workflow", e);
        }
    }

    // TUTORIAL MODE: Save only to memory, not to backend
    async function saveWorkflow(newWorkflow: ProjectWorkflowData, workflowId?: string) {
        savingWorkflow = true;
        try {
            const wfId = workflowId || activeWorkflowId;
            workflowData = newWorkflow;

            if (wfId) {
                allWorkflowsData[wfId] = newWorkflow;
                allWorkflowsData = { ...allWorkflowsData };
            }

            // In tutorial mode, we don't save to backend
            // Just update local state
            console.log("[Tutorial Mode] Workflow change saved to memory only");
        } catch (e) {
            console.error("Failed to save workflow", e);
        } finally {
            savingWorkflow = false;
        }
    }

    function handleWorkflowChange(event) {
        const { workflowId, ...newWorkflow } = event.detail;
        const targetWorkflowId = workflowId || activeWorkflowId;

        if (targetWorkflowId) {
            allWorkflowsData[targetWorkflowId] = newWorkflow;
            allWorkflowsData = { ...allWorkflowsData };
        }

        workflowData = newWorkflow;
        saveWorkflow(newWorkflow, targetWorkflowId);
        updateCaptureOverlays();
    }

    function handleWorkflowTabChange(event) {
        const { workflowId } = event.detail;
        activeWorkflowId = workflowId;
        workflowData = allWorkflowsData[workflowId] || createEmptyWorkflowData();
        updateCaptureOverlays();
    }

    function handleCapture(event) {
        const capture = event.detail;
        if (workflowSectionRef && captureTargetStepId) {
            if (typeof captureTargetStepId === 'string' && captureTargetStepId.startsWith('coreStep:')) {
                workflowSectionRef.addCoreStepCapture(capture);
            } else {
                workflowSectionRef.addCapture(capture);
            }
        }
    }

    function handleToggleCaptureMode(event) {
        const { stepId } = event.detail;
        if (stepId) {
            captureMode = true;
            captureTargetStepId = stepId;
        } else {
            captureMode = false;
            captureTargetStepId = null;
        }
    }

    function updateCaptureOverlays() {
        if (workflowSectionRef && workflowSectionRef.getCaptureOverlays) {
            captureOverlays = workflowSectionRef.getCaptureOverlays();
        } else {
            captureOverlays = [];
        }
    }

    async function handleDeleteWorkflow(
        event: CustomEvent<{ workflowId: string }>,
    ) {
        const { workflowId } = event.detail;
        const emptyWorkflow = createEmptyWorkflowData();

        allWorkflowsData[workflowId] = emptyWorkflow;
        allWorkflowsData = { ...allWorkflowsData };

        // In tutorial mode, no backend save
        console.log("[Tutorial Mode] Workflow deleted from memory only");

        if (workflowId === activeWorkflowId) {
            workflowData = emptyWorkflow;
        }

        if (captureMode) {
            captureMode = false;
            captureTargetStepId = null;
        }

        captureOverlays = [];
    }

    async function handleDeleteUndefinedWorkflow(
        event: CustomEvent<{ workflowId: string }>,
    ) {
        const { workflowId } = event.detail;

        delete allWorkflowsData[workflowId];
        allWorkflowsData = { ...allWorkflowsData };

        // In tutorial mode, no backend save
        console.log("[Tutorial Mode] Undefined workflow deleted from memory only");

        const workflows = settings?.workflow_settings?.workflows || [];
        if (workflows.length > 0) {
            activeWorkflowId = workflows[0].id;
            workflowData =
                allWorkflowsData[activeWorkflowId] || createEmptyWorkflowData();
        } else {
            activeWorkflowId = null;
            workflowData = createEmptyWorkflowData();
        }

        if (captureMode) {
            captureMode = false;
            captureTargetStepId = null;
        }
        captureOverlays = [];
    }

    // Helper: get the current active workflow definition from settings
    function getActiveWorkflowDef() {
        const workflows = settings?.workflow_settings?.workflows || [];
        return workflows.find((w: any) => w.id === activeWorkflowId);
    }

    async function handleDeleteStepDefinition(
        event: CustomEvent<{ stepId: string }>,
    ) {
        const { stepId } = event.detail;
        const workflow = getActiveWorkflowDef();
        if (!workflow?.steps) return;

        workflow.steps.rows = workflow.steps.rows.filter(
            (r: any) => r.id !== stepId,
        );
        settings = { ...settings };

        // In tutorial mode, no backend save
        console.log("[Tutorial Mode] Step definition deleted from memory only");
    }

    async function handleCreateStepDefinition(
        event: CustomEvent<{ values: Record<string, string> }>,
    ) {
        const { values } = event.detail;
        const workflow = getActiveWorkflowDef();
        if (!workflow?.steps) return;

        const newId = `row_${Date.now()}`;
        const newRow = {
            id: newId,
            values: { ...values },
        };

        workflow.steps.columns.forEach((col: any) => {
            if (!(col.id in newRow.values)) {
                newRow.values[col.id] = "";
            }
        });

        workflow.steps.rows = [
            ...workflow.steps.rows,
            newRow,
        ];
        settings = { ...settings };

        // In tutorial mode, no backend save
        console.log("[Tutorial Mode] Step definition created in memory only");
    }

    async function handleUpdateStepDefinition(
        event: CustomEvent<{ stepId: string; values: Record<string, string> }>,
    ) {
        const { stepId, values } = event.detail;
        const workflow = getActiveWorkflowDef();
        if (!workflow?.steps) return;

        workflow.steps.rows = workflow.steps.rows.map((r: any) => {
            if (r.id === stepId) {
                return { ...r, values: { ...values } };
            }
            return r;
        });
        settings = { ...settings };

        // In tutorial mode, no backend save
        console.log("[Tutorial Mode] Step definition updated in memory only");
    }

    // TUTORIAL MODE: Save only to memory
    async function saveSummary() {
        savingSummary = true;
        try {
            // In tutorial mode, just trigger reactivity
            summaryData = { ...summaryData };
            console.log("[Tutorial Mode] Summary saved to memory only");
        } finally {
            savingSummary = false;
        }
    }

    // LLM generation disabled in tutorial mode
    async function generateSummaryForField(
        fieldId,
        skipSaveOnComplete = false,
    ) {
        alert("Tutorial 모드에서는 LLM 요약 생성이 비활성화되어 있습니다.");
    }

    async function generateAllSummaries() {
        alert("Tutorial 모드에서는 LLM 요약 생성이 비활성화되어 있습니다.");
    }

    function toggleCompare(fieldId) {
        if (comparingFieldId === fieldId) {
            comparingFieldId = null;
        } else {
            comparingFieldId = fieldId;
        }
    }

    function restoreLLMVersion(fieldId) {
        if (summaryDataLLM[fieldId]) {
            summaryData[fieldId] = summaryDataLLM[fieldId];
            summaryData = summaryData;
        }
    }

    function toggleSlideSelection(slideIndex) {
        if (selectedSlideIndices.includes(slideIndex)) {
            selectedSlideIndices = selectedSlideIndices.filter(
                (i) => i !== slideIndex,
            );
        } else if (selectedSlideIndices.length < 3) {
            selectedSlideIndices = [...selectedSlideIndices, slideIndex];
        }
    }

    function updateScale() {
        if (!project || !containerWidth) return;
        const slideW = project.slide_width || 960;
        scale = (containerWidth - 64) / slideW;
    }

    $: if (containerWidth && project) {
        updateScale();
    }

    $: currentSlide = project?.slides.find(
        (s) => s.slide_index === currentSlideIndex + 1,
    );

    function getAllShapes(shapes) {
        let result = [];
        for (const s of shapes) {
            result.push(s);
            if (s.children) {
                result = result.concat(getAllShapes(s.children));
            }
        }
        return result;
    }

    $: allShapes = currentSlide ? getAllShapes(currentSlide.shapes) : [];

    $: sortedShapes =
        currentSlide?.shapes.sort(
            (a, b) => (a.z_order_position || 0) - (b.z_order_position || 0),
        ) || [];

    $: selectedShape = allShapes.find((s) => s.shape_index === selectedShapeId);

    $: if (selectedShape) {
        editingDescription = selectedShape.description || "";
    } else {
        editingDescription = "";
    }

    // History Management
    function resetHistory() {
        history = [];
        historyIndex = -1;
        isDirty = false;
        if (currentSlide) {
            pushToHistory(true);
        }
    }

    function getSnapshot() {
        if (!currentSlide) return [];
        return allShapes.map((s) => ({
            shape_index: s.shape_index,
            left: s.left,
            top: s.top,
        }));
    }

    function pushToHistory(initial = false) {
        const snapshot = getSnapshot();

        if (!initial && historyIndex >= 0) {
            const current = history[historyIndex];
            const isSame = JSON.stringify(current) === JSON.stringify(snapshot);
            if (isSame) return;
        }

        if (historyIndex < history.length - 1) {
            history = history.slice(0, historyIndex + 1);
        }

        history = [...history, snapshot];
        historyIndex++;
        if (!initial) isDirty = true;
    }

    function restoreSnapshot(snapshot) {
        if (!currentSlide) return;

        const snapMap = new Map(snapshot.map((s) => [s.shape_index, s]));

        function updateShapesRecursive(shapes) {
            for (const shape of shapes) {
                const snap = snapMap.get(shape.shape_index);
                if (snap) {
                    shape.left = snap.left;
                    shape.top = snap.top;
                }
                if (shape.children) {
                    updateShapesRecursive(shape.children);
                }
            }
        }

        updateShapesRecursive(currentSlide.shapes);
        currentSlide = currentSlide;
    }

    function undo() {
        if (historyIndex > 0) {
            historyIndex--;
            restoreSnapshot(history[historyIndex]);
        }
    }

    function redo() {
        if (historyIndex < history.length - 1) {
            historyIndex++;
            restoreSnapshot(history[historyIndex]);
        }
    }

    function handleKeyDown(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "z") {
            e.preventDefault();
            undo();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "y") {
            e.preventDefault();
            redo();
        }
    }

    // Drag & Drop Logic
    function handleMouseDown(e, shape) {
        if (e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();

        selectedShapeId = shape.shape_index;
        draggingId = shape.shape_index;
        startX = e.clientX;
        startY = e.clientY;
        initialLeft = shape.left;
        initialTop = shape.top;

        window.addEventListener("mousemove", handleMouseMove);
        window.addEventListener("mouseup", handleMouseUp);
    }

    function handleCanvasMouseDown() {
        if (captureMode) return;
        selectedShapeId = null;
    }

    function handleMouseMove(e) {
        if (!draggingId || !allowEdit) return;

        const dx = (e.clientX - startX) / scale;
        const dy = (e.clientY - startY) / scale;

        const shape = allShapes.find((s) => s.shape_index === draggingId);

        if (shape) {
            shape.left = initialLeft + dx;
            shape.top = initialTop + dy;
            currentSlide = currentSlide;
        }
    }

    function handleMouseUp() {
        if (draggingId) {
            pushToHistory();
        }
        draggingId = null;
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
    }

    // TUTORIAL MODE: Save only to memory
    async function handleSaveState() {
        if (!isDirty) return;
        saving = true;
        try {
            // In tutorial mode, we don't save to backend
            isDirty = false;
            console.log("[Tutorial Mode] Shape positions saved to memory only");
        } finally {
            saving = false;
        }
    }

    function handleReset() {
        if (!confirm("모든 객체를 원래 위치로 되돌리시겠습니까?"))
            return;

        function resetRecursive(shapes) {
            for (const shape of shapes) {
                if (
                    shape.parsed_left !== undefined &&
                    shape.parsed_top !== undefined
                ) {
                    shape.left = shape.parsed_left;
                    shape.top = shape.parsed_top;
                }
                if (shape.children) {
                    resetRecursive(shape.children);
                }
            }
        }

        resetRecursive(currentSlide.shapes);
        currentSlide = currentSlide;
        pushToHistory();
    }

    // TUTORIAL MODE: Save only to memory
    async function handleSaveDescription() {
        if (!selectedShape) return;

        selectedShape.description = editingDescription;
        currentSlide = currentSlide;

        // In tutorial mode, no backend save
        console.log("[Tutorial Mode] Description saved to memory only");
    }

    // Reparse disabled in tutorial mode
    async function handleReparseAll() {
        alert("Tutorial 모드에서는 재파싱이 비활성화되어 있습니다.");
    }

    async function handleReparseSlide() {
        alert("Tutorial 모드에서는 재파싱이 비활성화되어 있습니다.");
    }

    function handleWheel(e) {
        const wheelEvent = e.detail;
        if (wheelEvent && wheelEvent.ctrlKey) {
            wheelEvent.preventDefault();
            const delta = wheelEvent.deltaY > 0 ? 0.9 : 1.1;
            scale *= delta;
        }
    }

    function scrollToSlide(index) {
        const el = document.getElementById(`slide-thumb-${index}`);
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    let canvasComponent;

    async function selectSlide(index) {
        if (isDirty) {
            if (!confirm("저장되지 않은 변경사항이 있습니다. 무시하시겠습니까?")) return;
        }
        currentSlideIndex = index;
        await tick();
        resetHistory();

        scrollToSlide(index);
        if (canvasComponent) {
            canvasComponent.scrollToSlide(index);
        }
    }

    function handleSlideInView(event) {
        const newIndex = event.detail.slideIndex;
        if (newIndex !== currentSlideIndex) {
            currentSlideIndex = newIndex;
            scrollToSlide(newIndex);
        }
    }

    // Resizable pane
    function startResize(e) {
        isResizing = true;
        e.preventDefault();
        window.addEventListener("mousemove", handleResize);
        window.addEventListener("mouseup", stopResize);
    }

    function handleResize(e) {
        if (!isResizing) return;
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth >= 300 && newWidth <= 900) {
            rightPaneWidth = newWidth;
        }
    }

    function stopResize() {
        isResizing = false;
        window.removeEventListener("mousemove", handleResize);
        window.removeEventListener("mouseup", stopResize);
    }

    // Download disabled in tutorial mode
    async function handleDownload() {
        alert("Tutorial 모드에서는 다운로드가 비활성화되어 있습니다.");
    }

    function toggleLeftPane() {
        leftPaneExpanded = !leftPaneExpanded;
        localStorage.setItem("viewer-left-pane-expanded", String(leftPaneExpanded));
    }

    function exitTutorial() {
        if (confirm("Tutorial을 종료하시겠습니까? 모든 변경사항이 사라집니다.")) {
            goto("/settings");
        }
    }
</script>

<div class="flex h-screen bg-gray-100 overflow-hidden">
    <!-- Tutorial Mode Banner -->
    <div class="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-4 py-2 flex items-center justify-between shadow-lg">
        <div class="flex items-center gap-3">
            <div class="flex items-center gap-2 bg-white/20 rounded-full px-3 py-1">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span class="font-semibold">Tutorial Mode</span>
            </div>
            <span class="text-sm text-white/80">
                모든 변경사항은 임시로만 저장됩니다. 페이지를 벗어나면 초기화됩니다.
            </span>
        </div>
        <button
            on:click={exitTutorial}
            class="bg-white/20 hover:bg-white/30 rounded-lg px-4 py-1.5 text-sm font-medium transition flex items-center gap-2"
        >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Tutorial 종료
        </button>
    </div>

    <!-- Add padding to account for banner -->
    <div class="flex w-full h-full pt-12">
        <!-- Left Sidebar -->
        <ViewerSidebar
            {project}
            {projectId}
            {currentSlideIndex}
            {useThumbnails}
            expanded={leftPaneExpanded}
            on:select={(e) => selectSlide(e.detail.index)}
            on:toggle={toggleLeftPane}
        />

        <!-- Main Canvas Area -->
        {#if !rightPaneFullscreen}
            <div
                class="flex-1 flex flex-col relative overflow-hidden"
                bind:clientWidth={containerWidth}
            >
                <ViewerToolbar
                    {historyIndex}
                    historyLength={history.length}
                    {isDirty}
                    {saving}
                    {allowEdit}
                    {useThumbnails}
                    {loadingSettings}
                    {downloading}
                    {scale}
                    {project}
                    showOverlays={showCaptureOverlays}
                    enableReparseAll={false}
                    enableReparseSlide={false}
                    enableDownload={false}
                    on:undo={undo}
                    on:redo={redo}
                    on:saveState={handleSaveState}
                    on:reset={handleReset}
                    on:toggleThumbnailView={toggleThumbnailView}
                    on:toggleOverlays={() => (showCaptureOverlays = !showCaptureOverlays)}
                    on:reparseAll={handleReparseAll}
                    on:reparseSlide={handleReparseSlide}
                    on:download={handleDownload}
                    on:zoomIn={() => (scale *= 1.1)}
                    on:zoomOut={() => (scale *= 0.9)}
                />

                <!-- Canvas with tutorial indicator border -->
                <div class="flex-1 relative">
                    <div class="absolute inset-0 border-4 border-emerald-400/50 pointer-events-none z-10 rounded-lg m-1"></div>
                    <ViewerCanvas
                        bind:this={canvasComponent}
                        {project}
                        {currentSlide}
                        {currentSlideIndex}
                        {scale}
                        {useThumbnails}
                        {projectId}
                        {sortedShapes}
                        {selectedShapeId}
                        {captureMode}
                        {captureOverlays}
                        showOverlays={showCaptureOverlays}
                        on:wheel={handleWheel}
                        on:canvasMouseDown={handleCanvasMouseDown}
                        on:shapeMouseDown={(e) =>
                            handleMouseDown(e.detail.event, e.detail.shape)}
                        on:slideInView={handleSlideInView}
                        on:capture={handleCapture}
                    />
                </div>
            </div>

            <!-- Resize Handle -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
                class="w-4 -ml-2 z-20 flex items-center justify-center cursor-col-resize group shrink-0 relative"
                on:mousedown={startResize}
            >
                <div
                    class="absolute inset-y-0 left-1/2 w-0.5 bg-gray-200 group-hover:bg-emerald-400 transition-colors"
                ></div>
                <div
                    class="w-4 h-8 bg-white border border-gray-300 rounded shadow-sm flex flex-col items-center justify-center gap-0.5 z-10 group-hover:border-emerald-400 group-hover:text-emerald-500"
                >
                    <div
                        class="w-0.5 h-0.5 bg-gray-400 rounded-full group-hover:bg-emerald-500"
                    ></div>
                    <div
                        class="w-0.5 h-0.5 bg-gray-400 rounded-full group-hover:bg-emerald-500"
                    ></div>
                    <div
                        class="w-0.5 h-0.5 bg-gray-400 rounded-full group-hover:bg-emerald-500"
                    ></div>
                </div>
            </div>
        {/if}

        <!-- Right Sidebar -->
        <ViewerRightPane
            bind:rightPaneFullscreen
            bind:rightPaneWidth
            bind:workflowSectionRef
            {expandedSection}
            {workflowData}
            {allWorkflowsData}
            {activeWorkflowId}
            {captureTargetStepId}
            {settings}
            {allowEdit}
            {savingWorkflow}
            {captureMode}
            bind:summaryData
            bind:summaryDataLLM
            {savingSummary}
            {generatingFieldIds}
            {generatingAll}
            {selectedSlideIndices}
            {comparingFieldId}
            {editingFieldId}
            {allShapes}
            {selectedShapeId}
            bind:editingDescription
            {project}
            {projectId}
            isTutorialMode={true}
            on:workflowChange={handleWorkflowChange}
            on:workflowTabChange={handleWorkflowTabChange}
            on:toggleCaptureMode={handleToggleCaptureMode}
            on:deleteWorkflow={handleDeleteWorkflow}
            on:deleteUndefinedWorkflow={handleDeleteUndefinedWorkflow}
            on:deleteStepDefinition={handleDeleteStepDefinition}
            on:createStepDefinition={handleCreateStepDefinition}
            on:updateStepDefinition={handleUpdateStepDefinition}
            on:generateAllSummaries={generateAllSummaries}
            on:toggleSlideSelection={(e) =>
                toggleSlideSelection(e.detail.slideIndex)}
            on:toggleCompare={(e) => toggleCompare(e.detail.fieldId)}
            on:generateSummaryForField={(e) =>
                generateSummaryForField(e.detail.fieldId)}
            on:restoreLLMVersion={(e) => restoreLLMVersion(e.detail.fieldId)}
            on:saveSummary={saveSummary}
            on:selectShape={(e) => (selectedShapeId = e.detail.shapeIndex)}
            on:handleSaveDescription={handleSaveDescription}
        />
    </div>
</div>

<!-- Toast Notifications -->
<Toast />
