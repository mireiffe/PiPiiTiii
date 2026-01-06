<script>
    import { page } from "$app/stores";
    import { onMount, tick } from "svelte";
    import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
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
    } from "$lib/api/project";

    const projectId = $page.params.id;
    let project = null;
    let currentSlideIndex = 0;
    let loading = true;
    let saving = false;
    let downloading = false;

    // Thumbnail toggle
    let useThumbnails = false;
    let loadingSettings = false;

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
    let rightPaneWidth = 400;
    let isResizing = false;

    // Settings and summary
    let settings = { summary_fields: [] };
    let summaryData = {};  // User version (displayed/edited)
    let summaryDataLLM = {};  // LLM-generated version (original)
    let savingSummary = false;

    // LLM auto-generation state
    let generatingFieldId = null;
    let generatingAll = false;
    let selectedSlideIndices = [];
    let showSlideSelector = false;

    // Version comparison state
    let comparingFieldId = null;  // Which field is being compared

    // Initialize selected slides (first 3 by default)
    $: if (project && selectedSlideIndices.length === 0) {
        selectedSlideIndices = project.slides
            .slice(0, 3)
            .map((s) => s.slide_index);
    }

    // 이미지 shape 필터링
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

    onMount(async () => {
        await loadProject();
        await loadSettings();
        await loadSummary();
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
    async function generateSummaryForField(fieldId) {
        if (generatingFieldId || generatingAll) return;

        generatingFieldId = fieldId;
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

            // Save user version to DB (same as LLM initially)
            await saveSummary();
        } catch (e) {
            console.error("Failed to generate summary", e);
            alert(`요약 생성 실패: ${e.message}`);
        } finally {
            generatingFieldId = null;
        }
    }

    async function generateAllSummaries() {
        if (generatingFieldId || generatingAll) return;

        generatingAll = true;
        const sortedFields = [...settings.summary_fields].sort(
            (a, b) => a.order - b.order,
        );

        for (const field of sortedFields) {
            generatingFieldId = field.id;
            let generatedContent = "";

            try {
                const stream = await generateSummaryStream(
                    projectId,
                    field.id,
                    selectedSlideIndices,
                );
                if (!stream) continue;

                const reader = stream.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    generatedContent += chunk;
                    summaryData[field.id] = generatedContent;
                    summaryData = summaryData;
                }

                // Save LLM version
                await updateProjectSummaryLLM(projectId, field.id, generatedContent);
                summaryDataLLM[field.id] = generatedContent;
            } catch (e) {
                console.error(
                    `Failed to generate summary for ${field.name}`,
                    e,
                );
            }
        }

        generatingFieldId = null;
        generatingAll = false;
        summaryDataLLM = summaryDataLLM;
        await saveSummary();
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
        if (e.ctrlKey) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            scale *= delta;
        }
    }

    function scrollToSlide(index) {
        const el = document.getElementById(`slide-thumb-${index}`);
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    async function selectSlide(index) {
        if (isDirty) {
            if (!confirm("You have unsaved changes. Discard them?")) return;
        }
        currentSlideIndex = index;
        await tick();
        resetHistory();
        scrollToSlide(index);
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
        if (newWidth >= 300 && newWidth <= 800) {
            rightPaneWidth = newWidth;
        }
    }

    function stopResize() {
        isResizing = false;
        window.removeEventListener("mousemove", handleResize);
        window.removeEventListener("mouseup", stopResize);
    }
</script>

<div class="flex h-screen bg-gray-100 overflow-hidden">
    <!-- Left Sidebar (Slides) -->
    <div class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div class="p-4 border-b border-gray-200">
            <h1 class="font-bold text-gray-800 truncate">
                {project?.ppt_path.split("\\").pop() || "Loading..."}
            </h1>
            <a href="/" class="text-xs text-blue-600 hover:underline"
                >← Back to Dashboard</a
            >
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-4">
            {#if project}
                {#each project.slides as slide, i}
                    <button
                        id={`slide-thumb-${i}`}
                        class="w-full text-left p-2 rounded hover:bg-gray-50 transition {currentSlideIndex ===
                        i
                            ? 'ring-2 ring-blue-500 bg-blue-50'
                            : ''}"
                        on:click={() => selectSlide(i)}
                    >
                        <div
                            class="aspect-video bg-white border border-gray-200 mb-1 relative overflow-hidden"
                        >
                            {#if useThumbnails}
                                <img
                                    src={`/api/results/${projectId}/thumbnails/slide_${slide.slide_index.toString().padStart(3, "0")}_thumb.png`}
                                    alt={`Slide ${slide.slide_index} thumbnail`}
                                    class="w-full h-full object-contain"
                                    on:error={(e) => {
                                        console.warn(
                                            `Thumbnail not found for slide ${slide.slide_index}`,
                                        );
                                        e.target.style.display = "none";
                                    }}
                                />
                            {:else}
                                <div
                                    class="absolute top-0 left-0 origin-top-left pointer-events-none"
                                    style="transform: scale({200 /
                                        (project.slide_width ||
                                            960)}); width: {project.slide_width}px; height: {project.slide_height}px;"
                                >
                                    {#each slide.shapes.sort((a, b) => (a.z_order_position || 0) - (b.z_order_position || 0)) as shape}
                                        <div class="absolute top-0 left-0">
                                            <ShapeRenderer
                                                {shape}
                                                {projectId}
                                            />
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                        <span class="text-sm text-gray-600 font-medium"
                            >Slide {slide.slide_index}</span
                        >
                    </button>
                {/each}
            {/if}
        </div>
    </div>

    <!-- Main Canvas Area -->
    <div
        class="flex-1 flex flex-col relative overflow-hidden"
        bind:clientWidth={containerWidth}
    >
        <!-- Toolbar -->
        <div
            class="min-h-[3.5rem] h-auto bg-white border-b border-gray-200 flex flex-wrap items-center justify-between px-4 py-2 gap-2 shrink-0 z-10"
        >
            {#if allowEdit}
                <div class="flex items-center space-x-2">
                    <button
                        class="p-2 hover:bg-gray-100 rounded disabled:opacity-50"
                        disabled={historyIndex <= 0}
                        on:click={undo}
                        title="Undo (Ctrl+Z)"
                    >
                        ↩️ Undo
                    </button>
                    <button
                        class="p-2 hover:bg-gray-100 rounded disabled:opacity-50"
                        disabled={historyIndex >= history.length - 1}
                        on:click={redo}
                        title="Redo (Ctrl+Y)"
                    >
                        ↪️ Redo
                    </button>
                    <div class="w-px h-6 bg-gray-300 mx-2"></div>
                    <button
                        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm font-medium transition disabled:bg-blue-300"
                        disabled={!isDirty || saving}
                        on:click={handleSaveState}
                    >
                        {saving ? "Saving..." : "Save State"}
                    </button>
                    <button
                        class="text-gray-600 hover:bg-gray-100 px-3 py-1.5 rounded text-sm transition"
                        on:click={handleReset}
                    >
                        Reset to Original
                    </button>
                </div>
            {:else}
                <div class="w-2"></div>
            {/if}

            <div class="flex items-center space-x-2 shrink-0">
                <button
                    on:click={toggleThumbnailView}
                    disabled={loadingSettings}
                    class="bg-purple-100 hover:bg-purple-200 text-purple-700 px-3 py-1 rounded text-sm transition whitespace-nowrap flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                    title={useThumbnails
                        ? "렌더링 보기로 전환"
                        : "썸네일 보기로 전환"}
                >
                    {#if useThumbnails}
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
                                d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z"
                            />
                        </svg>
                        <span>썸네일</span>
                    {:else}
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
                                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                        </svg>
                        <span>렌더링</span>
                    {/if}
                </button>
                <button
                    class="bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded text-sm transition whitespace-nowrap"
                    on:click={handleReparseAll}
                >
                    Reparse All
                </button>
                <button
                    class="bg-blue-100 hover:bg-blue-200 text-blue-700 px-3 py-1 rounded text-sm transition whitespace-nowrap"
                    on:click={handleReparseSlide}
                >
                    Reparse Slide
                </button>
                <button
                    class="bg-green-100 hover:bg-green-200 text-green-700 px-3 py-1 rounded text-sm transition whitespace-nowrap flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                    on:click={async () => {
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
                    }}
                    disabled={downloading}
                >
                    {#if downloading}
                        <svg
                            class="animate-spin h-3 w-3 text-green-700"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                        >
                            <circle
                                class="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="4"
                            ></circle>
                            <path
                                class="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                        </svg>
                        <span>Generating...</span>
                    {:else}
                        <span>Download</span>
                    {/if}
                </button>
                <div class="w-px h-4 bg-gray-300 mx-2"></div>
                <button
                    class="p-1 hover:bg-gray-100 rounded w-8 h-8 flex items-center justify-center"
                    on:click={() => (scale *= 1.1)}>+</button
                >
                <span class="text-xs text-gray-500 w-12 text-center"
                    >{Math.round(scale * 100)}%</span
                >
                <button
                    class="p-1 hover:bg-gray-100 rounded w-8 h-8 flex items-center justify-center"
                    on:click={() => (scale *= 0.9)}>-</button
                >
            </div>
        </div>

        <!-- Canvas -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div
            class="flex-1 overflow-auto bg-gray-100 p-8 flex items-center justify-center"
            on:wheel={handleWheel}
            on:mousedown={() => (selectedShapeId = null)}
        >
            {#if currentSlide}
                <div
                    style={`
                        width: ${project.slide_width * scale}px;
                        height: ${project.slide_height * scale}px;
                    `}
                >
                    <div
                        class="bg-white shadow-lg relative transition-transform duration-200 ease-out origin-top-left"
                        style={`
                            width: ${project.slide_width}px;
                            height: ${project.slide_height}px;
                            transform: scale(${scale});
                        `}
                    >
                        {#if useThumbnails}
                            <img
                                src={`/api/results/${projectId}/thumbnails/slide_${currentSlide.slide_index.toString().padStart(3, "0")}_thumb.png`}
                                alt={`Slide ${currentSlide.slide_index} thumbnail`}
                                class="w-full h-full object-contain"
                                on:error={(e) => {
                                    console.warn(
                                        `Thumbnail not found for slide ${currentSlide.slide_index}, falling back to rendering`,
                                    );
                                    e.target.style.display = "none";
                                }}
                            />
                        {:else}
                            {#each sortedShapes as shape (shape.shape_index)}
                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                <div
                                    on:mousedown={(e) =>
                                        handleMouseDown(e, shape)}
                                    class="absolute"
                                    style={`
                                        left: 0;
                                        top: 0;
                                        width: 0;
                                        height: 0;
                                        cursor: grab;
                                    `}
                                >
                                    <ShapeRenderer
                                        {shape}
                                        {projectId}
                                        highlight={selectedShapeId ===
                                            shape.shape_index}
                                    />
                                </div>
                            {/each}
                        {/if}
                    </div>
                </div>
            {/if}
        </div>
    </div>

    <!-- Resize Handle -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
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

    <!-- Right Sidebar -->
    <div
        class="bg-white border-l border-gray-200 flex flex-col shrink-0"
        style="width: {rightPaneWidth}px;"
    >
        <div class="p-4 border-b border-gray-200">
            <h2 class="font-bold text-gray-800">프로젝트 정보</h2>
        </div>

        <div class="flex-1 overflow-y-auto min-h-0">
            <!-- Summary Fields -->
            <div class="p-4 space-y-4">
                <div class="flex items-center justify-between">
                    <h3
                        class="text-sm font-bold text-gray-800 flex items-center gap-2"
                    >
                        <span>📄 요약 정보</span>
                        {#if savingSummary}
                            <span
                                class="text-xs font-normal text-gray-400 animate-pulse"
                                >저장 중...</span
                            >
                        {/if}
                    </h3>
                    {#if settings.summary_fields && settings.summary_fields.length > 0}
                        <button
                            class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-600 px-3 py-1.5 rounded-full transition flex items-center gap-1.5 font-medium disabled:opacity-50"
                            on:click={generateAllSummaries}
                            disabled={generatingFieldId || generatingAll}
                            title="모든 요약 필드를 LLM으로 자동 생성"
                        >
                            {#if generatingAll}
                                <svg
                                    class="animate-spin h-3 w-3"
                                    viewBox="0 0 24 24"
                                >
                                    <circle
                                        class="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        stroke-width="4"
                                        fill="none"
                                    ></circle>
                                    <path
                                        class="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                    ></path>
                                </svg>
                                <span>생성 중...</span>
                            {:else}
                                <svg
                                    class="w-3 h-3"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M13 10V3L4 14h7v7l9-11h-7z"
                                    /></svg
                                >
                                <span>전체 자동 생성</span>
                            {/if}
                        </button>
                    {/if}
                </div>

                <!-- Slide Selection for Summary -->
                {#if settings.summary_fields && settings.summary_fields.length > 0}
                    <div
                        class="bg-gray-50 rounded-lg border border-gray-100 overflow-hidden"
                    >
                        <button
                            class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-100 transition-colors"
                            on:click={() =>
                                (showSlideSelector = !showSlideSelector)}
                        >
                            <div
                                class="flex items-center gap-2 overflow-hidden"
                            >
                                <span
                                    class="text-xs font-semibold text-gray-500 whitespace-nowrap"
                                    >참조 슬라이드:</span
                                >
                                <div class="flex gap-1 overflow-hidden">
                                    {#if selectedSlideIndices.length === 0}
                                        <span
                                            class="text-xs text-gray-400 italic"
                                            >선택 없음</span
                                        >
                                    {:else}
                                        {#each selectedSlideIndices.sort((a, b) => a - b) as idx}
                                            <span
                                                class="bg-white border border-gray-200 text-gray-600 text-[10px] px-1.5 py-0.5 rounded shadow-sm"
                                            >
                                                #{idx}
                                            </span>
                                        {/each}
                                    {/if}
                                </div>
                            </div>
                            <svg
                                class="w-4 h-4 text-gray-400 transform transition-transform {showSlideSelector
                                    ? 'rotate-180'
                                    : ''}"
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

                        {#if showSlideSelector}
                            <div
                                class="p-3 bg-white border-t border-gray-100 animate-in fade-in slide-in-from-top-1 duration-200"
                            >
                                <div
                                    class="flex items-center justify-between mb-2"
                                >
                                    <p class="text-[10px] text-gray-400">
                                        최대 3개까지 선택하여 요약에 참조합니다.
                                    </p>
                                </div>
                                <div
                                    class="grid grid-cols-5 gap-1 max-h-32 overflow-y-auto p-1"
                                >
                                    {#if project}
                                        {#each project.slides as slide}
                                            <button
                                                class="text-xs p-1.5 rounded border transition flex flex-col items-center justify-center gap-1 {selectedSlideIndices.includes(
                                                    slide.slide_index,
                                                )
                                                    ? 'bg-blue-50 text-blue-600 border-blue-200 ring-1 ring-blue-100'
                                                    : 'bg-white text-gray-500 border-gray-100 hover:border-gray-300 hover:bg-gray-50'}
                                                        {selectedSlideIndices.length >=
                                                    3 &&
                                                !selectedSlideIndices.includes(
                                                    slide.slide_index,
                                                )
                                                    ? 'opacity-40 cursor-not-allowed'
                                                    : ''}"
                                                on:click={() =>
                                                    toggleSlideSelection(
                                                        slide.slide_index,
                                                    )}
                                                disabled={selectedSlideIndices.length >=
                                                    3 &&
                                                    !selectedSlideIndices.includes(
                                                        slide.slide_index,
                                                    )}
                                            >
                                                <span class="font-medium"
                                                    >{slide.slide_index}</span
                                                >
                                            </button>
                                        {/each}
                                    {/if}
                                </div>
                            </div>
                        {/if}
                    </div>
                {/if}

                {#if settings.summary_fields && settings.summary_fields.length > 0}
                    <div class="space-y-4">
                        {#each settings.summary_fields.sort((a, b) => a.order - b.order) as field}
                            <div class="group">
                                <div
                                    class="flex items-center justify-between mb-1.5 px-0.5"
                                >
                                    <div class="flex items-center gap-2">
                                        <label
                                            class="text-xs font-semibold text-gray-600 uppercase tracking-wider"
                                        >
                                            {field.name}
                                        </label>
                                        <!-- Compare button - shows when LLM version exists and differs from user version -->
                                        {#if summaryDataLLM[field.id] && summaryDataLLM[field.id] !== summaryData[field.id]}
                                            <button
                                                class="text-[9px] px-1.5 py-0.5 rounded-full transition-all flex items-center gap-0.5 {comparingFieldId === field.id
                                                    ? 'bg-amber-100 text-amber-700 border border-amber-200'
                                                    : 'bg-gray-100 text-gray-500 hover:bg-amber-50 hover:text-amber-600 border border-transparent hover:border-amber-200'}"
                                                on:click={() => toggleCompare(field.id)}
                                                title={comparingFieldId === field.id ? "비교 닫기" : "LLM 버전과 비교"}
                                            >
                                                <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                </svg>
                                                <span>{comparingFieldId === field.id ? "닫기" : "비교"}</span>
                                            </button>
                                        {/if}
                                    </div>
                                    <button
                                        class="text-[10px] text-gray-400 hover:text-indigo-600 opacity-0 group-hover:opacity-100 transition-all flex items-center gap-1"
                                        on:click={() =>
                                            generateSummaryForField(field.id)}
                                        disabled={generatingFieldId ||
                                            generatingAll}
                                        title="이 항목만 재생성"
                                    >
                                        {#if generatingFieldId === field.id}
                                            <span class="text-indigo-500"
                                                >생성 중...</span
                                            >
                                        {:else}
                                            <svg
                                                class="w-3 h-3"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                                ><path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    stroke-width="2"
                                                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                                /></svg
                                            >
                                            <span>재생성</span>
                                        {/if}
                                    </button>
                                </div>

                                <!-- Comparison View -->
                                {#if comparingFieldId === field.id && summaryDataLLM[field.id]}
                                    <div class="mb-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                                        <div class="flex items-center justify-between mb-1.5">
                                            <span class="text-[10px] font-medium text-amber-700">LLM 생성 버전</span>
                                            <button
                                                class="text-[9px] px-2 py-0.5 bg-amber-100 hover:bg-amber-200 text-amber-700 rounded transition-colors flex items-center gap-1"
                                                on:click={() => restoreLLMVersion(field.id)}
                                                title="LLM 버전으로 되돌리기"
                                            >
                                                <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                </svg>
                                                <span>이 버전으로 복원</span>
                                            </button>
                                        </div>
                                        <div class="text-xs text-amber-900/80 whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">
                                            {summaryDataLLM[field.id]}
                                        </div>
                                    </div>
                                {/if}

                                <div class="relative">
                                    <textarea
                                        class="w-full text-sm leading-relaxed p-3 border border-gray-200 rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all placeholder-gray-300 resize-y min-h-[80px] hover:border-gray-300 {generatingFieldId ===
                                        field.id
                                            ? 'bg-indigo-50/30'
                                            : 'bg-white'}"
                                        rows="3"
                                        placeholder="{field.name}에 대한 내용을 입력하세요..."
                                        bind:value={summaryData[field.id]}
                                        on:blur={saveSummary}
                                        disabled={generatingFieldId ===
                                            field.id}
                                    ></textarea>
                                    {#if generatingFieldId === field.id}
                                        <div
                                            class="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-[1px] rounded-lg"
                                        >
                                            <div
                                                class="flex items-center gap-2 text-indigo-600 text-sm font-medium"
                                            >
                                                <svg
                                                    class="animate-spin h-4 w-4"
                                                    viewBox="0 0 24 24"
                                                >
                                                    <circle
                                                        class="opacity-25"
                                                        cx="12"
                                                        cy="12"
                                                        r="10"
                                                        stroke="currentColor"
                                                        stroke-width="4"
                                                        fill="none"
                                                    ></circle>
                                                    <path
                                                        class="opacity-75"
                                                        fill="currentColor"
                                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                                    ></path>
                                                </svg>
                                                작성 중...
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <div
                        class="text-center py-8 bg-gray-50 rounded-lg border border-dashed border-gray-200"
                    >
                        <p class="text-sm text-gray-500 mb-1">
                            정보 필드가 없습니다.
                        </p>
                        <p class="text-xs text-gray-400">
                            설정에서 요약 필드를 추가해주세요.
                        </p>
                    </div>
                {/if}
            </div>
        </div>

        <!-- Object List (Bottom Sticky) -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div
            class="shrink-0 border-t border-gray-200 bg-white transition-all duration-300 ease-in-out flex flex-col"
            style="max-height: {otherShapesExpanded ? '50%' : 'auto'};"
        >
            <div
                class="w-full flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 {otherShapesExpanded
                    ? 'bg-gray-50'
                    : ''}"
                on:click={() => (otherShapesExpanded = !otherShapesExpanded)}
            >
                <div class="flex items-center gap-2">
                    <span class="font-bold text-gray-700">📦 객체 목록</span>
                    <span
                        class="bg-gray-100 text-gray-500 text-xs px-2 py-0.5 rounded-full font-mono"
                        >{allShapes.length}</span
                    >
                </div>
                <span
                    class="text-gray-400 transition-transform duration-300"
                    class:rotate-180={otherShapesExpanded}
                >
                    ▲
                </span>
            </div>

            {#if otherShapesExpanded}
                <div class="overflow-y-auto flex-1 p-0 min-h-0 bg-gray-50/50">
                    {#if allShapes.length === 0}
                        <div
                            class="p-8 text-gray-400 text-sm text-center flex flex-col items-center gap-2"
                        >
                            <span class="text-2xl">📭</span>
                            <span>발견된 객체가 없습니다</span>
                        </div>
                    {:else}
                        <div class="p-2 space-y-4">
                            <!-- 이미지 객체 -->
                            {#if imageShapes.length > 0}
                                <div>
                                    <div
                                        class="flex items-center gap-2 px-2 py-1 mb-1"
                                    >
                                        <span
                                            class="text-xs font-bold text-orange-600 uppercase tracking-wide"
                                            >이미지 assets</span
                                        >
                                        <span class="h-px flex-1 bg-orange-200"
                                        ></span>
                                    </div>
                                    <ul class="space-y-1">
                                        {#each imageShapes as shape}
                                            <li>
                                                <button
                                                    class="w-full text-left p-2 rounded-lg text-sm flex items-start gap-3 transition-all border {selectedShapeId ===
                                                    shape.shape_index
                                                        ? 'bg-orange-50 border-orange-200 shadow-sm ring-1 ring-orange-200'
                                                        : 'bg-white border-transparent hover:border-orange-200 hover:shadow-sm'}"
                                                    on:click={() =>
                                                        (selectedShapeId =
                                                            shape.shape_index)}
                                                >
                                                    {#if shape.description}
                                                        <div
                                                            class="mt-0.5 text-green-500"
                                                            title="설명 완료"
                                                        >
                                                            ✅
                                                        </div>
                                                    {:else}
                                                        <div
                                                            class="mt-0.5 text-orange-400 animate-pulse"
                                                            title="설명 필요"
                                                        >
                                                            ⚠️
                                                        </div>
                                                    {/if}
                                                    <div class="flex-1 min-w-0">
                                                        <div
                                                            class="font-medium text-gray-700 truncate"
                                                            title={shape.name}
                                                        >
                                                            {shape.name}
                                                        </div>
                                                        {#if shape.description}
                                                            <div
                                                                class="text-xs text-gray-400 truncate mt-0.5"
                                                            >
                                                                {shape.description}
                                                            </div>
                                                        {:else}
                                                            <div
                                                                class="text-xs text-orange-400 mt-0.5"
                                                            >
                                                                설명을
                                                                입력해주세요
                                                            </div>
                                                        {/if}
                                                    </div>
                                                </button>
                                            </li>
                                        {/each}
                                    </ul>
                                </div>
                            {/if}

                            <!-- 기타 객체 -->
                            {#if otherShapes.length > 0}
                                <div>
                                    <div
                                        class="flex items-center gap-2 px-2 py-1 mb-1"
                                    >
                                        <span
                                            class="text-xs font-bold text-gray-500 uppercase tracking-wide"
                                            >기타 객체</span
                                        >
                                        <span class="h-px flex-1 bg-gray-200"
                                        ></span>
                                    </div>
                                    <ul class="space-y-1">
                                        {#each otherShapes as shape}
                                            <li>
                                                <button
                                                    class="w-full text-left p-2 rounded-lg text-sm flex items-start gap-3 transition-all border {selectedShapeId ===
                                                    shape.shape_index
                                                        ? 'bg-blue-50 border-blue-200 shadow-sm ring-1 ring-blue-200'
                                                        : 'bg-white border-transparent hover:border-gray-200 hover:shadow-sm'}"
                                                    on:click={() =>
                                                        (selectedShapeId =
                                                            shape.shape_index)}
                                                >
                                                    <div
                                                        class="mt-0.5 text-gray-400"
                                                    >
                                                        🔹
                                                    </div>
                                                    <div class="flex-1 min-w-0">
                                                        <div
                                                            class="font-medium text-gray-700 truncate"
                                                            title={shape.name}
                                                        >
                                                            {shape.name}
                                                        </div>
                                                        {#if shape.description}
                                                            <div
                                                                class="text-xs text-gray-400 truncate mt-0.5"
                                                            >
                                                                {shape.description}
                                                            </div>
                                                        {/if}
                                                    </div>
                                                    {#if shape.description}
                                                        <div
                                                            class="mt-0.5 text-gray-300"
                                                            title="설명 있음"
                                                        >
                                                            📝
                                                        </div>
                                                    {/if}
                                                </button>
                                            </li>
                                        {/each}
                                    </ul>
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>

                <!-- Description Editor (Sticky at bottom of Object List) -->
                {#if selectedShape}
                    <div
                        class="p-3 bg-white border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] z-10"
                    >
                        <div class="flex items-center justify-between mb-2">
                            <span
                                class="text-xs font-bold text-gray-500 uppercase"
                                >Description</span
                            >
                            <span
                                class="text-xs text-gray-400 max-w-[150px] truncate"
                                >{selectedShape.name}</span
                            >
                        </div>
                        <div class="relative">
                            <textarea
                                class="w-full text-sm p-2 pr-10 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none transition-shadow"
                                rows="2"
                                placeholder="객체에 대한 설명을 입력하세요..."
                                bind:value={editingDescription}
                                on:keydown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSaveDescription();
                                    }
                                }}
                            ></textarea>
                            <button
                                class="absolute right-2 bottom-2 p-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm transition-transform active:scale-95"
                                on:click={handleSaveDescription}
                                title="저장 (Enter)"
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M5 13l4 4L19 7"
                                    /></svg
                                >
                            </button>
                        </div>
                    </div>
                {/if}
            {/if}
        </div>
    </div>
</div>
