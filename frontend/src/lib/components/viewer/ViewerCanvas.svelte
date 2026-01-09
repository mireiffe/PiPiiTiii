<script>
    import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
    import { createEventDispatcher, onMount, tick } from "svelte";

    export let project;
    export let currentSlide;
    export let scale;
    export let useThumbnails;
    export let projectId;
    export let sortedShapes = [];
    export let selectedShapeId;
    export let currentSlideIndex;

    const dispatch = createEventDispatcher();
    let slideElements = {};
    let observer;

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
        return slide?.shapes.sort(
            (a, b) => (a.z_order_position || 0) - (b.z_order_position || 0),
        ) || [];
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
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
    class="flex-1 overflow-y-auto overflow-x-hidden bg-gray-100 p-8 slides-container"
    on:wheel={handleWheel}
    on:mousedown={handleCanvasMouseDown}
>
    <div class="flex flex-col items-center gap-8">
        {#if project?.slides}
            {#each project.slides as slide, i (slide.slide_index)}
                <div
                    bind:this={slideElements[i]}
                    data-slide-index={i}
                    class="slide-container"
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
                                src={`/api/results/${projectId}/thumbnails/slide_${slide.slide_index.toString().padStart(3, "0")}_thumb.png`}
                                alt={`Slide ${slide.slide_index} thumbnail`}
                                class="w-full h-full object-contain"
                                on:error={(e) => {
                                    console.warn(
                                        `Thumbnail not found for slide ${slide.slide_index}, falling back to rendering`,
                                    );
                                    e.target.style.display = "none";
                                }}
                            />
                        {:else if i === currentSlideIndex}
                            <!-- Only render shapes for the current slide to improve performance -->
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
                        {:else}
                            <!-- For non-current slides in render mode, show thumbnail as placeholder -->
                            <img
                                src={`/api/results/${projectId}/thumbnails/slide_${slide.slide_index.toString().padStart(3, "0")}_thumb.png`}
                                alt={`Slide ${slide.slide_index} thumbnail`}
                                class="w-full h-full object-contain"
                                on:error={(e) => {
                                    e.target.style.display = "none";
                                }}
                            />
                        {/if}
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>
