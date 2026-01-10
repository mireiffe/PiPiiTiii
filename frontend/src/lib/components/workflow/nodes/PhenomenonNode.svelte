<script lang="ts">
    import { Handle, Position, useUpdateNodeInternals } from "@xyflow/svelte";
    import { NODE_TYPE_COLORS, NODE_TYPE_NAMES, PHENOMENON_MIN_HEIGHT, PHENOMENON_MAX_HEIGHT } from "../utils/constants";
    import { CAPTURE_COLORS, type WorkflowNode } from "$lib/api/project";
    import { onMount, tick } from "svelte";

    export let id: string;
    export let data: {
        nodeId: string;
        workflowNode: WorkflowNode;
        label: string;
        isRoot?: boolean;
    };
    export let selected: boolean = false;

    $: isRoot = data.isRoot ?? false;

    const updateNodeInternals = useUpdateNodeInternals();

    let contentDiv: HTMLDivElement;
    let measuredHeight = PHENOMENON_MIN_HEIGHT;

    $: node = data.workflowNode;
    $: colors = NODE_TYPE_COLORS.Phenomenon;
    $: typeName = NODE_TYPE_NAMES.Phenomenon;
    $: captures = node.captures || [];
    $: description = node.description || "";

    // Update node height when content changes
    $: if (contentDiv && (captures || description)) {
        tick().then(() => {
            requestAnimationFrame(() => {
                if (contentDiv) {
                    const newHeight = Math.min(
                        PHENOMENON_MAX_HEIGHT,
                        Math.max(PHENOMENON_MIN_HEIGHT, contentDiv.scrollHeight + 40)
                    );
                    if (newHeight !== measuredHeight) {
                        measuredHeight = newHeight;
                        updateNodeInternals(id);
                    }
                }
            });
        });
    }

    onMount(() => {
        // Initial measurement
        if (contentDiv) {
            measuredHeight = Math.min(
                PHENOMENON_MAX_HEIGHT,
                Math.max(PHENOMENON_MIN_HEIGHT, contentDiv.scrollHeight + 40)
            );
        }
    });
</script>

<div
    class="rounded-lg border-2 shadow-sm transition-shadow duration-150 group
           {colors.bg} {colors.border}
           {selected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-md'}"
    style="width: 180px; min-height: {PHENOMENON_MIN_HEIGHT}px; height: auto;"
>
    <!-- Type Badge -->
    <div
        class="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold text-white {colors.darkBg}"
    >
        {typeName}
    </div>

    <!-- Content Area -->
    <div
        bind:this={contentDiv}
        class="flex flex-col p-2 pt-3 justify-between overflow-hidden"
        style="min-height: {PHENOMENON_MIN_HEIGHT - 40}px; max-height: {PHENOMENON_MAX_HEIGHT - 40}px;"
    >
        <!-- Node Name -->
        <span class="text-sm font-semibold {colors.text} truncate" title={data.label}>
            {data.label}
        </span>

        <!-- Captures Display -->
        <div class="flex-1 flex flex-col gap-1 mt-1 overflow-hidden">
            {#if captures.length > 0}
                <div class="flex gap-1 flex-wrap max-h-[80px] overflow-hidden">
                    {#each captures.slice(0, 6) as capture, idx}
                        {@const color = CAPTURE_COLORS[idx % CAPTURE_COLORS.length]}
                        <div
                            class="w-12 h-7 rounded border-2 flex flex-col items-center justify-center text-[7px] font-medium"
                            style="background-color: {color.bg}; border-color: {color.border}; color: {color.border};"
                            title="슬라이드 {capture.slideIndex}: ({capture.x}, {capture.y}) {capture.width}x{capture.height}"
                        >
                            <span class="font-bold">#{idx + 1}</span>
                            <span class="opacity-80">S{capture.slideIndex}</span>
                        </div>
                    {/each}
                    {#if captures.length > 6}
                        <div class="w-8 h-7 bg-gray-100 rounded border border-gray-300 flex items-center justify-center text-[8px] text-gray-500">
                            +{captures.length - 6}
                        </div>
                    {/if}
                </div>
            {:else}
                <div class="text-[9px] text-gray-400 italic">
                    캡처 영역 없음
                </div>
            {/if}

            <!-- Description -->
            {#if description}
                <div class="text-[9px] text-gray-600 truncate mt-1" title={description}>
                    {description}
                </div>
            {/if}
        </div>
    </div>

    <!-- Handles -->
    {#if !isRoot}
        <Handle
            type="target"
            position={Position.Top}
            class="!bg-gray-400 !border-gray-500 !w-2 !h-2"
        />
    {/if}
    <Handle
        type="source"
        position={Position.Bottom}
        class="!bg-gray-400 !border-gray-500 !w-2 !h-2"
    />
</div>
