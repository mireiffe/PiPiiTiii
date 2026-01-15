<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import type { WorkflowNode, WorkflowAction, WorkflowData } from "$lib/api/project";
    import { CAPTURE_COLORS } from "$lib/api/project";
    import { NODE_TYPE_NAMES } from "./workflowTreeLayout";

    export let selectedNode: WorkflowNode | null = null;
    export let selectedNodeId: string | null = null;
    export let workflow: WorkflowData | null = null;
    export let workflowActions: WorkflowAction[] = [];

    const dispatch = createEventDispatcher<{
        close: void;
        updateName: { nodeId: string; name: string };
        updateDescription: { nodeId: string; description: string };
        updateType: { nodeId: string; newType: string };
        updateAction: { nodeId: string; actionId: string };
        updateParam: { nodeId: string; paramId: string; value: string };
        removeCapture: { nodeId: string; captureIndex: number };
        deleteNode: { nodeId: string };
    }>();

    $: selectedAction = selectedNode?.type === "Action" && selectedNode.actionId
        ? workflowActions.find((a) => a.id === selectedNode!.actionId)
        : undefined;
</script>

{#if selectedNode && workflow}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
        class="absolute bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-3 shadow-lg z-30 max-h-[250px] overflow-y-auto"
        transition:slide={{ duration: 200 }}
        on:click|stopPropagation
        on:mousedown|stopPropagation
    >
        <div class="flex items-center justify-between mb-3">
            <h3 class="font-bold text-gray-800 text-sm flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                노드 설정
            </h3>
            <button class="text-gray-400 hover:text-gray-600" on:click={() => dispatch("close")}>✕</button>
        </div>

        {#if selectedNode.type === "Phenomenon"}
            <!-- Phenomenon node settings -->
            <div class="space-y-3">
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">타입</label>
                    <div class="text-sm font-medium text-red-600">
                        {NODE_TYPE_NAMES[selectedNode.type]}
                    </div>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">현상 설명</label>
                    <textarea
                        class="w-full text-sm border rounded px-2 py-1.5 resize-none"
                        rows="2"
                        placeholder="발생한 현상을 설명하세요..."
                        value={selectedNode.description || ""}
                        on:change={(e) => dispatch("updateDescription", { nodeId: selectedNodeId!, description: e.currentTarget.value })}
                    ></textarea>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">
                        캡처 영역 ({selectedNode.captures?.length || 0}개)
                    </label>
                    <p class="text-[10px] text-gray-400 mb-2">
                        캔버스에서 마우스 좌클릭+드래그로 캡처 영역을 지정하세요
                    </p>
                    {#if selectedNode.captures && selectedNode.captures.length > 0}
                        <div class="space-y-1.5 max-h-[100px] overflow-y-auto pr-1">
                            {#each selectedNode.captures as capture, idx}
                                {@const color = CAPTURE_COLORS[idx % CAPTURE_COLORS.length]}
                                <div class="flex items-center gap-2 group">
                                    <div
                                        class="w-6 h-6 rounded border-2 flex items-center justify-center text-[10px] font-bold shrink-0"
                                        style="background-color: {color.bg}; border-color: {color.border}; color: {color.border};"
                                    >
                                        {idx + 1}
                                    </div>
                                    <div class="flex-1 text-[10px] text-gray-600 min-w-0">
                                        <span class="font-medium">슬라이드 {capture.slideIndex}</span>
                                        <span class="text-gray-400 ml-1">({capture.x}, {capture.y}) {capture.width}×{capture.height}</span>
                                    </div>
                                    <button
                                        class="w-5 h-5 bg-red-100 text-red-500 rounded text-[10px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center hover:bg-red-200 shrink-0"
                                        on:click={() => dispatch("removeCapture", { nodeId: selectedNodeId!, captureIndex: idx })}
                                        title="캡처 삭제"
                                    >×</button>
                                </div>
                            {/each}
                        </div>
                    {:else}
                        <div class="text-xs text-gray-400 italic py-2">캡처된 영역이 없습니다</div>
                    {/if}
                </div>
            </div>
        {:else}
            <!-- Other node types settings -->
            <div class="grid grid-cols-2 gap-4">
                <div class="space-y-3">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">타입</label>
                        {#if selectedNodeId === workflow.rootId}
                            <div class="text-sm font-medium">{NODE_TYPE_NAMES[selectedNode.type]}</div>
                        {:else}
                            <select
                                class="w-full text-sm border rounded px-2 py-1.5"
                                value={selectedNode.type}
                                on:change={(e) => dispatch("updateType", { nodeId: selectedNodeId!, newType: e.currentTarget.value })}
                            >
                                <option value="Sequence">원인 후보 분석 (Sequence)</option>
                                <option value="Selector">원인 도출 (Selector)</option>
                                <option value="Condition">분기 (Condition)</option>
                                <option value="Action">액션 (Action)</option>
                            </select>
                        {/if}
                    </div>

                    {#if selectedNode.type !== "Action"}
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">이름</label>
                            <input
                                type="text"
                                class="w-full text-sm border rounded px-2 py-1.5"
                                value={selectedNode.name || ""}
                                on:change={(e) => dispatch("updateName", { nodeId: selectedNodeId!, name: e.currentTarget.value })}
                            />
                        </div>
                    {:else}
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">액션</label>
                            <select
                                class="w-full text-sm border rounded px-2 py-1.5"
                                value={selectedNode.actionId || ""}
                                on:change={(e) => dispatch("updateAction", { nodeId: selectedNodeId!, actionId: e.currentTarget.value })}
                            >
                                {#each workflowActions as action}
                                    <option value={action.id}>{action.name}</option>
                                {/each}
                            </select>
                        </div>
                    {/if}
                </div>

                <div class="space-y-3">
                    {#if selectedNode.type === "Action" && selectedAction}
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">파라미터</label>
                            <div class="space-y-2 max-h-[120px] overflow-y-auto pr-1">
                                {#each selectedAction.params as param}
                                    <div class="flex flex-col gap-0.5">
                                        <span class="text-[10px] text-gray-400">
                                            {param.name}{#if param.required}*{/if}
                                        </span>
                                        <input
                                            type="text"
                                            class="w-full text-xs border rounded px-2 py-1"
                                            value={selectedNode.params?.[param.id] || ""}
                                            on:change={(e) => dispatch("updateParam", { nodeId: selectedNodeId!, paramId: param.id, value: e.currentTarget.value })}
                                        />
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {:else if selectedNodeId !== workflow.rootId}
                        <div class="flex items-end h-full">
                            <button
                                class="w-full py-2 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded border border-red-200"
                                on:click={() => dispatch("deleteNode", { nodeId: selectedNodeId! })}
                            >
                                노드 삭제
                            </button>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
{/if}
