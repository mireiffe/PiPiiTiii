<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import type { PhenomenonData, CaptureEvidence, AttributeEvidence } from '$lib/types/phenomenon';
    import { EVIDENCE_COLORS, createCaptureEvidence } from '$lib/types/phenomenon';
    import EvidenceCard from './EvidenceCard.svelte';

    export let phenomenon: PhenomenonData;
    export let captureMode = false;
    // 설정에서 선택된 속성들 (이미 필터링된 상태로 전달됨)
    export let phenomenonAttributes: { key: string; name: string; value: string; source?: string }[] = [];

    const dispatch = createEventDispatcher<{
        change: PhenomenonData;
        toggleCaptureMode: void;
        evidenceHover: { evidenceId: string | null };
    }>();

    let descriptionTextarea: HTMLTextAreaElement;

    // 캡처 증거만 필터링
    $: captureEvidences = phenomenon.evidences.filter((e): e is CaptureEvidence => e.type === 'capture');

    // 텍스트 영역 자동 크기 조절
    function autoResizeTextarea() {
        if (descriptionTextarea) {
            descriptionTextarea.style.height = 'auto';
            descriptionTextarea.style.height = Math.min(descriptionTextarea.scrollHeight, 150) + 'px';
        }
    }

    // 설명 텍스트 변경
    function handleDescriptionChange() {
        dispatch('change', {
            ...phenomenon,
            description: phenomenon.description,
            updatedAt: new Date().toISOString()
        });
    }

    // 증거 삭제
    function handleDeleteEvidence(evidenceId: string) {
        phenomenon.evidences = phenomenon.evidences.filter(e => e.id !== evidenceId);
        dispatch('change', phenomenon);
    }

    // 증거 라벨 업데이트
    function handleUpdateLabel(evidenceId: string, label: string) {
        const evidence = phenomenon.evidences.find(e => e.id === evidenceId);
        if (evidence && evidence.type === 'capture') {
            evidence.label = label;
            phenomenon.evidences = [...phenomenon.evidences];
            dispatch('change', phenomenon);
        }
    }

    // 캡처 증거 추가 (외부에서 호출)
    export function addCapture(capture: { slideIndex: number; x: number; y: number; width: number; height: number }) {
        const newEvidence = createCaptureEvidence(
            capture.slideIndex,
            capture.x,
            capture.y,
            capture.width,
            capture.height
        );
        phenomenon.evidences = [...phenomenon.evidences, newEvidence];
        dispatch('change', phenomenon);
    }

    // 캡처 오버레이 데이터 반환 (ViewerCanvas에서 사용)
    export function getCaptureOverlays() {
        return captureEvidences.map((capture, index) => ({
            ...capture,
            colorIndex: index
        }));
    }

    // 증거 호버 이벤트
    function handleEvidenceHover(evidenceId: string | null) {
        dispatch('evidenceHover', { evidenceId });
    }
</script>

<div class="flex flex-col h-full">
    <!-- 헤더 -->
    <div class="px-4 py-3 border-b border-gray-200 bg-white">
        <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-red-500"></div>
            <h2 class="text-sm font-semibold text-gray-800">발생현상 수집</h2>
        </div>
        <p class="text-xs text-gray-500 mt-1">
            증거를 수집하여 발생현상을 정의하세요
        </p>
    </div>

    <!-- 스크롤 영역 -->
    <div class="flex-1 overflow-y-auto">
        <!-- 캡처 섹션 -->
        <div class="px-4 py-3 border-b border-gray-100">
            <div class="flex items-center justify-between mb-2">
                <h3 class="text-xs font-medium text-gray-700 flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    캡처 ({captureEvidences.length})
                </h3>
                <button
                    class="text-xs px-2 py-1 rounded transition-colors {captureMode
                        ? 'bg-red-500 text-white hover:bg-red-600'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
                    on:click={() => dispatch('toggleCaptureMode')}
                >
                    {captureMode ? '캡처 종료' : '+ 캡처'}
                </button>
            </div>

            {#if captureMode}
                <div class="mb-2 p-2 bg-red-50 border border-red-200 rounded-lg">
                    <p class="text-xs text-red-600 flex items-center gap-1">
                        <svg class="w-3.5 h-3.5 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        캔버스에서 드래그하여 영역을 선택하세요
                    </p>
                </div>
            {/if}

            {#if captureEvidences.length === 0}
                <div class="text-center py-4 text-gray-400 text-xs">
                    캡처된 영역이 없습니다
                </div>
            {:else}
                <div class="space-y-2">
                    {#each captureEvidences as evidence, index (evidence.id)}
                        <EvidenceCard
                            {evidence}
                            color={EVIDENCE_COLORS[index % EVIDENCE_COLORS.length]}
                            index={index}
                            on:delete={() => handleDeleteEvidence(evidence.id)}
                            on:updateLabel={(e) => handleUpdateLabel(evidence.id, e.detail)}
                            on:mouseenter={() => handleEvidenceHover(evidence.id)}
                            on:mouseleave={() => handleEvidenceHover(null)}
                        />
                    {/each}
                </div>
            {/if}
        </div>

        <!-- 속성 섹션 (설정에서 선택된 속성 자동 표시) -->
        <div class="px-4 py-3 border-b border-gray-100">
            <div class="flex items-center justify-between mb-2">
                <h3 class="text-xs font-medium text-gray-700 flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    속성 ({phenomenonAttributes.length})
                </h3>
            </div>

            {#if phenomenonAttributes.length === 0}
                <div class="text-center py-4 text-gray-400 text-xs">
                    설정에서 발생현상에 포함할 속성을 선택하세요
                </div>
            {:else}
                <div class="space-y-2">
                    {#each phenomenonAttributes as attr (attr.key)}
                        <div class="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
                            <svg class="w-3.5 h-3.5 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                            </svg>
                            <div class="flex-1 min-w-0">
                                <span class="text-xs font-medium text-gray-700">{attr.name}:</span>
                                <span class="text-xs text-gray-600 ml-1">{attr.value || '(없음)'}</span>
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>

        <!-- 설명 섹션 -->
        <div class="px-4 py-3">
            <h3 class="text-xs font-medium text-gray-700 flex items-center gap-1.5 mb-2">
                <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
                </svg>
                설명
            </h3>
            <textarea
                bind:this={descriptionTextarea}
                bind:value={phenomenon.description}
                on:input={() => { autoResizeTextarea(); handleDescriptionChange(); }}
                placeholder="발생현상에 대한 설명을 입력하세요..."
                class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg resize-none
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       placeholder:text-gray-400"
                rows="3"
            ></textarea>
        </div>
    </div>

    <!-- 하단 요약 -->
    <div class="px-4 py-3 bg-gray-50 border-t border-gray-200">
        <div class="flex items-center justify-between text-xs text-gray-500">
            <span>
                캡처 {captureEvidences.length}개, 속성 {phenomenonAttributes.length}개
            </span>
            <span>
                {#if phenomenon.updatedAt}
                    마지막 수정: {new Date(phenomenon.updatedAt).toLocaleTimeString('ko-KR')}
                {/if}
            </span>
        </div>
    </div>
</div>
