<script>
    import { createEventDispatcher } from "svelte";

    export let icon = "";
    export let title = "";
    export let isExpanded = false;
    export let badge = null;
    export let savingIndicator = false;

    const dispatch = createEventDispatcher();
</script>

<div
    class="w-full flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-gray-50 transition-all font-medium text-gray-700 hover:text-blue-600 select-none"
    on:click
    role="button"
    tabindex="0"
    on:keydown={(e) => e.key === "Enter" && dispatch("click")}
>
    <div class="flex items-center gap-2.5">
        <span class="text-lg">{icon}</span>
        <span class="font-bold text-sm tracking-wide">{title}</span>
        {#if savingIndicator}
            <span
                class="text-xs font-normal text-blue-500 animate-pulse bg-blue-50 px-2 py-0.5 rounded-full"
            >
                저장 중...
            </span>
        {/if}
        {#if badge !== null}
            <span
                class="bg-blue-50 text-blue-600 border border-blue-100 text-xs px-2 py-0.5 rounded-full font-mono"
            >
                {badge}
            </span>
        {/if}
    </div>

    <div class="flex items-center gap-2">
        <slot name="actions" />

        <svg
            class="w-4 h-4 text-gray-400 transition-transform duration-300 ease-in-out {isExpanded
                ? 'rotate-180 text-blue-500'
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
</div>
