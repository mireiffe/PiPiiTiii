<script>
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";

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

    onMount(async () => {
        await loadProject();
        window.addEventListener("resize", updateScale);
    });

    async function loadProject() {
        try {
            const res = await fetch(
                `http://localhost:8000/api/project/${projectId}`,
            );
            if (res.ok) {
                project = await res.json();
                updateScale();
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
    $: sortedShapes =
        currentSlide?.shapes.sort(
            (a, b) => (a.z_order_position || 0) - (b.z_order_position || 0),
        ) || [];

    // --- Drag & Drop Logic ---

    function handleMouseDown(e, shape) {
        e.preventDefault();
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

        const shape = currentSlide.shapes.find(
            (s) => s.shape_index === draggingId,
        );
        if (shape) {
            shape.left = initialLeft + dx;
            shape.top = initialTop + dy;
            currentSlide = currentSlide; // Trigger reactivity
        }
    }

    async function handleMouseUp() {
        if (draggingId) {
            const shape = currentSlide.shapes.find(
                (s) => s.shape_index === draggingId,
            );
            if (shape) {
                await savePosition(shape);
            }
        }
        draggingId = null;
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
    }

    async function savePosition(shape) {
        saving = true;
        try {
            await fetch(
                `http://localhost:8000/api/project/${projectId}/update`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        slide_index: currentSlide.slide_index,
                        shape_index: shape.shape_index,
                        left: shape.left,
                        top: shape.top,
                    }),
                },
            );
        } catch (e) {
            console.error("Failed to save position", e);
        } finally {
            saving = false;
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
            const res = await fetch(
                `http://localhost:8000/api/project/${projectId}/reparse_all`,
                {
                    method: "POST",
                },
            );

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
                `Are you sure you want to reparse Slide ${currentSlide.slide_index}? This will reset changes for this slide.`,
            )
        )
            return;

        loading = true;
        try {
            const res = await fetch(
                `http://localhost:8000/api/project/${projectId}/slides/${currentSlide.slide_index}/reparse`,
                {
                    method: "POST",
                },
            );

            if (res.ok) {
                const data = await res.json();
                // Update specific slide in local state
                if (project && data.slide) {
                    const idx = project.slides.findIndex(
                        (s) => s.slide_index === data.slide.slide_index,
                    );
                    if (idx !== -1) {
                        project.slides[idx] = data.slide;
                        project = project; // Trigger reactivity
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
</script>

<div class="flex h-screen bg-gray-100 overflow-hidden">
    <!-- Sidebar -->
    <div class="w-64 bg-white border-r border-gray-200 flex flex-col">
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
                        class="w-full text-left p-2 rounded hover:bg-gray-50 transition {currentSlideIndex ===
                        i
                            ? 'ring-2 ring-blue-500 bg-blue-50'
                            : ''}"
                        on:click={() => (currentSlideIndex = i)}
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
                                        <ShapeRenderer {shape} scale={1} />
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
        class="flex-1 flex flex-col relative"
        bind:clientWidth={containerWidth}
    >
        <!-- Toolbar -->
        <div
            class="h-12 bg-white border-b border-gray-200 flex items-center justify-between px-4"
        >
            <div class="text-sm text-gray-500">
                {#if saving}
                    <span class="text-blue-600">Saving changes...</span>
                {:else}
                    All changes saved
                {/if}
            </div>
            <div class="flex items-center space-x-2">
                <button
                    class="bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded text-sm transition"
                    on:click={handleReparseAll}
                >
                    Reparse All
                </button>
                <button
                    class="bg-blue-100 hover:bg-blue-200 text-blue-700 px-3 py-1 rounded text-sm transition"
                    on:click={handleReparseSlide}
                >
                    Reparse Slide
                </button>
                <div class="w-px h-4 bg-gray-300 mx-2"></div>
                <button
                    class="p-1 hover:bg-gray-100 rounded"
                    on:click={() => (scale *= 1.1)}>+</button
                >
                <span class="text-xs text-gray-500"
                    >{Math.round(scale * 100)}%</span
                >
                <button
                    class="p-1 hover:bg-gray-100 rounded"
                    on:click={() => (scale *= 0.9)}>-</button
                >
            </div>
        </div>

        <!-- Canvas -->
        <div
            class="flex-1 overflow-auto bg-gray-100 p-8 flex items-center justify-center"
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
                            <ShapeRenderer {shape} {scale} />
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
</div>
