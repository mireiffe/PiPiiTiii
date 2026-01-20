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
        <div
            class="p-3 border-b border-gray-200 bg-white flex items-center justify-between shadow-sm z-10"
        >
            <Button
                href="/"
                variant="ghost"
                size="sm"
                class="p-2 shrink-0"
                title="Back to Dashboard"
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                    /></svg
                >
            </Button>
            <button
                class="p-2 hover:bg-gray-100 rounded transition-colors shrink-0"
                on:click={togglePane}
                title="사이드바 접기"
            >
                <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
            </button>
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
        <!-- Home and toggle buttons -->
        <div class="p-2 border-b border-gray-200 flex flex-col items-center gap-1">
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
            <button
                class="p-2 hover:bg-gray-100 rounded transition-colors"
                on:click={togglePane}
                title="사이드바 펼치기"
            >
                <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
            </button>
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
