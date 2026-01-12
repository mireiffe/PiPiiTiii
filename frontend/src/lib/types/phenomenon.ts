/**
 * 발생현상 수집 관련 타입 정의
 *
 * 발생현상(Phenomenon)은 세 가지 종류의 증거로 구성됨:
 * 1. Capture - 슬라이드 영역 캡처
 * 2. Attribute - PPT에 부여된 속성 정보
 * 3. Description - 사용자 텍스트 설명
 */

// 캡처 증거 - 슬라이드 영역 선택
export interface CaptureEvidence {
    type: 'capture';
    id: string;
    slideIndex: number;
    x: number;
    y: number;
    width: number;
    height: number;
    label?: string;  // 사용자가 부여한 라벨
    description?: string;  // 캡처에 대한 설명
}

// 속성 증거 - PPT에서 추출된 속성 (DB에 저장된 프로젝트 속성)
export interface AttributeEvidence {
    type: 'attribute';
    id: string;
    key: string;            // 속성 키 (DB 컬럼명)
    name: string;           // 속성 표시 이름
    value: string;          // 속성 값
    source?: string;        // 속성 출처 (project 등)
}

// 모든 증거 타입
export type Evidence = CaptureEvidence | AttributeEvidence;

// 발생현상 데이터
export interface PhenomenonData {
    evidences: Evidence[];
    description: string;  // 사용자 텍스트 설명
    candidateCauses: CandidateCause[]; // 원인 후보 목록
    finalCauseId?: string;  // 사용자가 지목한 최종 원인 ID
    workflowCompleted?: boolean;  // 워크플로우 완료 여부
    createdAt?: string;
    updatedAt?: string;
}

// 캡처 색상 팔레트
export const EVIDENCE_COLORS = [
    { bg: 'rgba(239, 68, 68, 0.2)', border: '#ef4444', name: '빨강' },   // red
    { bg: 'rgba(59, 130, 246, 0.2)', border: '#3b82f6', name: '파랑' },  // blue
    { bg: 'rgba(34, 197, 94, 0.2)', border: '#22c55e', name: '초록' },   // green
    { bg: 'rgba(168, 85, 247, 0.2)', border: '#a855f7', name: '보라' },  // purple
    { bg: 'rgba(249, 115, 22, 0.2)', border: '#f97316', name: '주황' },  // orange
    { bg: 'rgba(236, 72, 153, 0.2)', border: '#ec4899', name: '분홍' },  // pink
    { bg: 'rgba(20, 184, 166, 0.2)', border: '#14b8a6', name: '청록' },  // teal
    { bg: 'rgba(234, 179, 8, 0.2)', border: '#eab308', name: '노랑' },   // yellow
] as const;

// 증거 ID 생성
export function generateEvidenceId(): string {
    return `ev_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// 캡처 증거 생성 헬퍼
export function createCaptureEvidence(
    slideIndex: number,
    x: number,
    y: number,
    width: number,
    height: number,
    label?: string,
    description?: string
): CaptureEvidence {
    return {
        type: 'capture',
        id: generateEvidenceId(),
        slideIndex,
        x,
        y,
        width,
        height,
        label,
        description
    };
}

// 속성 증거 생성 헬퍼
export function createAttributeEvidence(
    key: string,
    name: string,
    value: string,
    source?: string
): AttributeEvidence {
    return {
        type: 'attribute',
        id: generateEvidenceId(),
        key,
        name,
        value,
        source
    };
}

// 원인 후보 데이터
export interface EvidenceLink {
    evidenceId: string;
    description: string;    // 근거와 원인 간의 관계 설명
}

// Deduction Todo Item
export type TodoType = 'action' | 'condition';

export type ConditionStatus = 'true' | 'false' | null;  // true=active(탐색중), false=inactive(탐색종료), null=미설정

export interface TodoItem {
    id: string;
    type: TodoType;
    text: string;
    isCompleted?: boolean;
    conditionStatus?: ConditionStatus;  // condition 타입일 때만 사용
    paramValues?: Record<string, string>;  // parameter ID -> value mapping
}

export interface CandidateCause {
    id: string;
    text: string;           // 원인 후보 설명
    evidenceIds: string[];  // @deprecated Use evidenceLinks instead. Kept for backward compatibility.
    evidenceLinks?: EvidenceLink[]; //
    notes?: string;         // 원인 후보에 대한 사용자 노트
    createdAt: string;

    // Cause Deduction
    todoList?: TodoItem[];
}

// 빈 발생현상 데이터 생성 (워크플로우 초기값)
export function createEmptyPhenomenon(): PhenomenonData {
    return {
        evidences: [],
        description: '',
        candidateCauses: [],
        createdAt: new Date().toISOString()
    };
}
