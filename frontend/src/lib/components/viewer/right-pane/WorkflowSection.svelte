<script>
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import WorkflowTree from "$lib/components/WorkflowTree.svelte";
    import AccordionHeader from "./AccordionHeader.svelte";

    export let isExpanded = false;
    export let workflowData;
    export let settings;
    export let savingWorkflow = false;

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
                <WorkflowTree
                    workflow={workflowData}
                    workflowActions={settings.workflow_actions || []}
                    readonly={false}
                    on:change={(e) => dispatch("workflowChange", e.detail)}
                />
            </div>
            <div class="px-4 py-3 bg-white border-t border-gray-100">
                {#if !workflowData}
                    <span class="text-[10px] text-red-400 block mb-2">
                        워크플로우가 없습니다
                    </span>
                {/if}
                <div class="relative">
                    <textarea
                        bind:this={workflowTextarea}
                        class="w-full text-xs p-2.5 pr-10 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none bg-gray-50 focus:bg-white transition-colors overflow-hidden"
                        rows="1"
                        placeholder="예: 검사 노드 추가해줘, 분석 파라미터를 필수로 변경해줘..."
                        on:input={autoResizeTextarea}
                        on:keydown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                if (handleWorkflowGenerate(e.currentTarget.value)) {
                                    e.currentTarget.value = "";
                                    autoResizeTextarea();
                                }
                            }
                        }}
                    ></textarea>
                    <button
                        class="absolute right-2 bottom-2 text-blue-500 hover:text-blue-600 disabled:opacity-50"
                        title="전송"
                        on:click={(e) => {
                            const textarea = e.currentTarget.previousElementSibling;
                            if (handleWorkflowGenerate(textarea.value)) {
                                textarea.value = "";
                                autoResizeTextarea();
                            }
                        }}
                    >
                        <svg
                            class="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                            />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    {/if}
</div>
