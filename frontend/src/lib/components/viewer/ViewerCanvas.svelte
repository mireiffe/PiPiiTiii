<script>
    import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
    import { createEventDispatcher } from "svelte";

    export let project;
    export let currentSlide;
    export let scale;
    export let useThumbnails;
    export let projectId;
    export let sortedShapes = [];
    export let selectedShapeId;

    const dispatch = createEventDispatcher();

    function handleWheel(e) {
        dispatch("wheel", e);
    }

    function handleMouseDownShape(e, shape) {
        dispatch("shapeMouseDown", { event: e, shape });
    }

    function handleCanvasMouseDown() {
        dispatch("canvasMouseDown");
    }
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
    class="flex-1 overflow-auto bg-gray-100 p-8 flex items-center justify-center"
    on:wheel={handleWheel}
    on:mousedown={handleCanvasMouseDown}
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
                            on:mousedown={(e) => handleMouseDownShape(e, shape)}
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
