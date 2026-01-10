<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";
    import { NODE_TYPE_COLORS, NODE_TYPE_NAMES, NODE_HEIGHT } from "../utils/constants";
    import type { WorkflowNode } from "$lib/api/project";

    export let id: string;
    export let data: {
        nodeId: string;
        workflowNode: WorkflowNode;
        label: string;
        isRoot?: boolean;
    };
    export let selected: boolean = false;

    $: isRoot = data.isRoot ?? false;
    $: node = data.workflowNode;
    $: colors = NODE_TYPE_COLORS.Condition;
    $: typeName = NODE_TYPE_NAMES.Condition;
</script>

<div
    class="rounded-lg border-2 shadow-sm transition-shadow duration-150 group
           {colors.bg} {colors.border}
           {selected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-md'}"
    style="width: 180px; height: {NODE_HEIGHT}px;"
>
    <!-- Type Badge -->
    <div
        class="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold text-white {colors.darkBg}"
    >
        {typeName}
    </div>

    <!-- Content Area -->
    <div class="flex flex-col p-2 pt-3 h-full justify-center overflow-hidden">
        <span class="text-sm font-semibold {colors.text} truncate" title={data.label}>
            {data.label}
        </span>
        <div class="text-[9px] text-gray-400 mt-1">
            조건 분기 노드
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
