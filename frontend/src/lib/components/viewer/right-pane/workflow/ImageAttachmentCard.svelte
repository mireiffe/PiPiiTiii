<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { getAttachmentImageUrl } from "$lib/api/project";

    export let imageId: string;
    export let caption: string | undefined = undefined;

    const dispatch = createEventDispatcher<{
        click: void;
        remove: void;
    }>();
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
    class="relative group cursor-pointer"
    on:click={() => dispatch("click")}
    title="클릭하여 캡션 편집"
>
    <img
        src={getAttachmentImageUrl(imageId)}
        alt="첨부된 이미지"
        class="w-full max-h-32 object-contain rounded border border-gray-200 bg-gray-50 hover:border-blue-300 transition"
    />
    {#if caption}
        <div
            class="mt-1 px-1.5 py-0.5 bg-gray-50 rounded border border-gray-200 text-[10px] text-gray-600 truncate"
        >
            {caption}
        </div>
    {/if}
    <div
        class="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
    >
        <button
            class="w-5 h-5 bg-blue-500 text-white rounded-full flex items-center justify-center hover:bg-blue-600 transition text-xs shadow"
            on:click|stopPropagation={() => dispatch("click")}
            title="캡션 편집"
        >
            <svg
                class="w-2.5 h-2.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                />
            </svg>
        </button>
        <button
            class="w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition text-xs shadow"
            on:click|stopPropagation={() => dispatch("remove")}
            title="이미지 삭제"
        >
            ×
        </button>
    </div>
</div>
