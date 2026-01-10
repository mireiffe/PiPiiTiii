<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";
    import { NODE_TYPE_COLORS, NODE_TYPE_NAMES, NODE_HEIGHT } from "../utils/constants";
    import type { WorkflowNode, WorkflowAction } from "$lib/api/project";
    import { getContext } from "svelte";

    export let id: string;
    export let data: {
        nodeId: string;
        workflowNode: WorkflowNode;
        label: string;
        isRoot?: boolean;
    };
    export let selected: boolean = false;

    // Get workflow actions from context (provided by parent SvelteFlowWorkflow)
    const workflowActions = getContext<WorkflowAction[]>("workflowActions") || [];

    $: isRoot = data.isRoot ?? false;
    $: node = data.workflowNode;
    $: colors = NODE_TYPE_COLORS.Action;
    $: typeName = NODE_TYPE_NAMES.Action;

    // Get action info for this node
    $: actionInfo = node.actionId
        ? workflowActions.find((a) => a.id === node.actionId)
        : null;

    // Get display params
    $: params = getNodeParams(node);

    function getNodeParams(n: WorkflowNode): Array<{ name: string; value: string }> {
        if (!n.params) return [];
        return Object.entries(n.params).map(([key, value]) => {
            const paramInfo = actionInfo?.params?.find((p) => p.id === key);
            return {
                name: paramInfo?.name || key,
                value: value || "-",
            };
        });
    }
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
    <div class="flex flex-col p-2 pt-3 h-full justify-between overflow-hidden">
        <span class="text-sm font-semibold {colors.text} truncate" title={data.label}>
            {data.label}
        </span>

        <!-- Parameters Display -->
        <div class="text-[9px] text-gray-500 overflow-hidden">
            {#each params.slice(0, 2) as p}
                <div class="truncate">
                    <span class="font-bold">{p.name}:</span>
                    {p.value}
                </div>
            {/each}
            {#if params.length > 2}
                <div class="text-gray-400">+{params.length - 2} more</div>
            {/if}
            {#if params.length === 0}
                <div class="text-gray-400 italic">파라미터 없음</div>
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
    <!-- Action nodes typically don't have children, but keep handle for consistency -->
    <Handle
        type="source"
        position={Position.Bottom}
        class="!bg-gray-400 !border-gray-500 !w-2 !h-2 !opacity-30"
    />
</div>
