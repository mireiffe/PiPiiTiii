<script>
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import SvelteFlowWorkflow from "$lib/components/workflow/SvelteFlowWorkflow.svelte";
    import AccordionHeader from "./AccordionHeader.svelte";

    export let isExpanded = false;
    export let workflowData;
    export let settings;
    export let savingWorkflow = false;
    export let captureMode = false;
    export let workflowTreeRef = null;

    const dispatch = createEventDispatcher();

    let workflowTextarea;

    function autoResizeTextarea() {
        if (workflowTextarea) {
            workflowTextarea.style.height = 'auto';
            workflowTextarea.style.height = Math.min(workflowTextarea.scrollHeight, 200) + 'px';
        }
    }

    function handleWorkflowGenerate(value) {
        if (value.trim()) {
            dispatch("generateWorkflow", value);
            return true;
        }
        return false;
    }

    // Check if we have a phenomenon node in the workflow
    $: hasPhenomenonNode = workflowData?.nodes && Object.values(workflowData.nodes).some(n => n.type === "Phenomenon");

    // Check if phenomenon node has no captures (show button only when no captures)
    $: phenomenonHasNoCaptures = (() => {
        if (!workflowData?.nodes) return true;
        const phenomenonNode = Object.values(workflowData.nodes).find(n => n.type === "Phenomenon");
        return !phenomenonNode?.captures || phenomenonNode.captures.length === 0;
    })();
</script>

<div
    class="border-b border-gray-200 {isExpanded
        ? 'flex-1 flex flex-col min-h-0'
        : ''}"
>
    <AccordionHeader
        icon="🔄"
        title="워크플로우"
        {isExpanded}
        savingIndicator={savingWorkflow}
        on:click={() => dispatch("toggleExpand")}
    />

    {#if isExpanded}
        <div
            transition:slide={{ duration: 200, axis: "y" }}
            class="border-t border-gray-100 bg-gray-50/30 flex-1 flex flex-col min-h-[350px]"
        >
            <div class="flex-1 overflow-hidden">
                <SvelteFlowWorkflow
                    bind:this={workflowTreeRef}
                    workflow={workflowData}
                    workflowActions={settings.workflow_actions || []}
                    readonly={false}
                    on:change={(e) => dispatch("workflowChange", e.detail)}
                    on:nodeSelect
                    on:requestCaptureMode={() => dispatch('toggleCaptureMode')}
                />
            </div>
            <div class="px-4 py-3 bg-white border-t border-gray-100">
                {#if captureMode}
                    <!-- Always show when in capture mode to allow exiting -->
                    <div class="mb-3">
                        <button
                            class="w-full py-2 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-2 transition-all bg-red-500 text-white hover:bg-red-600"
                            on:click={() => dispatch('toggleCaptureMode')}
                        >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                      d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                            캡처 모드 종료
                        </button>
                        <p class="text-[10px] text-red-500 mt-1 text-center">
                            캔버스에서 마우스 좌클릭+드래그로 영역을 선택하세요
                        </p>
                    </div>
                {:else if hasPhenomenonNode && phenomenonHasNoCaptures}
                    <!-- Show capture button only when phenomenon node has no captures -->
                    <div class="mb-3">
                        <button
                            class="w-full py-2 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-2 transition-all bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300"
                            on:click={() => dispatch('toggleCaptureMode')}
                        >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                      d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                            발생 현상 캡처하기
                        </button>
                        <p class="text-[10px] text-gray-400 mt-1 text-center">
                            캡처가 있으면 발생현상 노드 우클릭으로 추가 가능
                        </p>
                    </div>
                {/if}
                {#if !workflowData}
                    <span class="text-[10px] text-red-400 block mb-2">
                        워크플로우가 없습니다
                    </span>
                {/if}
            </div>
        </div>
    {/if}
</div>
