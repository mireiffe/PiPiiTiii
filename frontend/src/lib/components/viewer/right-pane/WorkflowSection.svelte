<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import PhenomenonCollector from "$lib/components/phenomenon/PhenomenonCollector.svelte";
    import CandidateCauseExplorer from "$lib/components/phenomenon/CandidateCauseExplorer.svelte";
    import CauseDerivationExplorer from "$lib/components/phenomenon/CauseDerivationExplorer.svelte";
    import type { PhenomenonData } from "$lib/types/phenomenon";
    import {
        createEmptyPhenomenon,
        createCaptureEvidence,
    } from "$lib/types/phenomenon";

    export let isExpanded = false;
    export let phenomenonData: PhenomenonData = createEmptyPhenomenon();
    export let savingWorkflow = false;
    export let captureMode = false;
    export let phenomenonAttributes: {
        key: string;
        name: string;
        value: string;
        source?: string;
    }[] = [];
    export let workflowActions: { id: string; name: string; params: any[] }[] = [];
    export let workflowConditions: { id: string; name: string; params: any[] }[] = [];

    const dispatch = createEventDispatcher();

    import WorkflowGraph from "$lib/components/phenomenon/WorkflowGraph.svelte"; // [NEW]

    let phenomenonCollectorRef: PhenomenonCollector;
    let candidateCauseExplorerRef: CandidateCauseExplorer;
    let currentStep = 0; // 0: Phenomenon, 1: Candidate Causes, 2: Cause Derivation
    let viewMode: "list" | "graph" = "list"; // [NEW]

    const STEPS = [
        { id: 0, title: "발생현상" },
        { id: 1, title: "원인후보" },
        { id: 2, title: "원인도출" },
    ];

    // 발생현상 데이터 변경 핸들러
    function handlePhenomenonChange(event: CustomEvent<PhenomenonData>) {
        dispatch("phenomenonChange", event.detail);
    }

    // 워크플로우 완료 핸들러
    function handleWorkflowComplete(event: CustomEvent<{ finalCauseId: string }>) {
        // Switch to graph view when workflow is completed
        viewMode = "graph";
        dispatch("phenomenonChange", phenomenonData);
    }

    // 캡처 모드 토글
    function handleToggleCaptureMode() {
        dispatch("toggleCaptureMode");
    }

    // 증거 호버 이벤트 전달
    function handleEvidenceHover(
        event: CustomEvent<{ evidenceId: string | null }>,
    ) {
        dispatch("evidenceHover", event.detail);
    }

    // Handle linking mode change from CandidateCauseExplorer
    function handleLinkingModeChange(
        event: CustomEvent<{
            isLinking: boolean;
            causeId: string | null;
            linkedEvidenceIds: string[];
        }>,
    ) {
        dispatch("linkingModeChange", event.detail);
    }

    // Handle evidence click from ViewerCanvas (via parent)
    export function handleEvidenceClick(evidenceId: string) {
        if (currentStep === 1 && candidateCauseExplorerRef) {
            candidateCauseExplorerRef.toggleEvidenceLink(evidenceId);
        }
    }

    // 캡처 추가 (ViewerCanvas에서 호출)
    export function addCapture(capture: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
    }) {
        // 데이터 직접 수정
        const newEvidence = createCaptureEvidence(
            capture.slideIndex,
            capture.x,
            capture.y,
            capture.width,
            capture.height,
        );

        const newData = {
            ...phenomenonData,
            evidences: [...phenomenonData.evidences, newEvidence],
        };

        dispatch("phenomenonChange", newData);

        // 만약 다른 스텝에 있다면 발생현상 탭으로 이동하여 캡처 확인 유도 (선택사항)
        if (currentStep !== 0) {
            // currentStep = 0;
            // 굳이 이동 안해도 될듯, 하지만 사용자 경험상 캡처했으면 보는게 나을수도.
            // 일단 유지.
        }
    }

    // 캡처 오버레이 데이터 반환
    export function getCaptureOverlays() {
        // 데이터 기반으로 생성 (컴포넌트 의존성 제거)
        if (!phenomenonData || !phenomenonData.evidences) return [];
        return phenomenonData.evidences
            .filter((e) => e.type === "capture")
            .map((e, index) => ({
                ...e,
                colorIndex: index,
            }));
    }

    function setStep(step: number) {
        // Disabled check removed for Step 2
        /*
        if (step > 1) {
            alert("준비 중인 기능입니다.");
            return;
        }
        */
        currentStep = step;

        // 탭 이동 시 캡처 모드는 꺼주는게 안전할 수 있음
        if (captureMode && step !== 0) {
            dispatch("toggleCaptureMode"); // Turn off capture mode if leaving Step 1
        }
    }
</script>

<div
    class="border-b border-gray-200 {isExpanded
        ? 'flex-1 flex flex-col min-h-0'
        : ''}"
>
    <!-- 헤더 영역 -->
    <div class="flex flex-col border-b border-gray-100">
        <AccordionHeader
            icon="⚡"
            title="워크플로우 정의"
            {isExpanded}
            on:click={() => dispatch("toggleExpand")}
        >
            <!-- Toggle View Button (List / Graph) - Only show when expanded -->
            <svelte:fragment slot="actions">
                {#if isExpanded}
                    <div
                        class="flex items-center gap-1 mr-2 bg-gray-100 rounded p-0.5"
                    >
                        <button
                            class="px-2 py-0.5 text-xs rounded transition-colors {viewMode ===
                            'list'
                                ? 'bg-white shadow-sm text-gray-800'
                                : 'text-gray-500 hover:text-gray-700'}"
                            on:click|stopPropagation={() => (viewMode = "list")}
                            title="리스트 뷰"
                        >
                            <span class="text-[10px]">☰</span>
                        </button>
                        <button
                            class="px-2 py-0.5 text-xs rounded transition-colors {viewMode ===
                            'graph'
                                ? 'bg-white shadow-sm text-gray-800'
                                : 'text-gray-500 hover:text-gray-700'}"
                            on:click|stopPropagation={() =>
                                (viewMode = "graph")}
                            title="그래프 뷰"
                        >
                            <span class="text-[10px]">☊</span>
                        </button>
                    </div>
                {/if}
            </svelte:fragment>
        </AccordionHeader>

        <!-- 스텝 네비게이션 (확장되었고 리스트 뷰일 때만 표시) -->
        {#if isExpanded && viewMode === "list"}
            <div class="flex bg-white px-2 py-1">
                {#each STEPS as step}
                    <button
                        class="flex-1 flex items-center justify-center py-2 text-xs font-medium border-b-2 transition-colors
                               {currentStep === step.id
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-400 hover:text-gray-600'}"
                        on:click={() => setStep(step.id)}
                    >
                        <div class="flex items-center gap-1.5">
                            <div
                                class="w-4 h-4 rounded-full flex items-center justify-center text-[9px] border
                                        {currentStep === step.id
                                    ? 'border-blue-500 bg-blue-50'
                                    : 'border-gray-300 bg-gray-50'}"
                            >
                                {step.id + 1}
                            </div>
                            {step.title}
                        </div>
                    </button>
                {/each}
            </div>
        {/if}
    </div>

    {#if isExpanded}
        <div
            transition:slide={{ duration: 200, axis: "y" }}
            class="bg-gray-50/30 flex-1 flex flex-col min-h-[350px] overflow-hidden relative"
        >
            {#if viewMode === "graph"}
                <WorkflowGraph
                    phenomenon={phenomenonData}
                    {workflowActions}
                    {workflowConditions}
                />
            {:else if currentStep === 0}
                <PhenomenonCollector
                    bind:this={phenomenonCollectorRef}
                    phenomenon={phenomenonData}
                    {captureMode}
                    {phenomenonAttributes}
                    on:change={handlePhenomenonChange}
                    on:toggleCaptureMode={handleToggleCaptureMode}
                    on:evidenceHover={handleEvidenceHover}
                />
            {:else if currentStep === 1}
                <CandidateCauseExplorer
                    bind:this={candidateCauseExplorerRef}
                    phenomenon={phenomenonData}
                    {phenomenonAttributes}
                    on:change={handlePhenomenonChange}
                    on:evidenceHover={handleEvidenceHover}
                    on:linkingModeChange={handleLinkingModeChange}
                />
            {:else if currentStep === 2}
                <CauseDerivationExplorer
                    phenomenon={phenomenonData}
                    {workflowActions}
                    {workflowConditions}
                    on:change={handlePhenomenonChange}
                    on:workflowComplete={handleWorkflowComplete}
                />
            {/if}
        </div>
    {/if}
</div>
