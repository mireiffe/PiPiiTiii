<script>
    import { createEventDispatcher } from "svelte";
    import KeyInfoSection from "./right-pane/KeyInfoSection.svelte";
    import SummarySection from "./right-pane/SummarySection.svelte";
    import ObjectsSection from "./right-pane/ObjectsSection.svelte";

    export let rightPaneFullscreen = false;
    export let rightPaneWidth = 300;
    export let expandedSection = null;
    export let settings;
    export let summaryData;
    export let summaryDataLLM;
    export let savingSummary;
    export let generatingFieldIds;
    export let generatingAll;
    export let selectedSlideIndices = [];
    export let comparingFieldId = null;
    export let editingFieldId = null;
    export let allShapes = [];
    export let selectedShapeId = null;
    export let editingDescription = "";
    export let project;
    export let projectId = "";
    export let slideWidth = 960;  // Original slide width for capture preview
    export let slideHeight = 540;  // Original slide height for capture preview

    // Key Info data
    export let keyInfoData = { instances: [] };
    export let savingKeyInfo = false;
    export let keyInfoCaptureMode = false;
    /** @type {string | null} */
    export let keyInfoCaptureTargetInstanceId = null;
    export let keyInfoSectionRef = null;

    const dispatch = createEventDispatcher();

    function toggleSection(section) {
        expandedSection = expandedSection === section ? null : section;
    }
</script>

<div
    class="bg-white border-l border-gray-200 flex flex-col {rightPaneFullscreen
        ? 'flex-1'
        : 'shrink-0'}"
    style={rightPaneFullscreen ? "" : `width: ${rightPaneWidth}px;`}
>
    <!-- Header -->
    <div class="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="font-bold text-gray-800">프로젝트 정보</h2>
        <button
            class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-all
                   {rightPaneFullscreen
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
            on:click={() => (rightPaneFullscreen = !rightPaneFullscreen)}
            title={rightPaneFullscreen ? "일반 보기" : "전체 보기"}
        >
            {#if rightPaneFullscreen}
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
                        d="M9 9V4.5M9 9H4.5M9 9L3.5 3.5M9 15v4.5M9 15H4.5M9 15l-5.5 5.5M15 9h4.5M15 9V4.5M15 9l5.5-5.5M15 15h4.5M15 15v4.5m0-4.5l5.5 5.5"
                    />
                </svg>
                <span>일반</span>
            {:else}
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
                        d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                    />
                </svg>
                <span>전체</span>
            {/if}
        </button>
    </div>

    <div class="flex-1 overflow-y-auto min-h-0 flex flex-col">
        <!-- Key Info Section -->
        <KeyInfoSection
            isExpanded={expandedSection === "keyinfo"}
            {projectId}
            {slideWidth}
            {slideHeight}
            {selectedSlideIndices}
            bind:keyInfoData
            keyInfoSettings={settings?.key_info_settings || { categories: [] }}
            {savingKeyInfo}
            captureMode={keyInfoCaptureMode}
            captureTargetInstanceId={keyInfoCaptureTargetInstanceId}
            bind:this={keyInfoSectionRef}
            on:toggleExpand={() => toggleSection("keyinfo")}
            on:keyInfoChange
            on:keyInfoSettingsChange
            on:toggleCaptureMode={(e) => dispatch("toggleKeyInfoCaptureMode", e.detail)}
        />

        <!-- Summary Section -->
        <SummarySection
            isExpanded={expandedSection === "summary"}
            {settings}
            {summaryData}
            {summaryDataLLM}
            {savingSummary}
            {generatingFieldIds}
            {generatingAll}
            {selectedSlideIndices}
            {comparingFieldId}
            {editingFieldId}
            {project}
            on:toggleExpand={() => toggleSection("summary")}
            on:generateAllSummaries
            on:toggleSlideSelection
            on:toggleCompare
            on:restoreLLMVersion
            on:generateSummaryForField
            on:saveSummary
        />

        <!-- Objects Section -->
        <ObjectsSection
            isExpanded={expandedSection === "objects"}
            {allShapes}
            {selectedShapeId}
            {editingDescription}
            on:toggleExpand={() => toggleSection("objects")}
            on:selectShape
            on:handleSaveDescription
        />
    </div>
</div>
