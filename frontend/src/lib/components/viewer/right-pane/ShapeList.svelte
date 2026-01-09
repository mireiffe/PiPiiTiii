<script>
    import { createEventDispatcher } from "svelte";
    import ShapeItem from "./ShapeItem.svelte";

    export let shapes;
    export let selectedShapeId = null;
    export let title = "";
    export let icon = "🔹";
    export let colorScheme = "blue";
    export let borderColor = "gray-200";

    const dispatch = createEventDispatcher();
</script>

{#if shapes.length > 0}
    <div>
        <div class="flex items-center gap-2 px-2 py-1 mb-1">
            <span
                class="text-xs font-bold uppercase tracking-wide {colorScheme === 'orange'
                    ? 'text-orange-600'
                    : colorScheme === 'indigo'
                      ? 'text-indigo-600'
                      : 'text-gray-500'}"
            >
                {title}
            </span>
            <span class="h-px flex-1 bg-{borderColor}"></span>
        </div>
        <ul class="space-y-1">
            {#each shapes as shape}
                <li>
                    <ShapeItem
                        {shape}
                        {selectedShapeId}
                        icon={icon}
                        {colorScheme}
                        on:select
                    />
                </li>
            {/each}
        </ul>
    </div>
{/if}
