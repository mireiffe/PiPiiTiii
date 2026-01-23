<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { StepAttachment } from "$lib/types/workflow";

    export let attachment: StepAttachment;

    const dispatch = createEventDispatcher<{
        update: { data: string };
        remove: void;
    }>();

    let isEditing = false;
    let editValue = "";

    function startEditing() {
        editValue = attachment.data || "";
        isEditing = true;
    }

    function stopEditing() {
        if (editValue !== attachment.data) {
            dispatch("update", { data: editValue });
        }
        isEditing = false;
    }

    function handleKeydown(event: KeyboardEvent) {
        if ((event.ctrlKey || event.metaKey) && event.key === "s") {
            event.preventDefault();
            stopEditing();
        }
    }

    function handleRemove() {
        if (confirm("이 첨부를 삭제하시겠습니까?")) {
            dispatch("remove");
        }
    }

    // Auto-resize textarea action
    function autoResizeTextarea(textarea: HTMLTextAreaElement) {
        const resize = () => {
            textarea.style.height = "auto";
            textarea.style.height = textarea.scrollHeight + "px";
        };

        resize();
        textarea.addEventListener("input", resize);

        return {
            destroy() {
                textarea.removeEventListener("input", resize);
            },
        };
    }
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="relative group">
    {#if isEditing}
        <textarea
            bind:value={editValue}
            on:blur={stopEditing}
            on:keydown={handleKeydown}
            placeholder="내용 입력... (Ctrl+S로 저장)"
            class="w-full min-h-[40px] border border-blue-300 rounded px-2 py-1.5 text-[11px] focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none bg-white overflow-hidden leading-snug"
            use:autoResizeTextarea
            autofocus
        ></textarea>
    {:else}
        <div
            class="relative bg-gray-50 rounded border border-gray-100 overflow-hidden cursor-pointer hover:border-blue-300 hover:shadow-sm transition-all"
            on:click={startEditing}
            title="클릭하여 편집"
        >
            <div
                class="p-2 text-[11px] text-gray-700 leading-snug break-words w-full whitespace-pre-wrap"
            >
                {#if attachment.data && attachment.data.trim()}
                    {attachment.data}
                {:else}
                    <span class="text-gray-400 italic">클릭하여 입력...</span>
                {/if}
            </div>
            <button
                class="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition text-xs shadow opacity-0 group-hover:opacity-100"
                on:click|stopPropagation={handleRemove}
                title="삭제"
            >
                ×
            </button>
        </div>
    {/if}
</div>
