<script lang="ts">
    import { createEventDispatcher } from "svelte";

    // Capture can be StepCapture or CoreStepPresetValue.captureValue
    export let capture: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
        label?: string;
        id?: string; // optional for CoreStepItem
    };
    export let projectId: string = "";
    export let slideWidth: number = 960;
    export let slideHeight: number = 540;
    export let showRecaptureButton = false;

    const dispatch = createEventDispatcher<{
        remove: void;
        recapture: void;
    }>();

    $: thumbUrl = `/api/results/${projectId}/thumbnails/slide_${String(capture.slideIndex + 1).padStart(3, "0")}_thumb.png`;
    $: maxWidth = 140;
    $: maxHeight = 100;
    $: scaleByWidth = maxWidth / capture.width;
    $: scaleByHeight = maxHeight / capture.height;
    $: scale = Math.min(scaleByWidth, scaleByHeight);
    $: previewWidth = capture.width * scale;
    $: previewHeight = capture.height * scale;
    $: bgWidth = slideWidth * scale;
    $: bgHeight = slideHeight * scale;
    $: bgPosX = -capture.x * scale;
    $: bgPosY = -capture.y * scale;
</script>

<div
    class="flex flex-col gap-1.5 p-2 bg-green-50 border border-green-200 rounded group"
>
    <!-- Capture preview thumbnail -->
    <div class="relative flex justify-center">
        <div
            class="rounded border border-green-300 overflow-hidden shadow-sm"
            style="
                width: {previewWidth}px;
                height: {previewHeight}px;
                background-image: url({thumbUrl});
                background-size: {bgWidth}px {bgHeight}px;
                background-position: {bgPosX}px {bgPosY}px;
                background-repeat: no-repeat;
                background-color: #f0fdf4;
            "
            title="슬라이드 {capture.slideIndex + 1} ({Math.round(
                capture.x,
            )}, {Math.round(capture.y)}) {Math.round(
                capture.width,
            )}x{Math.round(capture.height)}"
        ></div>
        <span
            class="absolute bottom-1 left-1 text-[9px] bg-green-600 text-white px-1 py-0.5 rounded shadow"
        >
            S{capture.slideIndex + 1}
        </span>
    </div>
    <div class="flex gap-1">
        {#if showRecaptureButton}
            <button
                class="text-[10px] text-gray-500 hover:text-green-600 px-1.5 py-0.5 border border-gray-200 rounded hover:border-green-300 transition flex-1"
                on:click={() => dispatch("recapture")}
            >
                다시 캡처
            </button>
        {/if}
        <button
            class="text-[10px] text-red-500 hover:text-red-700 px-1.5 py-0.5 {showRecaptureButton
                ? ''
                : 'flex-1 border border-gray-200 rounded hover:border-red-300 transition'}"
            on:click={() => dispatch("remove")}
        >
            삭제
        </button>
    </div>
</div>
