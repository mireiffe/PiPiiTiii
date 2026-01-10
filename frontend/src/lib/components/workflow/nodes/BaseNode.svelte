<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";
    import { NODE_TYPE_COLORS, NODE_TYPE_NAMES } from "../utils/constants";
    import type { WorkflowNode } from "$lib/api/project";

    export let id: string;
    export let data: {
        nodeId: string;
        workflowNode: WorkflowNode;
        label: string;
    };
    export let selected: boolean = false;
    export let isRoot: boolean = false;

    $: node = data.workflowNode;
    $: colors = NODE_TYPE_COLORS[node.type] || NODE_TYPE_COLORS.Action;
    $: typeName = NODE_TYPE_NAMES[node.type] || node.type;
</script>

<div
    class="rounded-lg border-2 shadow-sm transition-shadow duration-150 group
           {colors.bg} {colors.border}
           {selected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-md'}"
    style="min-width: 180px;"
>
    <!-- Type Badge -->
    <div
        class="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold text-white {colors.darkBg}"
    >
        {typeName}
    </div>

    <!-- Content Area (to be filled by extending components) -->
    <div class="flex flex-col p-2 pt-3 h-full justify-between overflow-hidden">
        <slot name="content">
            <span class="text-sm font-semibold {colors.text} truncate" title={data.label}>
                {data.label}
            </span>
        </slot>
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
