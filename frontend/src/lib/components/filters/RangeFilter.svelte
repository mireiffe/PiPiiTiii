<script>
    /** @type {string} */
    export let title;
    export let min = 0;
    export let max = 100;
    /** @type {number|undefined} */
    export let selectedMin;
    /** @type {number|undefined} */
    export let selectedMax;
    /** @type {(range: {min: number, max: number}) => void} */
    export let onChange; // ({min, max}) => void

    // Sort props
    export let isSorted = false;
    export let sortDirection = "asc"; // 'asc' | 'desc'
    /** @type {() => void} */
    export let onSortChange; // () => void

    let expanded = false;

    // Local state
    let localMin;
    let localMax;

    // Initialize local state
    $: {
        localMin =
            selectedMin !== "" &&
            selectedMin !== undefined &&
            selectedMin !== null
                ? Number(selectedMin)
                : min;
        localMax =
            selectedMax !== "" &&
            selectedMax !== undefined &&
            selectedMax !== null
                ? Number(selectedMax)
                : max;
    }

    // Calculate percentages for the track
    $: minPercent = Math.max(
        0,
        Math.min(100, ((localMin - min) / (max - min)) * 100),
    );
    $: maxPercent = Math.max(
        0,
        Math.min(100, ((localMax - min) / (max - min)) * 100),
    );

    function handleMinChange(e) {
        const val = Number(e.target.value);
        // Prevent crossing
        if (val > localMax) {
            localMin = localMax;
        } else {
            localMin = val;
        }
        onChange({ min: localMin, max: localMax });
    }

    function handleMaxChange(e) {
        const val = Number(e.target.value);
        // Prevent crossing
        if (val < localMin) {
            localMax = localMin;
        } else {
            localMax = val;
        }
        onChange({ min: localMin, max: localMax });
    }
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
                {#if (selectedMin !== undefined && selectedMin !== "" && selectedMin !== null) || (selectedMax !== undefined && selectedMax !== "" && selectedMax !== null)}
                    {Number(localMin).toLocaleString()} - {Number(
                        localMax,
                    ).toLocaleString()}
                {:else}
                    All
                {/if}
            </span>
        </div>
        <div class="flex items-center gap-1">
            <!-- Sort Toggle (Mini) -->
            <div
                class="p-0.5 rounded hover:bg-gray-200 transition-colors {isSorted
                    ? 'text-blue-600'
                    : 'text-gray-300'}"
                on:click|stopPropagation={onSortChange}
                title="Toggle Sort"
            >
                {#if isSorted}
                    <svg
                        class="w-3 h-3 {sortDirection === 'asc'
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
                        class="w-3 h-3"
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

            <svg
                class="w-3.5 h-3.5 text-gray-400 transition-transform duration-200 {expanded
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
        </div>
    </button>

    {#if expanded}
        <div
            class="absolute top-full left-0 right-0 bg-white border border-gray-200 border-t-0 rounded-b-lg p-3 shadow-lg z-20 min-w-[200px]"
        >
            <!-- Dual Slider -->
            <div class="relative h-8 mb-2">
                <div
                    class="absolute top-1/2 left-0 right-0 h-1 bg-gray-200 rounded-full -translate-y-1/2"
                ></div>
                <div
                    class="absolute top-1/2 h-1 bg-blue-500 rounded-full -translate-y-1/2"
                    style="left: {minPercent}%; right: {100 - maxPercent}%"
                ></div>

                <!-- Range Inputs -->
                <input
                    type="range"
                    {min}
                    {max}
                    step="any"
                    value={localMin}
                    on:input={handleMinChange}
                    class="absolute top-1/2 -translate-y-1/2 w-full h-1 opacity-0 cursor-pointer pointer-events-none z-20 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:appearance-none"
                />
                <input
                    type="range"
                    {min}
                    {max}
                    step="any"
                    value={localMax}
                    on:input={handleMaxChange}
                    class="absolute top-1/2 -translate-y-1/2 w-full h-1 opacity-0 cursor-pointer pointer-events-none z-20 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:appearance-none"
                />
            </div>

            <!-- Manual Inputs -->
            <div class="flex items-center gap-2">
                <input
                    type="number"
                    bind:value={localMin}
                    on:change={() => onChange({ min: localMin, max: localMax })}
                    class="w-full px-1.5 py-1 text-[10px] border border-gray-200 rounded focus:ring-1 focus:ring-blue-500 outline-none text-center"
                />
                <span class="text-gray-400 text-[10px]">to</span>
                <input
                    type="number"
                    bind:value={localMax}
                    on:change={() => onChange({ min: localMin, max: localMax })}
                    class="w-full px-1.5 py-1 text-[10px] border border-gray-200 rounded focus:ring-1 focus:ring-blue-500 outline-none text-center"
                />
            </div>
        </div>
    {/if}
</div>

<style>
    /* Custom Range Input Styling */
    input[type="range"] {
        -webkit-appearance: none; /* Hides the slider so that custom slider can be made */
        background: transparent; /* Otherwise white in Chrome */
    }

    input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        height: 16px;
        width: 16px;
        border-radius: 50%;
        background: #ffffff;
        border: 2px solid #3b82f6;
        cursor: pointer;
        margin-top: 0px; /* You need to specify a margin in Chrome, but in this absolute setup it might be fine */
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        pointer-events: auto;
    }

    input[type="range"]::-moz-range-thumb {
        height: 16px;
        width: 16px;
        border-radius: 50%;
        background: #ffffff;
        border: 2px solid #3b82f6;
        cursor: pointer;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        pointer-events: auto;
    }
</style>
