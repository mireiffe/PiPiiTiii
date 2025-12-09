<script>
    /** @type {string} */
    export let title;
    /** @type {boolean} */
    export let active = false;
    /** @type {'asc' | 'desc'} */
    export let direction = "desc";
    /** @type {() => void} */
    export let onToggle;
</script>

<button
    class="flex items-center justify-between gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors group {active
        ? 'border-blue-300 ring-1 ring-blue-100'
        : ''}"
    on:click={onToggle}
    {title}
>
    <span
        class="text-xs font-medium {active ? 'text-blue-700' : 'text-gray-600'}"
        >{title}</span
    >
    <div class="flex items-center">
        {#if active}
            <svg
                class="w-3.5 h-3.5 text-blue-600 transition-transform duration-200 {direction ===
                'asc'
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
        {:else}
            <svg
                class="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover:opacity-50 transition-opacity"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
                />
            </svg>
        {/if}
    </div>
</button>
