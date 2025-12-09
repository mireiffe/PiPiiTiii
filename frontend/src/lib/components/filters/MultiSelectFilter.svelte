<script>
    /** @type {string} */
    export let title;
    /** @type {any[]} */
    export let options = [];
    /** @type {any[]} */
    export let selected = [];
    /** @type {(selected: any[]) => void} */
    export let onChange;

    // Compute derived state
    $: allSelected = options.length > 0 && selected.length === options.length;
    $: isIndeterminate =
        selected.length > 0 && selected.length < options.length;

    function toggleOption(option) {
        let newSelected;
        if (selected.includes(option)) {
            newSelected = selected.filter((s) => s !== option);
        } else {
            newSelected = [...selected, option];
        }
        onChange(newSelected);
    }

    function toggleAll() {
        if (allSelected) {
            onChange([]);
        } else {
            onChange([...options]);
        }
    }

    let expanded = false;
</script>

<div class="flex flex-col relative">
    <button
        class="flex items-center justify-between gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors group {expanded
            ? 'rounded-b-none border-b-0 bg-gray-50'
            : ''}"
        on:click={() => (expanded = !expanded)}
        {title}
    >
        <div class="flex items-center gap-2 overflow-hidden">
            <span class="text-xs font-medium text-gray-700 whitespace-nowrap"
                >{title}</span
            >
            <span
                class="text-[10px] text-gray-500 truncate bg-gray-100 px-1.5 py-0.5 rounded"
            >
                {#if selected.length === 0}
                    All
                {:else if selected.length === options.length}
                    All
                {:else}
                    {selected.length}
                {/if}
            </span>
        </div>
        <svg
            class="w-3.5 h-3.5 text-gray-400 transition-transform duration-200 flex-shrink-0 {expanded
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

    {#if expanded}
        <div
            class="absolute top-full left-0 right-0 bg-white border border-gray-200 border-t-0 rounded-b-lg p-2 shadow-lg z-20"
        >
            <div class="flex justify-end mb-2">
                <button
                    class="text-[10px] font-medium text-blue-600 hover:text-blue-800 transition-colors"
                    on:click={toggleAll}
                >
                    {allSelected ? "Deselect All" : "Select All"}
                </button>
            </div>
            <div
                class="overflow-y-auto space-y-1 custom-scrollbar pr-1 max-h-40"
            >
                {#if options.length === 0}
                    <div class="text-xs text-gray-400 italic">No options</div>
                {/if}
                {#each options as option}
                    <label
                        class="flex items-center gap-2 cursor-pointer group select-none hover:bg-gray-50 p-1 rounded"
                    >
                        <div
                            class="relative flex items-center justify-center w-3.5 h-3.5"
                        >
                            <input
                                type="checkbox"
                                class="peer appearance-none w-3.5 h-3.5 border border-gray-300 rounded bg-white checked:bg-blue-500 checked:border-blue-500 transition-all cursor-pointer"
                                checked={selected.includes(option)}
                                on:change={() => toggleOption(option)}
                            />
                            <svg
                                class="absolute w-2.5 h-2.5 text-white pointer-events-none opacity-0 peer-checked:opacity-100 transition-opacity"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="3"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <span
                            class="text-xs text-gray-600 group-hover:text-gray-900 transition-colors truncate"
                            >{option}</span
                        >
                    </label>
                {/each}
            </div>
        </div>
    {/if}
</div>

<style>
    .custom-scrollbar::-webkit-scrollbar {
        width: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 2px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #d1d5db;
        border-radius: 2px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #9ca3af;
    }
</style>
