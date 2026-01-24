<script lang="ts">
    import { createEventDispatcher } from "svelte";

    export let workflowId: string | null = null;

    const dispatch = createEventDispatcher<{
        delete: { workflowId: string };
    }>();

    function handleDelete() {
        if (!workflowId) return;

        if (
            confirm(
                "이 워크플로우 데이터를 삭제하시겠습니까?\n삭제된 데이터는 복구할 수 없습니다.",
            )
        ) {
            dispatch("delete", { workflowId });
        }
    }
</script>

<div
    class="flex-1 flex flex-col items-center justify-center p-8 bg-red-50/50"
>
    <div class="text-center max-w-sm">
        <div
            class="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center"
        >
            <svg class="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path
                    fill-rule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clip-rule="evenodd"
                />
            </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900 mb-2">
            정의되지 않은 워크플로우
        </h3>
        <p class="text-sm text-gray-600 mb-6">
            이 워크플로우는 설정에서 삭제되었지만 프로젝트에 데이터가 남아 있습니다.
            <br />더 이상 필요하지 않다면 삭제할 수 있습니다.
        </p>
        <div class="flex flex-col gap-2">
            <button
                type="button"
                class="w-full px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                on:click={handleDelete}
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                </svg>
                워크플로우 데이터 삭제
            </button>
            <p class="text-xs text-gray-500 mt-2">
                워크플로우 ID: <code class="bg-gray-200 px-1 rounded"
                    >{workflowId}</code
                >
            </p>
        </div>
    </div>
</div>
