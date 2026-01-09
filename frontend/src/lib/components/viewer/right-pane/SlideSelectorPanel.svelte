<script>
    import { createEventDispatcher } from "svelte";

    export let selectedSlideIndices = [];
    export let project;

    const dispatch = createEventDispatcher();

    let showSlideSelector = false;
</script>

<div class="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
    <button
        class="w-full flex items-center justify-between p-3.5 text-left hover:bg-gray-50 transition-colors"
        on:click={() => (showSlideSelector = !showSlideSelector)}
    >
        <div class="flex items-center gap-2 overflow-hidden">
            <span
                class="text-xs font-semibold text-gray-500 whitespace-nowrap uppercase tracking-wider"
            >
                참조 슬라이드
            </span>
            <div class="flex gap-1 overflow-hidden">
                {#if selectedSlideIndices.length === 0}
                    <span class="text-xs text-gray-400 italic">선택 없음</span>
                {:else}
                    {#each selectedSlideIndices.sort((a, b) => a - b) as idx}
                        <span
                            class="bg-blue-50 border border-blue-100 text-blue-600 text-[10px] font-medium px-2 py-0.5 rounded-full"
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
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
            />
        </svg>
    </button>

    {#if showSlideSelector}
        <div
            class="p-4 bg-gray-50/50 border-t border-gray-100 animate-in fade-in slide-in-from-top-1 duration-200"
        >
            <div class="flex items-center justify-between mb-3">
                <p class="text-[11px] text-gray-400 flex items-center gap-1">
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
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    최대 3개 선택 가능
                </p>
            </div>
            <div class="grid grid-cols-5 gap-1.5 max-h-32 overflow-y-auto p-1">
                {#if project}
                    {#each project.slides as slide}
                        <button
                            class="text-xs p-2 rounded-lg border transition-all flex flex-col items-center justify-center gap-1 {selectedSlideIndices.includes(
                                slide.slide_index,
                            )
                                ? 'bg-blue-50 text-blue-600 border-blue-200 ring-2 ring-blue-100 font-bold'
                                : 'bg-white text-gray-500 border-gray-200 hover:border-blue-200 hover:text-blue-500 shadow-sm'}
                                {selectedSlideIndices.length >= 3 &&
                            !selectedSlideIndices.includes(slide.slide_index)
                                ? 'opacity-40 cursor-not-allowed grayscale'
                                : ''}"
                            on:click={() =>
                                dispatch("toggleSlideSelection", {
                                    slideIndex: slide.slide_index,
                                })}
                            disabled={selectedSlideIndices.length >= 3 &&
                                !selectedSlideIndices.includes(slide.slide_index)}
                        >
                            <span>{slide.slide_index}</span>
                        </button>
                    {/each}
                {/if}
            </div>
        </div>
    {/if}
</div>
