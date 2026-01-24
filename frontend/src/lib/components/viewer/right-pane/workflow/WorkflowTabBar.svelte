<script lang="ts">
    import { createEventDispatcher } from "svelte";

    export let workflows: { id: string; name: string }[] = [];
    export let undefinedWorkflowIds: string[] = [];
    export let activeWorkflowId: string | null = null;

    const dispatch = createEventDispatcher<{
        selectTab: { workflowId: string };
    }>();

    function handleSelect(workflowId: string) {
        dispatch("selectTab", { workflowId });
    }
</script>

{#if workflows.length > 0 || undefinedWorkflowIds.length > 0}
    <div
        class="flex border-b border-gray-200 bg-gray-50 px-2 pt-2 gap-1 overflow-x-auto shrink-0"
    >
        {#each workflows as workflow (workflow.id)}
            <button
                class="px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors whitespace-nowrap
                {activeWorkflowId === workflow.id
                    ? 'bg-white text-blue-600 border border-b-0 border-gray-200 -mb-px'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'}"
                on:click={() => handleSelect(workflow.id)}
            >
                {workflow.name}
            </button>
        {/each}

        <!-- Undefined Workflow Tabs (deleted from settings but still have data) -->
        {#each undefinedWorkflowIds as undefinedWfId (undefinedWfId)}
            <button
                class="px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors whitespace-nowrap flex items-center gap-1.5
                {activeWorkflowId === undefinedWfId
                    ? 'bg-red-50 text-red-600 border border-b-0 border-red-200 -mb-px'
                    : 'text-red-400 hover:text-red-600 hover:bg-red-50 border border-transparent'}"
                on:click={() => handleSelect(undefinedWfId)}
                title="정의되지 않은 워크플로우 - 클릭하여 삭제"
            >
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path
                        fill-rule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                        clip-rule="evenodd"
                    />
                </svg>
                정의되지 않음
            </button>
        {/each}

        <a
            href="/settings#section-workflows"
            class="px-2 py-1.5 text-xs text-gray-400 hover:text-blue-500 transition-colors"
            title="워크플로우 추가"
        >
            +
        </a>
    </div>
{/if}
