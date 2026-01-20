<script lang="ts">
    import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
    import { createEventDispatcher, onMount, tick } from "svelte";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";

    export let project;
    export let currentSlide;
    export let scale;
    export let useThumbnails;
    export let projectId;
    export let sortedShapes = [];
    export let selectedShapeId;
    export let currentSlideIndex;
    export let captureMode = false; // Enable capture mode
    export let captureOverlays = []; // Capture regions to display when phenomenon node is selected
    export let highlightedCaptureIndex = null; // Index of currently highlighted capture (for candidate search)
    export let isActionCapture = false; // True when capturing for action (gray color)

    // Candidate Cause Linking Props
    export let isCandidateLinkingMode = false;
    export let linkedEvidenceIds: string[] = [];

    // Create a map of slideIndex -> overlays for reactive updates
    $: overlaysBySlide = captureOverlays.reduce((acc, overlay) => {
        const idx = overlay.slideIndex;
        if (!acc[idx]) acc[idx] = [];
        acc[idx].push(overlay);
        return acc;
    }, {});

    const dispatch = createEventDispatcher();
    let slideElements = {};
    let observer;

    // Capture selection state
    let isCapturing = false;
    let captureStart = { x: 0, y: 0 };
    let captureEnd = { x: 0, y: 0 };
    let captureSlideIndex = -1;
    let captureSlideElement = null;

    onMount(() => {
        // Create Intersection Observer to detect which slide is in view
        observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
                        const slideIndex = parseInt(
                            entry.target.getAttribute("data-slide-index"),
                        );
                        dispatch("slideInView", { slideIndex });
                    }
                });
            },
            {
                root: null,
                threshold: [0, 0.5, 1],
                rootMargin: "-20% 0px -20% 0px",
            },
        );

        return () => {
            if (observer) {
                observer.disconnect();
            }
        };
    });

    // Watch for slideElements changes and observe new elements
    $: if (observer && project?.slides) {
        // Disconnect all and reconnect
        Object.values(slideElements).forEach((el) => {
            if (el) observer.observe(el);
        });
    }

    // Helper function to get shapes for a specific slide
    function getShapesForSlide(slide) {
        return (
            slide?.shapes.sort(
                (a, b) => (a.z_order_position || 0) - (b.z_order_position || 0),
            ) || []
        );
    }

    function handleWheel(e) {
        // Remove ctrl+wheel zoom, let natural scroll work
        if (!e.ctrlKey) {
            return;
        }
        dispatch("wheel", e);
    }

    function handleMouseDownShape(e, shape) {
        dispatch("shapeMouseDown", { event: e, shape });
    }

    function handleCanvasMouseDown(e) {
        // Only dispatch if clicking on the container, not slides
        if (e.target.classList.contains("slides-container")) {
            dispatch("canvasMouseDown");
        }
    }

    // Scroll to specific slide when currentSlideIndex changes externally
    export async function scrollToSlide(index) {
        await tick();
        const el = slideElements[index];
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    // Capture functions - left click + drag when in capture mode
    function handleSlideCaptureStart(e, slideIndex, slideEl) {
        if (!captureMode) return;
        if (e.button !== 0) return; // Left click only
        e.preventDefault();
        e.stopPropagation();

        isCapturing = true;
        captureSlideIndex = slideIndex;
        captureSlideElement = slideEl;

        const rect = slideEl.getBoundingClientRect();
        // Convert to slide coordinates (unscaled)
        captureStart = {
            x: (e.clientX - rect.left) / scale,
            y: (e.clientY - rect.top) / scale,
        };
        captureEnd = { ...captureStart };

        window.addEventListener("mousemove", handleCaptureMove);
        window.addEventListener("mouseup", handleCaptureEnd);
    }

    function handleCaptureMove(e) {
        if (!isCapturing || !captureSlideElement) return;

        const rect = captureSlideElement.getBoundingClientRect();
        captureEnd = {
            x: Math.max(
                0,
                Math.min(project.slide_width, (e.clientX - rect.left) / scale),
            ),
            y: Math.max(
                0,
                Math.min(project.slide_height, (e.clientY - rect.top) / scale),
            ),
        };
    }

    function handleCaptureEnd(e) {
        window.removeEventListener("mousemove", handleCaptureMove);
        window.removeEventListener("mouseup", handleCaptureEnd);

        if (!isCapturing) return;

        // Calculate capture region
        const x = Math.min(captureStart.x, captureEnd.x);
        const y = Math.min(captureStart.y, captureEnd.y);
        const width = Math.abs(captureEnd.x - captureStart.x);
        const height = Math.abs(captureEnd.y - captureStart.y);

        // Minimum size threshold
        if (width < 20 || height < 20) {
            isCapturing = false;
            captureSlideIndex = -1;
            return;
        }

        // Dispatch capture event (coordinates only, no thumbnail)
        dispatch("capture", {
            slideIndex: captureSlideIndex, // Keep as 0-based index
            x: Math.round(x),
            y: Math.round(y),
            width: Math.round(width),
            height: Math.round(height),
        });

        isCapturing = false;
        captureSlideIndex = -1;
        captureSlideElement = null;
    }

    // Calculate capture selection rectangle for display
    $: captureRect = isCapturing
        ? {
              left: Math.min(captureStart.x, captureEnd.x),
              top: Math.min(captureStart.y, captureEnd.y),
              width: Math.abs(captureEnd.x - captureStart.x),
              height: Math.abs(captureEnd.y - captureStart.y),
          }
        : null;
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
    class="flex-1 overflow-auto bg-gray-100 p-8 slides-container {captureMode
        ? isActionCapture ? 'capture-mode action-capture' : 'capture-mode'
        : ''}"
    on:wheel={handleWheel}
    on:mousedown={handleCanvasMouseDown}
>
    {#if captureMode}
        <div
            class="fixed top-16 left-1/2 transform -translate-x-1/2 z-50 {isActionCapture ? 'bg-gray-600' : 'bg-red-500'} text-white px-4 py-2 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2"
        >
            <svg
                class="w-4 h-4 animate-pulse"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
            </svg>
            {#if isActionCapture}
                Action 캡처 모드: 마우스 좌클릭+드래그로 영역을 선택하세요
            {:else}
                캡처 모드: 마우스 좌클릭+드래그로 영역을 선택하세요
            {/if}
        </div>
    {/if}

    <div class="flex flex-col gap-8">
        {#if project?.slides}
            {#each project.slides as slide, i (slide.slide_index)}
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <div
                    bind:this={slideElements[i]}
                    data-slide-index={i}
                    class="slide-container relative overflow-hidden mx-auto"
                    style={`
                        width: ${project.slide_width * scale}px;
                        height: ${project.slide_height * scale}px;
                    `}
                    on:mousedown={(e) =>
                        handleSlideCaptureStart(
                            e,
                            i,
                            slideElements[i].querySelector(".slide-inner"),
                        )}
                >
                    <div
                        class="bg-white shadow-lg relative transition-transform duration-200 ease-out origin-top-left slide-inner {captureMode
                            ? 'cursor-crosshair'
                            : ''}"
                        style={`
                            width: ${project.slide_width}px;
                            height: ${project.slide_height}px;
                            transform: scale(${scale});
                        `}
                    >
                        {#if useThumbnails}
                            <img
                                src={`/api/results/${projectId}/thumbnails/slide_${slide.slide_index.toString().padStart(3, "0")}_thumb.png`}
                                alt={`Slide ${slide.slide_index} thumbnail`}
                                class="w-full h-full object-fill pointer-events-none"
                                on:error={(e) => {
                                    console.warn(
                                        `Thumbnail not found for slide ${slide.slide_index}, falling back to rendering`,
                                    );
                                    e.target.style.display = "none";
                                }}
                            />
                        {:else}
                            {#each getShapesForSlide(slide) as shape (shape.shape_index)}
                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                <div
                                    on:mousedown={(e) =>
                                        handleMouseDownShape(e, shape)}
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

                        <!-- Capture selection rectangle (during capture) -->
                        {#if isCapturing && captureSlideIndex === i && captureRect}
                            <div
                                class="absolute border-2 {isActionCapture ? 'border-gray-500 bg-gray-500/20' : 'border-red-500 bg-red-500/20'} pointer-events-none"
                                style={`
                                    left: ${captureRect.left}px;
                                    top: ${captureRect.top}px;
                                    width: ${captureRect.width}px;
                                    height: ${captureRect.height}px;
                                `}
                            ></div>
                        {/if}

                        <!-- Capture overlay rectangles (when phenomenon node is selected) -->
                        {#each overlaysBySlide[i] || [] as overlay}
                            {@const color = overlay.isActionCapture
                                ? { bg: 'rgba(107, 114, 128, 0.2)', border: '#6b7280', name: '회색' }
                                : EVIDENCE_COLORS[
                                    overlay.colorIndex % EVIDENCE_COLORS.length
                                ]}
                            {@const isHighlighted =
                                highlightedCaptureIndex === overlay.colorIndex}
                            <!-- svelte-ignore a11y-click-events-have-key-events -->
                            <!-- svelte-ignore a11y-no-static-element-interactions -->
                            <div
                                class="absolute pointer-events-none border-2 transition-all duration-200
                                       {isHighlighted
                                    ? 'z-50 ring-4 ring-blue-500 ring-opacity-50'
                                    : ''}
                                       {isCandidateLinkingMode
                                    ? 'hover:brightness-110 z-40'
                                    : ''}"
                                style={`
                                    left: ${overlay.x}px;
                                    top: ${overlay.y}px;
                                    width: ${overlay.width}px;
                                    height: ${overlay.height}px;
                                    background-color: ${isHighlighted ? color.bg.replace("0.2", "0.4") : isCandidateLinkingMode && linkedEvidenceIds.includes(overlay.id) ? color.bg.replace("0.2", "0.4") : color.bg};
                                    border-color: ${color.border};
                                    border-width: ${isHighlighted || (isCandidateLinkingMode && linkedEvidenceIds.includes(overlay.id)) ? "3px" : "2px"};
                                    ${isHighlighted || (isCandidateLinkingMode && linkedEvidenceIds.includes(overlay.id)) ? "box-shadow: 0 0 20px " + color.border + "80;" : ""}
                                    ${isCandidateLinkingMode && !captureMode ? "cursor: pointer; pointer-events: auto !important;" : ""}
                                `}
                                on:click|stopPropagation={() => {
                                    if (isCandidateLinkingMode) {
                                        dispatch("evidenceClick", {
                                            evidenceId: overlay.id,
                                        });
                                    }
                                }}
                                title={overlay.isActionCapture ? `Action: ${overlay.actionName || ''}\nCause: ${overlay.causeName || ''}` : overlay.label || ''}
                            >
                                <div
                                    class="absolute -top-5 left-0 px-1.5 py-0.5 text-[10px] font-bold text-white rounded-t whitespace-nowrap
                                           {isHighlighted ? 'scale-110' : ''}"
                                    style="background-color: {color.border};"
                                >
                                    {#if overlay.isActionCapture}
                                        A{overlay.colorIndex + 1}
                                    {:else if overlay.isSupporter}
                                        {overlay.workflowName}: #{overlay.stepNumber}({overlay.phaseName || '위상'})-{overlay.captureIndexInStep + 1}
                                    {:else}
                                        {overlay.workflowName}: #{overlay.stepNumber}-{overlay.captureIndexInStep + 1}
                                    {/if}
                                </div>
                                {#if isHighlighted}
                                    <div
                                        class="absolute inset-0 flex items-center justify-center"
                                    >
                                        <div
                                            class="bg-black/50 text-white px-2 py-1 rounded text-xs font-medium"
                                        >
                                            선택됨
                                        </div>
                                    </div>
                                {/if}
                                {#if isCandidateLinkingMode && linkedEvidenceIds.includes(overlay.id)}
                                    <div
                                        class="absolute inset-0 flex items-center justify-center pointer-events-none"
                                    >
                                        <div
                                            class="bg-blue-600 text-white px-2 py-1 rounded-full shadow-lg transform scale-110"
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
                                                    stroke-width="3"
                                                    d="M5 13l4 4L19 7"
                                                />
                                            </svg>
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>

<style>
    .capture-mode {
        cursor: crosshair;
    }
    .capture-mode .slide-container:hover {
        outline: 2px dashed #ef4444;
        outline-offset: 4px;
    }
    .capture-mode.action-capture .slide-container:hover {
        outline: 2px dashed #6b7280;
        outline-offset: 4px;
    }
</style>
