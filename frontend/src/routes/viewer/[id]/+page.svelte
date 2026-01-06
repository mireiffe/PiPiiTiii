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
    $: allowEdit = $page.url.searchParams.get('allowEdit') === 'true';

    // Resizable pane
    let rightPaneWidth = 400;
    let isResizing = false;

    // Settings and summary
    let settings = { summary_fields: [] };
    let summaryData = {};
    let savingSummary = false;

    // LLM auto-generation state
    let generatingFieldId = null;
    let generatingAll = false;
    let selectedSlideIndices = [];
    let showSlideSelector = false;

    // Initialize selected slides (first 3 by default)
    $: if (project && selectedSlideIndices.length === 0) {
        selectedSlideIndices = project.slides.slice(0, 3).map(s => s.slide_index);
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
                summaryData = await res.json();
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
        summaryData[fieldId] = '';  // Clear existing content

        try {
            const stream = await generateSummaryStream(projectId, fieldId, selectedSlideIndices);
            if (!stream) {
                throw new Error("No stream returned");
            }

            const reader = stream.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                summaryData[fieldId] = (summaryData[fieldId] || '') + chunk;
                summaryData = summaryData;  // Trigger reactivity
            }

            // Save to DB after generation completes
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
        const sortedFields = [...settings.summary_fields].sort((a, b) => a.order - b.order);

        for (const field of sortedFields) {
            generatingFieldId = field.id;
            summaryData[field.id] = '';

            try {
                const stream = await generateSummaryStream(projectId, field.id, selectedSlideIndices);
                if (!stream) continue;

                const reader = stream.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    summaryData[field.id] = (summaryData[field.id] || '') + chunk;
                    summaryData = summaryData;
                }
            } catch (e) {
                console.error(`Failed to generate summary for ${field.name}`, e);
            }
        }

        generatingFieldId = null;
        generatingAll = false;
        await saveSummary();
    }

    function toggleSlideSelection(slideIndex) {
        if (selectedSlideIndices.includes(slideIndex)) {
            selectedSlideIndices = selectedSlideIndices.filter(i => i !== slideIndex);
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
                                    src={`/api/results/${projectId}/thumbnails/slide_${slide.slide_index.toString().padStart(3, '0')}_thumb.png`}
                                    alt={`Slide ${slide.slide_index} thumbnail`}
                                    class="w-full h-full object-contain"
                                    on:error={(e) => {
                                        console.warn(`Thumbnail not found for slide ${slide.slide_index}`);
                                        e.target.style.display = 'none';
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
                                            <ShapeRenderer {shape} {projectId} />
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
                    title={useThumbnails ? "렌더링 보기로 전환" : "썸네일 보기로 전환"}
                >
                    {#if useThumbnails}
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z"/>
                        </svg>
                        <span>썸네일</span>
                    {:else}
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
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
                                src={`/api/results/${projectId}/thumbnails/slide_${currentSlide.slide_index.toString().padStart(3, '0')}_thumb.png`}
                                alt={`Slide ${currentSlide.slide_index} thumbnail`}
                                class="w-full h-full object-contain"
                                on:error={(e) => {
                                    console.warn(`Thumbnail not found for slide ${currentSlide.slide_index}, falling back to rendering`);
                                    e.target.style.display = 'none';
                                }}
                            />
                        {:else}
                            {#each sortedShapes as shape (shape.shape_index)}
                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                <div
                                    on:mousedown={(e) => handleMouseDown(e, shape)}
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
    <div
        class="w-1 bg-gray-300 hover:bg-blue-500 cursor-col-resize transition-colors shrink-0"
        on:mousedown={startResize}
    ></div>

    <!-- Right Sidebar -->
    <div
        class="bg-white border-l border-gray-200 flex flex-col shrink-0"
        style="width: {rightPaneWidth}px;"
    >
        <div class="p-4 border-b border-gray-200">
            <h2 class="font-bold text-gray-800">프로젝트 정보</h2>
        </div>

        <div class="flex-1 overflow-y-auto">
            <!-- Summary Fields -->
            <div class="p-4 border-b border-gray-200 space-y-3">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-sm font-bold text-gray-700 uppercase">
                        요약 정보
                    </h3>
                    {#if settings.summary_fields && settings.summary_fields.length > 0}
                        <button
                            class="text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 px-2 py-1 rounded transition flex items-center gap-1 disabled:opacity-50"
                            on:click={generateAllSummaries}
                            disabled={generatingFieldId || generatingAll}
                            title="모든 요약 필드를 LLM으로 자동 생성"
                        >
                            {#if generatingAll}
                                <svg class="animate-spin h-3 w-3" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <span>생성 중...</span>
                            {:else}
                                <span>전체 자동 생성</span>
                            {/if}
                        </button>
                    {/if}
                </div>

                <!-- Slide Selection for Summary -->
                {#if settings.summary_fields && settings.summary_fields.length > 0}
                    <div class="bg-gray-50 rounded p-2 mb-3">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-xs text-gray-600">요약용 슬라이드:</span>
                            <button
                                class="text-xs text-blue-600 hover:text-blue-800 underline"
                                on:click={() => showSlideSelector = !showSlideSelector}
                            >
                                {showSlideSelector ? '닫기' : '변경'}
                            </button>
                        </div>
                        <div class="flex gap-1 flex-wrap">
                            {#each selectedSlideIndices.sort((a, b) => a - b) as idx}
                                <span class="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded">
                                    슬라이드 {idx}
                                </span>
                            {/each}
                            {#if selectedSlideIndices.length === 0}
                                <span class="text-xs text-gray-400 italic">선택된 슬라이드 없음</span>
                            {/if}
                        </div>

                        {#if showSlideSelector}
                            <div class="mt-2 pt-2 border-t border-gray-200">
                                <p class="text-xs text-gray-500 mb-2">최대 3개 선택 가능</p>
                                <div class="grid grid-cols-4 gap-1 max-h-32 overflow-y-auto">
                                    {#if project}
                                        {#each project.slides as slide}
                                            <button
                                                class="text-xs p-1 rounded border transition {selectedSlideIndices.includes(slide.slide_index)
                                                    ? 'bg-blue-500 text-white border-blue-500'
                                                    : 'bg-white text-gray-700 border-gray-300 hover:border-blue-300'}
                                                    {selectedSlideIndices.length >= 3 && !selectedSlideIndices.includes(slide.slide_index) ? 'opacity-50 cursor-not-allowed' : ''}"
                                                on:click={() => toggleSlideSelection(slide.slide_index)}
                                                disabled={selectedSlideIndices.length >= 3 && !selectedSlideIndices.includes(slide.slide_index)}
                                            >
                                                {slide.slide_index}
                                            </button>
                                        {/each}
                                    {/if}
                                </div>
                            </div>
                        {/if}
                    </div>
                {/if}

                {#if settings.summary_fields && settings.summary_fields.length > 0}
                    {#each settings.summary_fields.sort((a, b) => a.order - b.order) as field}
                        <div>
                            <div class="flex items-center justify-between mb-1">
                                <span class="text-sm font-medium text-gray-700">
                                    {field.name}
                                </span>
                                <button
                                    class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50"
                                    on:click={() => generateSummaryForField(field.id)}
                                    disabled={generatingFieldId || generatingAll}
                                    title="LLM으로 자동 생성"
                                >
                                    {#if generatingFieldId === field.id}
                                        <svg class="animate-spin h-3 w-3" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span>생성 중</span>
                                    {:else}
                                        <span>자동생성</span>
                                    {/if}
                                </button>
                            </div>
                            <div class="relative">
                                <textarea
                                    class="w-full text-sm p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none {generatingFieldId === field.id ? 'bg-purple-50 animate-pulse' : ''}"
                                    rows="3"
                                    placeholder="{field.name}을(를) 입력하세요..."
                                    bind:value={summaryData[field.id]}
                                    on:blur={saveSummary}
                                    disabled={generatingFieldId === field.id}
                                ></textarea>
                            </div>
                        </div>
                    {/each}
                    {#if savingSummary}
                        <div class="text-xs text-gray-500 italic">저장 중...</div>
                    {/if}
                {:else}
                    <div class="text-sm text-gray-400 italic">
                        설정에서 요약 필드를 추가하세요.
                    </div>
                {/if}
            </div>

            <!-- Object List (Collapsible) -->
            <div class="p-4">
                <button
                    class="w-full flex items-center justify-between px-2 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50 rounded mb-2"
                    on:click={() => otherShapesExpanded = !otherShapesExpanded}
                >
                    <span>객체 목록 ({allShapes.length})</span>
                    <span
                        class="text-gray-400 transition-transform duration-200"
                        class:rotate-180={otherShapesExpanded}
                    >
                        ▼
                    </span>
                </button>

                {#if otherShapesExpanded}
                    {#if allShapes.length === 0}
                        <div class="text-gray-400 text-sm text-center mt-4">
                            No objects found
                        </div>
                    {:else}
                        <!-- 이미지 객체 -->
                        {#if imageShapes.length > 0}
                            <div class="mb-4">
                                <div class="flex items-center gap-2 px-2 py-1 mb-2">
                                    <span class="text-sm font-bold text-orange-600"
                                        >🖼️ 이미지</span
                                    >
                                    <span
                                        class="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full"
                                    >
                                        설명을 달아주세요!!
                                    </span>
                                </div>
                                <ul class="space-y-1">
                                    {#each imageShapes as shape}
                                        <li>
                                            <button
                                                class="w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between group border-l-4 border-orange-400 {selectedShapeId ===
                                                shape.shape_index
                                                    ? 'bg-orange-50 text-orange-700 ring-1 ring-orange-300'
                                                    : 'hover:bg-orange-50 text-gray-700 bg-orange-50/50'}"
                                                on:click={() =>
                                                    (selectedShapeId =
                                                        shape.shape_index)}
                                            >
                                                <span
                                                    class="truncate"
                                                    title={shape.name}
                                                    >{shape.name}</span
                                                >
                                                {#if shape.description}
                                                    <span
                                                        class="text-xs text-green-500 ml-2"
                                                        >✅</span
                                                    >
                                                {:else}
                                                    <span
                                                        class="text-xs text-orange-400 ml-2"
                                                        >⚠️</span
                                                    >
                                                {/if}
                                            </button>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}

                        <!-- 기타 객체 -->
                        {#if otherShapes.length > 0}
                            <div class="border-t border-gray-200 pt-2">
                                <div class="px-2 py-1 mb-1">
                                    <span class="text-sm font-medium text-gray-600"
                                        >기타 객체 ({otherShapes.length})</span
                                    >
                                </div>

                                <ul class="space-y-1">
                                    {#each otherShapes as shape}
                                        <li>
                                            <button
                                                class="w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between group {selectedShapeId ===
                                                shape.shape_index
                                                    ? 'bg-blue-50 text-blue-700 ring-1 ring-blue-300'
                                                    : 'hover:bg-gray-50 text-gray-700'}"
                                                on:click={() =>
                                                    (selectedShapeId =
                                                        shape.shape_index)}
                                            >
                                                <span
                                                    class="truncate"
                                                    title={shape.name}
                                                    >{shape.name}</span
                                                >
                                                {#if shape.description}
                                                    <span
                                                        class="text-xs text-gray-400 ml-2"
                                                        >📝</span
                                                    >
                                                {/if}
                                            </button>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    {/if}

                    <!-- Description Editor -->
                    {#if selectedShape}
                        <div class="mt-4 p-3 border-t border-gray-200 bg-gray-50 rounded">
                            <h4 class="text-xs font-bold text-gray-500 uppercase mb-2">
                                Description
                            </h4>
                            <div class="space-y-2">
                                <div
                                    class="text-sm font-medium text-gray-800 truncate mb-1"
                                >
                                    {selectedShape.name}
                                </div>
                                <textarea
                                    class="w-full text-sm p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
                                    rows="3"
                                    placeholder="Enter description..."
                                    bind:value={editingDescription}
                                    on:keydown={(e) => {
                                        if (e.key === "Enter" && !e.shiftKey) {
                                            e.preventDefault();
                                            handleSaveDescription();
                                        }
                                    }}
                                ></textarea>
                                <button
                                    class="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm py-1.5 rounded transition"
                                    on:click={handleSaveDescription}
                                >
                                    Save Description
                                </button>
                            </div>
                        </div>
                    {/if}
                {/if}
            </div>
        </div>
    </div>
</div>
