<script>
    import { createEventDispatcher } from "svelte";

    export let selectedShape;
    export let editingDescription = "";

    const dispatch = createEventDispatcher();
</script>

{#if selectedShape}
    <div
        class="p-3 bg-white border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] z-10"
    >
        <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-gray-500 uppercase">Description</span>
            <span class="text-xs text-gray-400 max-w-[150px] truncate">
                {selectedShape.name}
            </span>
        </div>
        <div class="relative">
            <textarea
                class="w-full text-sm p-2 pr-10 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none transition-shadow"
                rows="2"
                placeholder="객체에 대한 설명을 입력하세요..."
                bind:value={editingDescription}
                on:keydown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        dispatch("save");
                    }
                }}
            ></textarea>
            <button
                class="absolute right-2 bottom-2 p-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm transition-transform active:scale-95"
                on:click={() => dispatch("save")}
                title="저장 (Enter)"
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M5 13l4 4L19 7"
                    />
                </svg>
            </button>
        </div>
    </div>
{/if}
