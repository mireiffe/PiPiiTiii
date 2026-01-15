<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { WorkflowAction } from "$lib/api/project";
    import { CAPTURE_COLORS } from "$lib/api/project";
    import {
        type LayoutNode,
        NODE_WIDTH,
        NODE_HEIGHT,
        NODE_TYPE_NAMES,
        NODE_TYPE_COLORS,
        getNodeDisplayName,
        getNodeParams,
    } from "./workflowTreeLayout";

    export let layoutNode: LayoutNode;
    export let workflowActions: WorkflowAction[] = [];
    export let isSelected = false;
    export let isDraggingThis = false;

    const dispatch = createEventDispatcher<{
        dragstart: { event: MouseEvent; nodeId: string };
        contextmenu: { event: MouseEvent; nodeId: string };
    }>();

    $: colors = NODE_TYPE_COLORS[layoutNode.node.type];
    $: displayName = getNodeDisplayName(layoutNode.node, workflowActions);
    $: params = getNodeParams(layoutNode.node, workflowActions);
</script>

<div
    class="absolute rounded-lg border-2 shadow-sm transition-shadow duration-150 group node-element
           {colors.bg} {colors.border}
           {isSelected ? 'ring-2 ring-blue-500 z-10 shadow-lg' : 'hover:shadow-md'}
           {isDraggingThis ? 'opacity-40' : ''}"
    style="left: {layoutNode.x}px; top: {layoutNode.y}px; width: {NODE_WIDTH}px; height: {layoutNode.height}px;"
    on:mousedown={(e) => dispatch("dragstart", { event: e, nodeId: layoutNode.id })}
    on:contextmenu={(e) => dispatch("contextmenu", { event: e, nodeId: layoutNode.id })}
>
    <!-- Node Type Badge -->
    <div class="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold text-white {colors.darkBg}">
        {NODE_TYPE_NAMES[layoutNode.node.type]}
    </div>

    <div class="flex flex-col p-2 pt-3 h-full justify-between overflow-hidden">
        <!-- Node Name -->
        <span class="text-sm font-semibold {colors.text} truncate" title={displayName}>
            {displayName}
        </span>

        {#if layoutNode.node.type === "Phenomenon"}
            <!-- Phenomenon node: show captures -->
            <div class="flex-1 flex flex-col gap-1 mt-1 overflow-hidden">
                {#if layoutNode.node.captures && layoutNode.node.captures.length > 0}
                    <div class="flex gap-1 flex-wrap max-h-[50px] overflow-hidden">
                        {#each layoutNode.node.captures.slice(0, 6) as capture, idx}
                            {@const color = CAPTURE_COLORS[idx % CAPTURE_COLORS.length]}
                            <div
                                class="w-12 h-7 rounded border-2 flex flex-col items-center justify-center text-[7px] font-medium"
                                style="background-color: {color.bg}; border-color: {color.border}; color: {color.border};"
                                title="슬라이드 {capture.slideIndex}: ({capture.x}, {capture.y}) {capture.width}×{capture.height}"
                            >
                                <span class="font-bold">#{idx + 1}</span>
                                <span class="opacity-80">S{capture.slideIndex}</span>
                            </div>
                        {/each}
                        {#if layoutNode.node.captures.length > 6}
                            <div class="w-8 h-7 bg-gray-100 rounded border border-gray-300 flex items-center justify-center text-[8px] text-gray-500">
                                +{layoutNode.node.captures.length - 6}
                            </div>
                        {/if}
                    </div>
                {:else}
                    <div class="text-[9px] text-gray-400 italic">캡처 영역 없음</div>
                {/if}
                {#if layoutNode.node.description}
                    <div class="text-[9px] text-gray-600 truncate" title={layoutNode.node.description}>
                        {layoutNode.node.description}
                    </div>
                {/if}
            </div>
        {:else if layoutNode.node.type === "Action"}
            <!-- Action node: show params -->
            <div class="text-[9px] text-gray-500 overflow-hidden">
                {#each params.slice(0, 2) as p}
                    <div class="truncate">
                        <span class="font-bold">{p.name}:</span> {p.value}
                    </div>
                {/each}
                {#if params.length > 2}
                    <div>+{params.length - 2} more</div>
                {/if}
            </div>
        {/if}
    </div>
</div>
