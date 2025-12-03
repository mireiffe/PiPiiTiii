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
    } from "$lib/api/project";

    const projectId = $page.params.id;
    let project = null;
    let currentSlideIndex = 0;
    let loading = true;
    let saving = false;

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
    // History stores arrays of { shape_index, left, top } for the current slide
    let history = [];
    let historyIndex = -1;
    let isDirty = false;

    // Selection & Sidebar
    let selectedShapeId = null;
    let editingDescription = "";

    onMount(async () => {
        await loadProject();
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

                // Check for slide query param
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

    function updateScale() {
        if (!project || !containerWidth) return;
        // Fit to width with some padding
        const slideW = project.slide_width || 960;
        scale = (containerWidth - 64) / slideW; // 32px padding on each side
    }

    $: currentSlide = project?.slides.find(
        (s) => s.slide_index === currentSlideIndex + 1,
    );

    // Flatten shapes for the sidebar list (including children if needed)
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

    // Watch selection to update description input
    $: if (selectedShape) {
        editingDescription = selectedShape.description || "";
    } else {
        editingDescription = "";
    }

    // --- History Management ---

    function resetHistory() {
        history = [];
        historyIndex = -1;
        isDirty = false;
        if (currentSlide) {
            pushToHistory(true); // Initial state
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

        // If not initial, check if different from current
        if (!initial && historyIndex >= 0) {
            const current = history[historyIndex];
            const isSame = JSON.stringify(current) === JSON.stringify(snapshot);
            if (isSame) return;
        }

        // Truncate future if we are in middle
        if (historyIndex < history.length - 1) {
            history = history.slice(0, historyIndex + 1);
        }

        history = [...history, snapshot];
        historyIndex++;
        if (!initial) isDirty = true;
    }

    function restoreSnapshot(snapshot) {
        if (!currentSlide) return;

        // Create a map for fast lookup
        const snapMap = new Map(snapshot.map((s) => [s.shape_index, s]));

        // Update all shapes
        // We need to update the actual objects in the project structure
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
        currentSlide = currentSlide; // Trigger reactivity
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

    // --- Drag & Drop Logic ---

    function handleMouseDown(e, shape) {
        if (e.button !== 0) return; // Only left click
        e.preventDefault();
        e.stopPropagation(); // Prevent selecting underlying shapes

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
        if (!draggingId) return;

        const dx = (e.clientX - startX) / scale;
        const dy = (e.clientY - startY) / scale;

        // Find shape recursively
        // Optimization: we know the draggingId, we can find it in allShapes
        const shape = allShapes.find((s) => s.shape_index === draggingId);

        if (shape) {
            shape.left = initialLeft + dx;
            shape.top = initialTop + dy;
            currentSlide = currentSlide; // Trigger reactivity
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

    // --- Actions ---

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

        // Optimistic update
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
                        resetHistory(); // Reset history for this slide
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

    // Switch slide handler
    async function selectSlide(index) {
        if (isDirty) {
            if (!confirm("You have unsaved changes. Discard them?")) return;
        }
        currentSlideIndex = index;
        await tick();
        resetHistory();
        scrollToSlide(index);
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
                                            scale={1}
                                            {projectId}
                                        />
                                    </div>
                                {/each}
                            </div>
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

            <div class="flex items-center space-x-2 shrink-0">
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
                    class="bg-white shadow-lg relative transition-transform duration-200 ease-out origin-center"
                    style={`
            width: ${project.slide_width * scale}px;
            height: ${project.slide_height * scale}px;
          `}
                >
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
                                {scale}
                                {projectId}
                                highlight={selectedShapeId ===
                                    shape.shape_index}
                            />
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </div>

    <!-- Right Sidebar (Object List) -->
    <div class="w-72 bg-white border-l border-gray-200 flex flex-col shrink-0">
        <div class="p-4 border-b border-gray-200">
            <h2 class="font-bold text-gray-800">Object List</h2>
        </div>

        <div class="flex-1 overflow-y-auto p-2">
            {#if allShapes.length === 0}
                <div class="text-gray-400 text-sm text-center mt-10">
                    No objects found
                </div>
            {/if}
            <ul class="space-y-1">
                {#each allShapes as shape}
                    <li>
                        <button
                            class="w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between group {selectedShapeId ===
                            shape.shape_index
                                ? 'bg-blue-50 text-blue-700 ring-1 ring-blue-300'
                                : 'hover:bg-gray-50 text-gray-700'}"
                            on:click={() =>
                                (selectedShapeId = shape.shape_index)}
                        >
                            <span class="truncate" title={shape.name}
                                >{shape.name}</span
                            >
                            {#if shape.description}
                                <span class="text-xs text-gray-400 ml-2"
                                    >📝</span
                                >
                            {/if}
                        </button>
                    </li>
                {/each}
            </ul>
        </div>

        <!-- Description Editor -->
        <div class="p-4 border-t border-gray-200 bg-gray-50">
            <h3 class="text-xs font-bold text-gray-500 uppercase mb-2">
                Description
            </h3>
            {#if selectedShape}
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
            {:else}
                <div class="text-sm text-gray-400 italic text-center py-4">
                    Select an object to edit description
                </div>
            {/if}
        </div>
    </div>
</div>
