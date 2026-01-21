<script>
    import Button from "$lib/components/ui/Button.svelte";
    import { createEventDispatcher } from "svelte";

    export let historyIndex;
    export let historyLength;
    export let isDirty;
    export let saving;
    export let allowEdit;
    export let useThumbnails;
    export let loadingSettings;
    export let downloading;
    export let scale;
    export let project = null;
    export let showOverlays = true;

    const dispatch = createEventDispatcher();

    $: pptFileName = project?.ppt_path?.split("\\").pop() || "Loading...";
</script>

<div
    class="bg-white border-b border-gray-200 flex flex-col shrink-0 z-10"
>
    <!-- Top row: PPT Title -->
    <div class="px-4 py-2 border-b border-gray-100">
        <h1
            class="font-bold text-gray-800 text-base"
            title={pptFileName}
        >
            {pptFileName}
        </h1>
    </div>

    <!-- Bottom row: Controls -->
    <div class="min-h-[3rem] h-auto flex flex-wrap items-center justify-between px-4 py-2 gap-2">
    <!-- Left side: Edit controls -->
    <div class="flex items-center gap-4 min-w-0">
    {#if allowEdit}
        <div class="flex items-center space-x-2">
            <Button
                variant="ghost"
                size="sm"
                disabled={historyIndex <= 0}
                on:click={() => dispatch("undo")}
                title="Undo (Ctrl+Z)"
            >
                ↩️ Undo
            </Button>
            <Button
                variant="ghost"
                size="sm"
                disabled={historyIndex >= historyLength - 1}
                on:click={() => dispatch("redo")}
                title="Redo (Ctrl+Y)"
            >
                ↪️ Redo
            </Button>
            <div class="w-px h-6 bg-gray-300 mx-2"></div>
            <Button
                variant="primary"
                size="sm"
                disabled={!isDirty || saving}
                loading={saving}
                on:click={() => dispatch("saveState")}
            >
                {saving ? "Saving..." : "Save State"}
            </Button>
            <Button
                variant="secondary"
                size="sm"
                on:click={() => dispatch("reset")}
            >
                Reset
            </Button>
        </div>
    {/if}
    </div>

    <div class="flex items-center space-x-2 shrink-0">
        <Button
            variant="secondary"
            size="sm"
            on:click={() => dispatch("toggleThumbnailView")}
            disabled={loadingSettings}
            title={useThumbnails ? "렌더링 보기로 전환" : "썸네일 보기로 전환"}
        >
            {#if useThumbnails}
                <svg
                    class="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z"
                    />
                </svg>
                <span>썸네일</span>
            {:else}
                <svg
                    class="w-3 h-3 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    /><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    /></svg
                >
                <span>렌더링</span>
            {/if}
        </Button>
        <button
            class="px-2 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1
                {showOverlays
                    ? 'bg-blue-100 text-blue-600 hover:bg-blue-200'
                    : 'bg-gray-100 text-gray-400 hover:bg-gray-200'}"
            on:click={() => dispatch("toggleOverlays")}
            title={showOverlays ? "캡쳐 오버레이 숨기기" : "캡쳐 오버레이 보기"}
        >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            <span>오버레이</span>
        </button>
        <div class="w-px h-4 bg-gray-300 mx-1"></div>
        <Button
            variant="destructive"
            size="sm"
            on:click={() => dispatch("reparseAll")}
        >
            Reparse All
        </Button>
        <Button
            variant="secondary"
            size="sm"
            on:click={() => dispatch("reparseSlide")}
        >
            Reparse Slide
        </Button>
        <Button
            variant="success"
            size="sm"
            on:click={() => dispatch("download")}
            disabled={downloading}
            loading={downloading}
        >
            Download
        </Button>
        <div class="w-px h-4 bg-gray-300 mx-2"></div>
        <button
            class="p-1 hover:bg-gray-100 rounded w-8 h-8 flex items-center justify-center transition-colors text-gray-600"
            on:click={() => dispatch("zoomIn")}
        >
            +
        </button>
        <span class="text-xs text-gray-500 w-12 text-center font-mono">
            {Math.round(scale * 100)}%
        </span>
        <button
            class="p-1 hover:bg-gray-100 rounded w-8 h-8 flex items-center justify-center transition-colors text-gray-600"
            on:click={() => dispatch("zoomOut")}
        >
            -
        </button>
    </div>
    </div>
</div>
