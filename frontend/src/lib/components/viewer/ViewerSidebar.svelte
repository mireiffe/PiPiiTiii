<script>
    import Button from "$lib/components/ui/Button.svelte";
    import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
    import { createEventDispatcher } from "svelte";

    export let project;
    export let projectId;
    export let currentSlideIndex;
    export let useThumbnails;

    const dispatch = createEventDispatcher();

    function selectSlide(index) {
        dispatch("select", { index });
    }
</script>

<div class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0">
    <div
        class="p-5 border-b border-gray-200 bg-white flex flex-col gap-2 shadow-sm z-10"
    >
        <h1
            class="font-bold text-gray-800 truncate text-lg"
            title={project?.ppt_path.split("\\").pop()}
        >
            {project?.ppt_path.split("\\").pop() || "Loading..."}
        </h1>
        <Button
            href="/"
            variant="ghost"
            size="sm"
            class="-ml-2 justify-start text-gray-500"
        >
            <svg
                class="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                /></svg
            >
            Back to Dashboard
        </Button>
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
