<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import PhenomenonCollector from "$lib/components/phenomenon/PhenomenonCollector.svelte";
    import type { PhenomenonData } from "$lib/types/phenomenon";
    import { createEmptyPhenomenon } from "$lib/types/phenomenon";

    export let isExpanded = false;
    export let phenomenonData: PhenomenonData = createEmptyPhenomenon();
    export let savingWorkflow = false;
    export let captureMode = false;
    export let phenomenonAttributes: { key: string; name: string; value: string; source?: string }[] = [];

    const dispatch = createEventDispatcher();

    let phenomenonCollectorRef: PhenomenonCollector;

    // 발생현상 데이터 변경 핸들러
    function handlePhenomenonChange(event: CustomEvent<PhenomenonData>) {
        dispatch("phenomenonChange", event.detail);
    }

    // 캡처 모드 토글
    function handleToggleCaptureMode() {
        dispatch('toggleCaptureMode');
    }

    // 증거 호버 이벤트 전달
    function handleEvidenceHover(event: CustomEvent<{ evidenceId: string | null }>) {
        dispatch('evidenceHover', event.detail);
    }

    // 캡처 추가 (ViewerCanvas에서 호출)
    export function addCapture(capture: { slideIndex: number; x: number; y: number; width: number; height: number }) {
        if (phenomenonCollectorRef) {
            phenomenonCollectorRef.addCapture(capture);
        }
    }

    // 캡처 오버레이 데이터 반환
    export function getCaptureOverlays() {
        if (phenomenonCollectorRef) {
            return phenomenonCollectorRef.getCaptureOverlays();
        }
        return [];
    }
</script>

<div
    class="border-b border-gray-200 {isExpanded
        ? 'flex-1 flex flex-col min-h-0'
        : ''}"
>
    <AccordionHeader
        icon="🔍"
        title="발생현상 수집"
        {isExpanded}
        savingIndicator={savingWorkflow}
        on:click={() => dispatch("toggleExpand")}
    />

    {#if isExpanded}
        <div
            transition:slide={{ duration: 200, axis: "y" }}
            class="border-t border-gray-100 bg-gray-50/30 flex-1 flex flex-col min-h-[350px] overflow-hidden"
        >
            <PhenomenonCollector
                bind:this={phenomenonCollectorRef}
                phenomenon={phenomenonData}
                {captureMode}
                {phenomenonAttributes}
                on:change={handlePhenomenonChange}
                on:toggleCaptureMode={handleToggleCaptureMode}
                on:evidenceHover={handleEvidenceHover}
            />
        </div>
    {/if}
</div>
