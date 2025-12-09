<script>
    /** @type {string} */
    export let title;
    /** @type {string} */
    export let value;
    /** @type {(value: string) => void} */
    export let onChange;

    // Cycle: "" (All) -> "on" (Yes) -> "off" (No) -> ""
    const states = [
        {
            value: "",
            label: "All",
            color: "bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100",
        },
        {
            value: "on",
            label: "Yes",
            color: "bg-green-50 text-green-700 border-green-200 ring-1 ring-green-500/20 hover:bg-green-100",
        },
        {
            value: "off",
            label: "No",
            color: "bg-red-50 text-red-700 border-red-200 ring-1 ring-red-500/20 hover:bg-red-100",
        },
    ];

    $: currentState = states.find((s) => s.value === value) || states[0];

    function cycle() {
        const currentIndex = states.findIndex((s) => s.value === value);
        // If value is not in states (e.g. initial load might be null), default to 0
        const idx = currentIndex === -1 ? 0 : currentIndex;
        const nextIndex = (idx + 1) % states.length;
        onChange(states[nextIndex].value);
    }
</script>

<button
    class="flex items-center justify-between gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors group {currentState.value !==
    ''
        ? 'border-blue-300 ring-1 ring-blue-100'
        : ''}"
    on:click={cycle}
    {title}
>
    <span
        class="text-xs font-medium {currentState.value !== ''
            ? 'text-blue-700'
            : 'text-gray-600'}">{title}</span
    >
    <div class="flex items-center gap-1">
        <span
            class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded {currentState.value ===
            'on'
                ? 'bg-green-100 text-green-700'
                : currentState.value === 'off'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-500'}"
        >
            {currentState.label}
        </span>
    </div>
</button>
