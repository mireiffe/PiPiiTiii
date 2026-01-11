<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { WorkflowData, WorkflowNode, SlideCapture } from "$lib/api/project";
    import { CAPTURE_COLORS } from "$lib/api/project";

    export let nodeId: string;
    export let node: WorkflowNode;
    export let workflow: WorkflowData;
    export let captureMode: boolean = false;

    const dispatch = createEventDispatcher();

    $: captures = node.captures || [];
    $: description = node.description || '';

    function updateWorkflow(updatedWorkflow: WorkflowData) {
        dispatch('change', updatedWorkflow);
    }

    function handleDescriptionChange(event: Event) {
        const target = event.target as HTMLTextAreaElement;
        const updated = JSON.parse(JSON.stringify(workflow));
        if (updated.nodes[nodeId]) {
            updated.nodes[nodeId].description = target.value;
            updateWorkflow(updated);
        }
    }

    function removeCapture(index: number) {
        const updated = JSON.parse(JSON.stringify(workflow));
        if (updated.nodes[nodeId]?.captures) {
            updated.nodes[nodeId].captures.splice(index, 1);
            updateWorkflow(updated);
        }
    }

    function toggleCaptureMode() {
        dispatch('requestCaptureMode');
    }
</script>

<div class="h-full flex flex-col">
    <!-- Section 1: Capture Collection -->
    <section class="flex-1 border-b border-gray-200 overflow-hidden flex flex-col">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <div class="flex items-center justify-between">
                <h3 class="text-sm font-semibold text-gray-700">
                    PPT 영역 캡처
                </h3>
                <button
                    class="px-3 py-1.5 text-xs font-medium rounded transition-colors
                           {captureMode
                               ? 'bg-red-500 text-white hover:bg-red-600'
                               : 'bg-blue-500 text-white hover:bg-blue-600'}"
                    on:click={toggleCaptureMode}
                >
                    {captureMode ? '캡처 모드 종료' : '캡처 모드 시작'}
                </button>
            </div>
            {#if captureMode}
                <p class="text-xs text-red-600 mt-2">
                    캔버스에서 마우스 좌클릭+드래그로 영역을 선택하세요
                </p>
            {/if}
        </div>

        <div class="flex-1 overflow-y-auto p-4">
            {#if captures.length === 0}
                <div class="text-center py-8 text-gray-400">
                    <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p class="text-sm">캡처된 영역이 없습니다</p>
                    <p class="text-xs mt-1">캡처 모드를 시작하여 PPT에서 영역을 선택하세요</p>
                </div>
            {:else}
                <div class="space-y-2">
                    {#each captures as capture, idx}
                        {@const color = CAPTURE_COLORS[idx % CAPTURE_COLORS.length]}
                        <div class="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200 group hover:shadow-sm transition-shadow">
                            <!-- Color indicator -->
                            <div
                                class="w-8 h-8 rounded-lg border-2 flex items-center justify-center text-xs font-bold shrink-0"
                                style="background-color: {color.bg}; border-color: {color.border}; color: {color.border};"
                            >
                                {idx + 1}
                            </div>

                            <!-- Capture info -->
                            <div class="flex-1 min-w-0">
                                <div class="text-sm font-medium text-gray-800">
                                    슬라이드 {capture.slideIndex + 1}
                                </div>
                                <div class="text-xs text-gray-500 mt-0.5">
                                    위치: ({capture.x}, {capture.y}) | 크기: {capture.width} x {capture.height}
                                </div>
                            </div>

                            <!-- Delete button -->
                            <button
                                class="w-7 h-7 flex items-center justify-center rounded text-gray-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                                on:click={() => removeCapture(idx)}
                                title="캡처 삭제"
                            >
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </section>

    <!-- Section 2: Description -->
    <section class="flex-1 overflow-hidden flex flex-col">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 class="text-sm font-semibold text-gray-700">
                현상 설명
            </h3>
        </div>

        <div class="flex-1 p-4">
            <textarea
                class="w-full h-full resize-none border border-gray-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-shadow"
                placeholder="발생한 현상에 대해 설명하세요..."
                value={description}
                on:input={handleDescriptionChange}
            ></textarea>
        </div>
    </section>
</div>
