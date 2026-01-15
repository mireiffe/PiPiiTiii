<script>
    import Button from "$lib/components/ui/Button.svelte";
    import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
    import { createEventDispatcher } from "svelte";

    export let project;
    export let projectId;
    export let currentSlideIndex;
    export let useThumbnails;
    export let expanded = true;

    const dispatch = createEventDispatcher();

    function selectSlide(index) {
        dispatch("select", { index });
    }

    function togglePane() {
        dispatch("toggle");
    }
</script>

{#if expanded}
    <div class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 relative">
        <!-- Toggle button (collapse) -->
        <button
            class="absolute -right-3 top-6 z-20 w-6 h-6 bg-white border border-gray-300 rounded-full shadow-sm flex items-center justify-center hover:bg-gray-50 hover:border-blue-400 transition-colors"
            on:click={togglePane}
            title="사이드바 접기"
        >
            <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
        </button>

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
{:else}
    <!-- Collapsed state -->
    <div class="w-12 bg-white border-r border-gray-200 flex flex-col shrink-0 relative">
        <!-- Toggle button (expand) -->
        <button
            class="absolute -right-3 top-6 z-20 w-6 h-6 bg-white border border-gray-300 rounded-full shadow-sm flex items-center justify-center hover:bg-gray-50 hover:border-blue-400 transition-colors"
            on:click={togglePane}
            title="사이드바 펼치기"
        >
            <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
        </button>

        <!-- Home button -->
        <div class="p-2 border-b border-gray-200 flex justify-center">
            <Button
                href="/"
                variant="ghost"
                size="sm"
                class="p-2"
                title="Back to Dashboard"
            >
                <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
            </Button>
        </div>

        <!-- Slide numbers -->
        <div class="flex-1 overflow-y-auto py-2">
            {#if project}
                {#each project.slides as slide, i}
                    <button
                        id={`slide-thumb-${i}`}
                        class="w-full py-2 text-center text-sm font-medium transition {currentSlideIndex === i
                            ? 'bg-blue-50 text-blue-600 border-r-2 border-blue-500'
                            : 'text-gray-500 hover:bg-gray-50'}"
                        on:click={() => selectSlide(i)}
                        title={`Slide ${slide.slide_index}`}
                    >
                        {slide.slide_index}
                    </button>
                {/each}
            {/if}
        </div>
    </div>
{/if}
