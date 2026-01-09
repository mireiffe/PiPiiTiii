<script>
    import { createEventDispatcher } from "svelte";

    export let shape;
    export let selectedShapeId = null;
    export let icon = "🔹";
    export let colorScheme = "blue"; // blue, orange, indigo

    const dispatch = createEventDispatcher();

    $: isSelected = selectedShapeId === shape.shape_index;

    $: colorClasses = {
        blue: {
            selected: "bg-blue-50 border-blue-200 shadow-sm ring-1 ring-blue-200",
            normal: "bg-white border-transparent hover:border-gray-200 hover:shadow-sm",
        },
        orange: {
            selected: "bg-orange-50 border-orange-200 shadow-sm ring-1 ring-orange-200",
            normal: "bg-white border-transparent hover:border-orange-200 hover:shadow-sm",
        },
        indigo: {
            selected: "bg-indigo-50 border-indigo-200 shadow-sm ring-1 ring-indigo-200",
            normal: "bg-white border-transparent hover:border-indigo-200 hover:shadow-sm",
        },
    }[colorScheme];
</script>

<button
    class="w-full text-left p-2 rounded-lg text-sm flex items-start gap-3 transition-all border {isSelected
        ? colorClasses.selected
        : colorClasses.normal}"
    on:click={() => dispatch("select", { shapeIndex: shape.shape_index })}
>
    {#if icon === "status"}
        {#if shape.description}
            <div class="mt-0.5 text-green-500" title="설명 완료">✅</div>
        {:else}
            <div class="mt-0.5 text-orange-400 animate-pulse" title="설명 필요">
                ⚠️
            </div>
        {/if}
    {:else if icon === "T"}
        <div class="mt-0.5 text-indigo-400">T</div>
    {:else}
        <div class="mt-0.5 text-gray-400">{icon}</div>
    {/if}

    <div class="flex-1 min-w-0">
        <div class="font-medium text-gray-700 truncate" title={shape.name}>
            {shape.name}
        </div>
        {#if shape.description}
            <div class="text-xs text-gray-400 truncate mt-0.5">
                {shape.description}
            </div>
        {:else if icon === "status"}
            <div class="text-xs text-orange-400 mt-0.5">설명을 입력해주세요</div>
        {/if}
    </div>

    {#if shape.description && icon !== "status"}
        <div class="mt-0.5 text-gray-300" title="설명 있음">📝</div>
    {/if}
</button>
