<script lang="ts">
    import { page } from "$app/stores";
    import { onMount, tick } from "svelte";
    import { marked } from "marked";
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
        updateShapePositions,
        updateShapeDescription,
        reparseProject,
        reparseSlide,
        downloadProject,
        fetchSettings,
        updateSettings,
        fetchProjectSummary,
        updateProjectSummary,
        generateSummaryStream,
        updateProjectSummaryLLM,
        updateProjectPromptVersion,
        fetchProjectWorkflows,
        updateProjectWorkflow,
        fetchAllAttributes,
        fetchProjectAttributes,
    } from "$lib/api/project";
    import {
        ENABLE_REPARSE_ALL,
        ENABLE_REPARSE_SLIDE,
        ENABLE_DOWNLOAD,
    } from "$lib/api/client";

    // Configure marked options
    marked.setOptions({
        breaks: true, // Convert \n to <br>
        gfm: true, // GitHub Flavored Markdown
    });

    const projectId = $page.params.id;
    let project = null;
    let currentSlideIndex = 0;
    let loading = true;
    let saving = false;
    let downloading = false;

    // Thumbnail toggle
    let useThumbnails = false;
    let loadingSettings = false;

    // Left pane toggle (persisted in localStorage)
    let leftPaneExpanded = true;

    // Scale factor to fit slide in view
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

    // Get allowEdit from query parameter, default to false
    $: allowEdit = $page.url.searchParams.get("allowEdit") === "true";

    // Resizable pane
    let rightPaneWidth = 600;
    let isResizing = false;

    // Settings and summary
    let settings = {
        summary_fields: [],
        workflow_steps: { columns: [], rows: [] },
    };
    let availableAttributes: { key: string; display_name: string; attr_type: { variant: string } }[] = [];
    let projectAttributeValues: Record<string, string> = {};
    let summaryData = {}; // User version (displayed/edited)
    let summaryDataLLM = {}; // LLM-generated version (original)
    let savingSummary = false;

    // Workflow state (step-based) - supports multiple workflows
    let workflowData = createEmptyWorkflowData();  // Default/legacy workflow data
    let allWorkflowsData: Record<string, any> = {};  // { workflowId: ProjectWorkflowData }
    let activeWorkflowId: string | null = null;
    let savingWorkflow = false;
    let captureMode = false;
    let captureTargetStepId = null; // Which step is capturing
    let workflowSectionRef; // Reference to WorkflowSection component
    let captureOverlays = []; // Capture regions to display on canvas
    let showCaptureOverlays = true; // Toggle visibility of capture overlays

    // Accordion state for right pane sections
    let expandedSection = "workflow"; // 'workflow' | 'summary' | 'objects' - default is workflow

    // LLM auto-generation state
    let generatingFieldIds = new Set(); // Track multiple fields being generated in parallel
    let generatingAll = false;
    let selectedSlideIndices = [];
    let showSlideSelector = false;

    // Version comparison state
    let comparingFieldId = null; // Which field is being compared

    // Edit/Preview mode for summary fields
    let editingFieldId = null; // Which field is being edited (null = preview mode)

    // Right pane fullscreen mode
    let rightPaneFullscreen = false;

    // Initialize selected slides (first 3 by default)
    $: if (project && selectedSlideIndices.length === 0) {
        selectedSlideIndices = project.slides
            .slice(0, 3)
            .map((s) => s.slide_index);
    }

    // ?대?吏 shape ?꾪꽣留?
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

    // Update capture overlays whenever workflow changes
    $: if (workflowData) {
        // Use tick to ensure workflowSectionRef is ready
        tick().then(() => {
            if (workflowSectionRef) {
                updateCaptureOverlays();
            }
        });
    }

    onMount(async () => {
        // Load left pane state from localStorage
        const savedLeftPaneState = localStorage.getItem("viewer-left-pane-expanded");
        if (savedLeftPaneState !== null) {
            leftPaneExpanded = savedLeftPaneState === "true";
        }

        // Set rightPane width to 35% of window width (min 600px, max 800px)
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
                project = await res.json();

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

                // Scroll canvas to initial slide
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
            const [res, attrsRes, projAttrsRes] = await Promise.all([
                fetchSettings(),
                fetchAllAttributes(),
                fetchProjectAttributes(projectId),
            ]);
            if (res.ok) {
                settings = await res.json();
                useThumbnails = settings.use_thumbnails || false;

                // Set initial active workflow if workflows are defined
                const workflows = settings.workflow_settings?.workflows || [];
                if (workflows.length > 0 && !activeWorkflowId) {
                    activeWorkflowId = workflows[0].id;
                }
            }
            if (attrsRes.ok) {
                availableAttributes = await attrsRes.json();
            }
            if (projAttrsRes.ok) {
                projectAttributeValues = await projAttrsRes.json();
            }
        } catch (e) {
            console.error("Failed to load settings", e);
        }
    }

    async function toggleThumbnailView() {
        loadingSettings = true;
        try {
            // Get current settings first
            const settingsRes = await fetchSettings();
            if (settingsRes.ok) {
                const currentSettings = await settingsRes.json();
                // Toggle the value
                currentSettings.use_thumbnails = !useThumbnails;
                // Save updated settings
                const updateRes = await updateSettings(currentSettings);
                if (updateRes.ok) {
                    useThumbnails = currentSettings.use_thumbnails;
                } else {
                    console.error("Failed to update settings");
                }
            }
        } catch (e) {
            console.error("Failed to toggle thumbnail view", e);
        } finally {
            loadingSettings = false;
        }
    }

    async function loadSummary() {
        try {
            const res = await fetchProjectSummary(projectId);
            if (res.ok) {
                const data = await res.json();
                // New format: { user: {...}, llm: {...} }
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
                // data format: { workflows: { workflowId: ProjectWorkflowData, ... } }
                const workflows = data.workflows || {};

                // Populate allWorkflowsData with migration for legacy data
                allWorkflowsData = {};
                for (const [wfId, wfData] of Object.entries(workflows)) {
                    if (wfData && typeof wfData === "object" && Array.isArray((wfData as any).steps)) {
                        // Migrate legacy steps to unifiedSteps if needed
                        allWorkflowsData[wfId] = migrateToUnifiedSteps(wfData as ProjectWorkflowData);
                    } else {
                        allWorkflowsData[wfId] = createEmptyWorkflowData();
                    }
                }

                // Set current workflowData based on activeWorkflowId
                if (activeWorkflowId && allWorkflowsData[activeWorkflowId]) {
                    workflowData = allWorkflowsData[activeWorkflowId];
                } else {
                    // Fallback to first workflow or empty
                    const firstWfId = Object.keys(allWorkflowsData)[0];
                    workflowData = firstWfId ? allWorkflowsData[firstWfId] : createEmptyWorkflowData();
                }
            }
        } catch (e) {
            console.error("Failed to load workflow", e);
        }
    }

    async function saveWorkflow(newWorkflow: ProjectWorkflowData, workflowId?: string) {
        savingWorkflow = true;
        try {
            const wfId = workflowId || activeWorkflowId;
            workflowData = newWorkflow;

            // Update allWorkflowsData
            if (wfId) {
                allWorkflowsData[wfId] = newWorkflow;
                allWorkflowsData = { ...allWorkflowsData };
            }

            // Save to backend with workflow ID
            await updateProjectWorkflow(projectId, newWorkflow, wfId || undefined);
        } catch (e) {
            console.error("Failed to save workflow", e);
        } finally {
            savingWorkflow = false;
        }
    }

    function handleWorkflowChange(event) {
        const { workflowId, ...newWorkflow } = event.detail;

        // Save to the specific workflow (use provided workflowId or activeWorkflowId)
        const targetWorkflowId = workflowId || activeWorkflowId;

        if (targetWorkflowId) {
            allWorkflowsData[targetWorkflowId] = newWorkflow;
            allWorkflowsData = { ...allWorkflowsData };
        }

        workflowData = newWorkflow;
        saveWorkflow(newWorkflow, targetWorkflowId);
        // Update capture overlays after workflow change
        updateCaptureOverlays();
    }

    function handleWorkflowTabChange(event) {
        const { workflowId } = event.detail;
        activeWorkflowId = workflowId;
        // Update workflowData to current workflow's data from allWorkflowsData
        workflowData = allWorkflowsData[workflowId] || createEmptyWorkflowData();
        updateCaptureOverlays();
    }

    function handleCapture(event) {
        const capture = event.detail;
        // Add capture to the workflow section
        if (workflowSectionRef && captureTargetStepId) {
            // Check if this is a Core Step capture
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

        // Reset workflow data to empty state for the specific workflow
        const emptyWorkflow = createEmptyWorkflowData();

        // Update allWorkflowsData with empty workflow
        allWorkflowsData[workflowId] = emptyWorkflow;
        allWorkflowsData = { ...allWorkflowsData };

        // Save empty workflow to backend
        try {
            await updateProjectWorkflow(projectId, emptyWorkflow, workflowId);
        } catch (e) {
            console.error("Failed to delete workflow data", e);
        }

        // If deleting the active workflow, update current view
        if (workflowId === activeWorkflowId) {
            workflowData = emptyWorkflow;
        }

        // Turn off capture mode if it's active
        if (captureMode) {
            captureMode = false;
            captureTargetStepId = null;
        }

        // Clear capture overlays
        captureOverlays = [];
    }

    async function handleDeleteUndefinedWorkflow(
        event: CustomEvent<{ workflowId: string }>,
    ) {
        const { workflowId } = event.detail;

        // Remove workflow data from allWorkflowsData
        delete allWorkflowsData[workflowId];
        allWorkflowsData = { ...allWorkflowsData };

        // Save empty workflow to backend to remove it
        try {
            await updateProjectWorkflow(projectId, null, workflowId);
        } catch (e) {
            console.error("Failed to delete undefined workflow", e);
        }

        // Switch to first available workflow or set to null
        const workflows = settings?.workflow_settings?.workflows || [];
        if (workflows.length > 0) {
            activeWorkflowId = workflows[0].id;
            workflowData =
                allWorkflowsData[activeWorkflowId] || createEmptyWorkflowData();
        } else {
            activeWorkflowId = null;
            workflowData = createEmptyWorkflowData();
        }

        // Clear capture mode if active
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

        // Remove from the active workflow's step rows
        workflow.steps.rows = workflow.steps.rows.filter(
            (r: any) => r.id !== stepId,
        );
        settings = { ...settings };

        // Save updated settings
        try {
            const res = await updateSettings(settings);
            if (!res.ok) {
                console.error(
                    "Failed to save settings after deleting step definition",
                );
                alert("설정 저장에 실패했습니다.");
            }
        } catch (e) {
            console.error("Failed to save settings", e);
            alert("설정 저장 중 오류가 발생했습니다.");
        }
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

        // Initialize empty values for all columns that weren't provided
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

        // Save updated settings
        try {
            const res = await updateSettings(settings);
            if (!res.ok) {
                console.error(
                    "Failed to save settings after creating step definition",
                );
                alert("설정 저장에 실패했습니다.");
            }
        } catch (e) {
            console.error("Failed to save settings", e);
            alert("설정 저장 중 오류가 발생했습니다.");
        }
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

        // Save updated settings
        try {
            const res = await updateSettings(settings);
            if (!res.ok) {
                console.error(
                    "Failed to save settings after updating step definition",
                );
                alert("설정 저장에 실패했습니다.");
            }
        } catch (e) {
            console.error("Failed to save settings", e);
            alert("설정 저장 중 오류가 발생했습니다.");
        }
    }

    async function saveSummary() {
        savingSummary = true;
        try {
            const res = await updateProjectSummary(projectId, summaryData);
            if (res.ok) {
                // Success
            } else {
                alert("Failed to save summary");
            }
        } catch (e) {
            console.error("Failed to save summary", e);
            alert("Error saving summary");
        } finally {
            savingSummary = false;
        }
    }

    // LLM Auto-generation functions
    async function generateSummaryForField(
        fieldId,
        skipSaveOnComplete = false,
    ) {
        if (generatingFieldIds.has(fieldId)) return;

        generatingFieldIds.add(fieldId);
        generatingFieldIds = generatingFieldIds; // Trigger reactivity
        let generatedContent = "";

        try {
            const stream = await generateSummaryStream(
                projectId,
                fieldId,
                selectedSlideIndices,
            );
            if (!stream) {
                throw new Error("No stream returned");
            }

            const reader = stream.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                generatedContent += chunk;
                // Update user data for live display
                summaryData[fieldId] = generatedContent;
                summaryData = summaryData; // Trigger reactivity
            }

            // Save LLM version to DB
            await updateProjectSummaryLLM(projectId, fieldId, generatedContent);
            summaryDataLLM[fieldId] = generatedContent;
            summaryDataLLM = summaryDataLLM;

            // Save user version to DB (same as LLM initially) - skip if called from generateAll
            if (!skipSaveOnComplete) {
                await saveSummary();
            }
        } catch (e) {
            console.error("Failed to generate summary", e);
            if (!skipSaveOnComplete) {
                alert(`?붿빟 ?앹꽦 ?ㅽ뙣: ${e.message}`);
            }
        } finally {
            generatingFieldIds.delete(fieldId);
            generatingFieldIds = generatingFieldIds; // Trigger reactivity
        }
    }

    async function generateAllSummaries() {
        if (generatingFieldIds.size > 0 || generatingAll) return;

        generatingAll = true;
        const sortedFields = [...settings.summary_fields].sort(
            (a, b) => a.order - b.order,
        );

        // Generate all fields in parallel
        await Promise.all(
            sortedFields.map((field) =>
                generateSummaryForField(field.id, true),
            ),
        );

        generatingAll = false;
        summaryDataLLM = summaryDataLLM;
        await saveSummary();

        // Update prompt version after all summaries are generated
        try {
            await updateProjectPromptVersion(projectId);
        } catch (e) {
            console.error("Failed to update prompt version", e);
        }
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
            saveSummary();
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

    // Reactively update scale when container width changes (e.g., when resizing right pane)
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

    // Actions
    async function handleSaveState() {
        if (!isDirty) return;
        saving = true;
        try {
            const updates = allShapes.map((s) => ({
                slide_index: currentSlide.slide_index,
                shape_index: s.shape_index,
                left: s.left,
                top: s.top,
            }));

            const res = await updateShapePositions(projectId, updates);

            if (res.ok) {
                isDirty = false;
            } else {
                alert("Failed to save state.");
            }
        } catch (e) {
            console.error("Failed to save state", e);
            alert("Error saving state.");
        } finally {
            saving = false;
        }
    }

    function handleReset() {
        if (!confirm("Revert all objects to their original parsed positions?"))
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

    async function handleSaveDescription() {
        if (!selectedShape) return;

        selectedShape.description = editingDescription;
        currentSlide = currentSlide;

        try {
            const res = await updateShapeDescription(projectId, {
                slide_index: currentSlide.slide_index,
                shape_index: selectedShape.shape_index,
                description: editingDescription,
            });
            if (!res.ok) {
                console.error("Failed to save description");
                alert("Failed to save description");
            }
        } catch (e) {
            console.error(e);
            alert("Error saving description");
        }
    }

    async function handleReparseAll() {
        if (
            !confirm(
                "Are you sure you want to reparse ALL slides? This will reset all changes.",
            )
        )
            return;

        loading = true;
        try {
            const res = await reparseProject(projectId);

            if (res.ok) {
                await loadProject();
                alert("Reparsing all complete!");
            } else {
                alert("Reparsing all failed.");
            }
        } catch (e) {
            console.error(e);
            alert("Error during reparse all.");
        } finally {
            loading = false;
        }
    }

    async function handleReparseSlide() {
        if (!currentSlide) return;
        if (
            !confirm(
                `Are you sure you want to reparse Slide ${currentSlide.slide_index}?`,
            )
        )
            return;

        loading = true;
        try {
            const res = await reparseSlide(projectId, currentSlide.slide_index);

            if (res.ok) {
                const data = await res.json();
                if (project && data.slide) {
                    const idx = project.slides.findIndex(
                        (s) => s.slide_index === data.slide.slide_index,
                    );
                    if (idx !== -1) {
                        project.slides[idx] = data.slide;
                        project = project;
                        resetHistory();
                    }
                }
                alert("Slide reparsed!");
            } else {
                alert("Slide reparse failed.");
            }
        } catch (e) {
            console.error(e);
            alert("Error during slide reparse.");
        } finally {
            loading = false;
        }
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
            if (!confirm("You have unsaved changes. Discard them?")) return;
        }
        currentSlideIndex = index;
        await tick();
        resetHistory();

        // Scroll both sidebar and canvas
        scrollToSlide(index);
        if (canvasComponent) {
            canvasComponent.scrollToSlide(index);
        }
    }

    // Handle slide coming into view in canvas
    function handleSlideInView(event) {
        const newIndex = event.detail.slideIndex;
        if (newIndex !== currentSlideIndex) {
            currentSlideIndex = newIndex;
            // Scroll sidebar to match
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

    async function handleDownload() {
        if (downloading) return;
        downloading = true;
        try {
            await downloadProject(projectId);
        } catch (e) {
            console.error(e);
            alert("Failed to download PPT");
        } finally {
            downloading = false;
        }
    }

    function toggleLeftPane() {
        leftPaneExpanded = !leftPaneExpanded;
        localStorage.setItem("viewer-left-pane-expanded", String(leftPaneExpanded));
    }
</script>

<div class="flex h-screen bg-gray-100 overflow-hidden">
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

    <!-- Right Pane (Order swapped in DOM but visually controlled by flex and order if needed, but here it is absolute or flex item? It's flex-col layout) -->
    <!-- Wait, ViewerRightPane is likely at the end of the file. Let me check the end of file -->

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
                enableReparseAll={ENABLE_REPARSE_ALL}
                enableReparseSlide={ENABLE_REPARSE_SLIDE}
                enableDownload={ENABLE_DOWNLOAD}
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

            <!-- Canvas -->
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

        <!-- Resize Handle -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div
            class="w-4 -ml-2 z-20 flex items-center justify-center cursor-col-resize group shrink-0 relative"
            on:mousedown={startResize}
        >
            <div
                class="absolute inset-y-0 left-1/2 w-0.5 bg-gray-200 group-hover:bg-blue-400 transition-colors"
            ></div>
            <div
                class="w-4 h-8 bg-white border border-gray-300 rounded shadow-sm flex flex-col items-center justify-center gap-0.5 z-10 group-hover:border-blue-400 group-hover:text-blue-500"
            >
                <div
                    class="w-0.5 h-0.5 bg-gray-400 rounded-full group-hover:bg-blue-500"
                ></div>
                <div
                    class="w-0.5 h-0.5 bg-gray-400 rounded-full group-hover:bg-blue-500"
                ></div>
                <div
                    class="w-0.5 h-0.5 bg-gray-400 rounded-full group-hover:bg-blue-500"
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
        {availableAttributes}
        {projectAttributeValues}
        slideWidth={project?.slide_width || 960}
        slideHeight={project?.slide_height || 540}
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

<!-- Toast Notifications -->
<Toast />
