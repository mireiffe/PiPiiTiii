/**
 * Key Info (핵심정보) Type Definitions
 *
 * Types for the Key Info system that replaces the workflow system.
 */

// ========== Settings Types (정의) ==========

/**
 * 핵심정보 항목 정의 (설정에서 정의)
 * 각 카테고리 안에 포함되는 항목
 */
export interface KeyInfoItemDefinition {
    id: string;
    title: string;        // 제목
    description: string;  // 설명
    order: number;
}

/**
 * 핵심정보 카테고리 정의 (설정에서 정의)
 */
export interface KeyInfoCategoryDefinition {
    id: string;
    name: string;
    order: number;
    items: KeyInfoItemDefinition[];
    createdAt: string;
    // LLM 자동 생성용 프롬프트 (카테고리별 설정)
    systemPrompt?: string;
    userPrompt?: string;  // {{key_info_title}}, {{key_info_description}} 템플릿 변수 지원
}

/**
 * 핵심정보 설정 (전역 설정)
 */
export interface KeyInfoSettings {
    categories: KeyInfoCategoryDefinition[];
}

// ========== Instance Types (프로젝트별 데이터) ==========

/**
 * 캡처 데이터
 */
export interface KeyInfoCaptureValue {
    id: string;
    slideIndex: number;
    x: number;
    y: number;
    width: number;
    height: number;
    label?: string;
    caption?: string;
}

/**
 * 프로젝트별 핵심정보 인스턴스
 * 각 핵심정보 항목에 대한 실제 데이터
 * 모든 컨텐츠 타입(텍스트, 캡처, 이미지)이 공존 가능
 */
export interface KeyInfoInstance {
    id: string;
    categoryId: string;   // KeyInfoCategoryDefinition.id 참조
    itemId: string;       // KeyInfoItemDefinition.id 참조

    // 텍스트 (항상 편집 가능)
    textValue?: string;

    // 다중 캡처/이미지 지원 (신규 배열 필드)
    captureValues?: KeyInfoCaptureValue[];  // 다중 슬라이드 캡처
    imageIds?: string[];                     // 다중 이미지 (attachments.db ID 배열)
    imageCaptions?: Record<string, string>; // 이미지별 캡션 {imageId: caption}

    // @deprecated - 하위 호환성을 위해 유지, captureValues/imageIds 사용 권장
    captureValue?: KeyInfoCaptureValue;
    imageId?: string;
    imageCaption?: string;

    order: number;
    createdAt: string;
    updatedAt?: string;
}

/**
 * 프로젝트의 핵심정보 데이터
 */
export interface ProjectKeyInfoData {
    instances: KeyInfoInstance[];
    createdAt?: string;
    updatedAt?: string;
}

// ========== ID Generation Functions ==========

/**
 * 카테고리 ID 생성
 */
export function generateKeyInfoCategoryId(): string {
    return `kic_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * 항목 ID 생성
 */
export function generateKeyInfoItemId(): string {
    return `kii_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * 인스턴스 ID 생성
 */
export function generateKeyInfoInstanceId(): string {
    return `kiin_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * 캡처 ID 생성
 */
export function generateKeyInfoCaptureId(): string {
    return `kicap_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// ========== Factory Functions ==========

/**
 * 새 카테고리 생성
 */
export function createKeyInfoCategory(name: string, order: number): KeyInfoCategoryDefinition {
    return {
        id: generateKeyInfoCategoryId(),
        name,
        order,
        items: [],
        createdAt: new Date().toISOString(),
    };
}

/**
 * 새 항목 생성
 */
export function createKeyInfoItem(title: string, description: string, order: number): KeyInfoItemDefinition {
    return {
        id: generateKeyInfoItemId(),
        title,
        description,
        order,
    };
}

/**
 * 새 인스턴스 생성
 */
export function createKeyInfoInstance(
    categoryId: string,
    itemId: string,
    order: number
): KeyInfoInstance {
    return {
        id: generateKeyInfoInstanceId(),
        categoryId,
        itemId,
        order,
        createdAt: new Date().toISOString(),
    };
}

/**
 * 빈 프로젝트 데이터 생성
 */
export function createEmptyKeyInfoData(): ProjectKeyInfoData {
    return {
        instances: [],
        createdAt: new Date().toISOString(),
    };
}

// ========== Helper Functions ==========

/**
 * 카테고리별 인스턴스 그룹화
 */
export function groupInstancesByCategory(
    instances: KeyInfoInstance[]
): Map<string, KeyInfoInstance[]> {
    const map = new Map<string, KeyInfoInstance[]>();
    for (const instance of instances) {
        const list = map.get(instance.categoryId) || [];
        list.push(instance);
        map.set(instance.categoryId, list);
    }
    return map;
}

/**
 * 항목별 인스턴스 찾기
 */
export function getInstanceByItem(
    instances: KeyInfoInstance[],
    categoryId: string,
    itemId: string
): KeyInfoInstance | undefined {
    return instances.find(inst => inst.categoryId === categoryId && inst.itemId === itemId);
}

/**
 * 카테고리의 완료 상태 확인
 * (모든 항목에 대해 인스턴스가 있는지)
 */
export function isCategoryComplete(
    category: KeyInfoCategoryDefinition,
    instances: KeyInfoInstance[]
): boolean {
    if (category.items.length === 0) return true;

    for (const item of category.items) {
        const instance = getInstanceByItem(instances, category.id, item.id);
        if (!instance) return false;
        // 인스턴스가 있더라도 실제 값이 있는지 확인
        if (!hasInstanceValue(instance)) return false;
    }
    return true;
}

/**
 * 인스턴스에 실제 값이 있는지 확인
 * (텍스트, 캡처, 이미지 중 하나라도 있으면 true)
 */
export function hasInstanceValue(instance: KeyInfoInstance): boolean {
    const hasText = !!instance.textValue && instance.textValue.trim().length > 0;
    // 신규 배열 필드 또는 deprecated 단일 필드 확인
    const hasCapture = (instance.captureValues && instance.captureValues.length > 0) || !!instance.captureValue;
    const hasImage = (instance.imageIds && instance.imageIds.length > 0) || !!instance.imageId;
    return hasText || hasCapture || hasImage;
}

/**
 * 단일 캡처/이미지를 배열 형식으로 마이그레이션
 */
export function migrateInstanceToArrays(instance: KeyInfoInstance): KeyInfoInstance {
    const migrated = { ...instance };

    // captureValue -> captureValues 마이그레이션
    if (instance.captureValue && (!instance.captureValues || instance.captureValues.length === 0)) {
        migrated.captureValues = [instance.captureValue];
        delete migrated.captureValue;
    }

    // imageId -> imageIds 마이그레이션
    if (instance.imageId && (!instance.imageIds || instance.imageIds.length === 0)) {
        migrated.imageIds = [instance.imageId];
        if (instance.imageCaption) {
            migrated.imageCaptions = { [instance.imageId]: instance.imageCaption };
        }
        delete migrated.imageId;
        delete migrated.imageCaption;
    }

    return migrated;
}

/**
 * 프로젝트 데이터 전체 마이그레이션
 */
export function migrateKeyInfoData(data: ProjectKeyInfoData): ProjectKeyInfoData {
    return {
        ...data,
        instances: data.instances.map(migrateInstanceToArrays),
    };
}

/**
 * 모든 카테고리의 완료 상태 확인
 */
export function areAllCategoriesComplete(
    categories: KeyInfoCategoryDefinition[],
    instances: KeyInfoInstance[]
): boolean {
    return categories.every(cat => isCategoryComplete(cat, instances));
}

// ========== Dashboard Types (대시보드용) ==========

/**
 * KeyInfo 항목의 사용 상세 정보 (프로젝트별)
 */
export interface KeyInfoUsageDetail {
    projectId: string;
    projectName: string;
    textValue?: string;
    captureValues: KeyInfoCaptureValue[];
    imageIds: string[];
    imageCaptions: Record<string, string>;
}

/**
 * KeyInfo 사용 상세 응답
 */
export interface KeyInfoUsageDetailsResponse {
    details: Record<string, KeyInfoUsageDetail[]>;  // "categoryId_itemId" -> details[]
}

/**
 * KeyInfo 사용 횟수 응답
 */
export interface KeyInfoUsageCountsResponse {
    counts: Record<string, number>;  // "categoryId_itemId" -> count
}
