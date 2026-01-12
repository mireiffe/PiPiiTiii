<script lang="ts">
  import { onMount } from "svelte";
  import { fetchSettings, updateSettings, fetchAllAttributes } from "$lib/api/project";

  interface AttributeDefinition {
    key: string;
    display_name: string;
    attr_type: {
      variant: string;
    };
  }

  interface SummaryField {
    id: string;
    name: string;
    order: number;
    system_prompt: string;
    user_prompt: string;
  }

  interface LLMConfig {
    api_type: string;
    api_endpoint: string;
    model_name: string;
  }

  interface WorkflowActionParam {
    id: string;
    name: string;
    required: boolean;
  }

  interface WorkflowAction {
    id: string;
    name: string;
    params: WorkflowActionParam[];
  }

  interface WorkflowCondition {
    id: string;
    name: string;
    params: WorkflowActionParam[];
  }

  interface Settings {
    llm: LLMConfig;
    workflow_llm?: LLMConfig;
    workflow_prompts?: {
      system_prompt: string;
      user_prompt: string;
    };
    summary_fields: SummaryField[];
    use_thumbnails: boolean;
    workflow_actions: WorkflowAction[];
    workflow_conditions: WorkflowCondition[];
    phenomenon_attributes: string[];
  }

  let loading = true;
  let saving = false;
  let availableAttributes: AttributeDefinition[] = [];
  let settings: Settings = {
    llm: {
      api_type: "openai",
      api_endpoint: "",
      model_name: "",
    },
    workflow_llm: {
      api_type: "openai",
      api_endpoint: "",
      model_name: "",
    },
    workflow_prompts: {
      system_prompt: "",
      user_prompt: "",
    },
    summary_fields: [],
    use_thumbnails: true,
    workflow_actions: [],
    workflow_conditions: [],
    phenomenon_attributes: [],
  };

  // Expanded field for editing prompts
  let expandedFieldId: string | null = null;
  // Expanded action for editing params
  let expandedActionId: string | null = null;
  // Expanded condition for editing params
  let expandedConditionId: string | null = null;

  onMount(async () => {
    try {
      // Load settings and available attributes in parallel
      const [settingsRes, attrsRes] = await Promise.all([
        fetchSettings(),
        fetchAllAttributes()
      ]);

      if (attrsRes.ok) {
        availableAttributes = await attrsRes.json();
      }

      if (settingsRes.ok) {
        const data = await settingsRes.json();
        // Ensure llm has all required fields with defaults
        settings = {
          llm: {
            api_type: data.llm?.api_type || "openai",
            api_endpoint: data.llm?.api_endpoint || "",
            model_name: data.llm?.model_name || "",
          },
          workflow_llm: {
            api_type:
              data.workflow_llm?.api_type || data.llm?.api_type || "openai",
            api_endpoint:
              data.workflow_llm?.api_endpoint || data.llm?.api_endpoint || "",
            model_name:
              data.workflow_llm?.model_name || data.llm?.model_name || "",
          },
          workflow_prompts: {
            system_prompt:
              data.workflow_prompts?.system_prompt ||
              "당신은 로봇이나 에이전트의 행동을 제어하는 Behavior Tree 워크플로우를 생성하고 수정하는 전문가입니다. 주어진 요청에 따라 워크플로우를 분석하고 수정된 JSON을 반환해야 합니다.",
            user_prompt:
              data.workflow_prompts?.user_prompt ||
              "현재 워크플로우: {workflow_json}\n\n요청사항: {query}\n\n위 요청사항을 반영하여 수정된 워크플로우 JSON 전체를 마크다운 코드 블록(json)으로 감싸서 반환해주세요.",
          },
          summary_fields: (data.summary_fields || []).map((f) => ({
            id: f.id,
            name: f.name,
            order: f.order,
            system_prompt: f.system_prompt || "",
            user_prompt: f.user_prompt || "",
          })),
          use_thumbnails: data.use_thumbnails ?? true,
          workflow_actions: (data.workflow_actions || []).map((a) => ({
            id: a.id,
            name: a.name,
            params: (a.params || []).map((p) => ({
              id: p.id,
              name: p.name,
              required: p.required || false,
            })),
          })),
          workflow_conditions: (data.workflow_conditions || []).map((c) => ({
            id: c.id,
            name: c.name,
            params: (c.params || []).map((p) => ({
              id: p.id,
              name: p.name,
              required: p.required || false,
            })),
          })),
          phenomenon_attributes: data.phenomenon_attributes || [],
        };
      }
    } catch (e) {
      console.error("Failed to load settings", e);
    } finally {
      loading = false;
    }
  });

  async function handleSave() {
    saving = true;
    try {
      // Clean up empty optional fields if needed, or backend handles it
      const res = await updateSettings(settings);
      if (res.ok) {
        alert("설정이 저장되었습니다.");
      } else {
        alert("설정 저장에 실패했습니다.");
      }
    } catch (e) {
      console.error("Failed to save settings", e);
      alert("설정 저장 중 오류가 발생했습니다.");
    } finally {
      saving = false;
    }
  }

  function addField() {
    const newId = `field_${Date.now()}`;
    const newOrder = settings.summary_fields.length;
    settings.summary_fields = [
      ...settings.summary_fields,
      {
        id: newId,
        name: "새 필드",
        order: newOrder,
        system_prompt: "",
        user_prompt: "",
      },
    ];
    // Auto-expand new field
    expandedFieldId = newId;
  }

  function removeField(index: number) {
    if (confirm("이 필드를 삭제하시겠습니까?")) {
      settings.summary_fields = settings.summary_fields.filter(
        (_, i) => i !== index,
      );
      // Reorder
      settings.summary_fields = settings.summary_fields.map((field, i) => ({
        ...field,
        order: i,
      }));
    }
  }

  function moveFieldUp(index: number) {
    if (index === 0) return;
    const temp = settings.summary_fields[index - 1];
    settings.summary_fields[index - 1] = settings.summary_fields[index];
    settings.summary_fields[index] = temp;
    settings.summary_fields = settings.summary_fields.map((field, i) => ({
      ...field,
      order: i,
    }));
  }

  function moveFieldDown(index: number) {
    if (index === settings.summary_fields.length - 1) return;
    const temp = settings.summary_fields[index + 1];
    settings.summary_fields[index + 1] = settings.summary_fields[index];
    settings.summary_fields[index] = temp;
    settings.summary_fields = settings.summary_fields.map((field, i) => ({
      ...field,
      order: i,
    }));
  }

  function toggleExpand(fieldId: string) {
    if (expandedFieldId === fieldId) {
      expandedFieldId = null;
    } else {
      expandedFieldId = fieldId;
    }
  }

  // ========== Workflow Actions Management ==========

  function addWorkflowAction() {
    const newId = `action_${Date.now()}`;
    settings.workflow_actions = [
      ...settings.workflow_actions,
      {
        id: newId,
        name: "새 액션",
        params: [],
      },
    ];
    expandedActionId = newId;
  }

  function removeWorkflowAction(index: number) {
    if (
      confirm(
        "이 액션을 삭제하시겠습니까? 이미 사용 중인 워크플로우에서 오류가 발생할 수 있습니다.",
      )
    ) {
      settings.workflow_actions = settings.workflow_actions.filter(
        (_, i) => i !== index,
      );
    }
  }

  function toggleActionExpand(actionId: string) {
    if (expandedActionId === actionId) {
      expandedActionId = null;
    } else {
      expandedActionId = actionId;
    }
  }

  function addActionParam(actionIndex: number) {
    const newId = `param_${Date.now()}`;
    settings.workflow_actions[actionIndex].params = [
      ...settings.workflow_actions[actionIndex].params,
      { id: newId, name: "새 파라미터", required: false },
    ];
    settings.workflow_actions = [...settings.workflow_actions];
  }

  function removeActionParam(actionIndex: number, paramIndex: number) {
    settings.workflow_actions[actionIndex].params = settings.workflow_actions[
      actionIndex
    ].params.filter((_, i) => i !== paramIndex);
    settings.workflow_actions = [...settings.workflow_actions];
  }

  // ========== Workflow Conditions Management ==========

  function addWorkflowCondition() {
    const newId = `condition_${Date.now()}`;
    settings.workflow_conditions = [
      ...settings.workflow_conditions,
      {
        id: newId,
        name: "새 조건",
        params: [],
      },
    ];
    expandedConditionId = newId;
  }

  function removeWorkflowCondition(index: number) {
    if (
      confirm(
        "이 조건을 삭제하시겠습니까? 이미 사용 중인 워크플로우에서 오류가 발생할 수 있습니다.",
      )
    ) {
      settings.workflow_conditions = settings.workflow_conditions.filter(
        (_, i) => i !== index,
      );
    }
  }

  function toggleConditionExpand(conditionId: string) {
    if (expandedConditionId === conditionId) {
      expandedConditionId = null;
    } else {
      expandedConditionId = conditionId;
    }
  }

  function addConditionParam(conditionIndex: number) {
    const newId = `param_${Date.now()}`;
    settings.workflow_conditions[conditionIndex].params = [
      ...settings.workflow_conditions[conditionIndex].params,
      { id: newId, name: "새 파라미터", required: false },
    ];
    settings.workflow_conditions = [...settings.workflow_conditions];
  }

  function removeConditionParam(conditionIndex: number, paramIndex: number) {
    settings.workflow_conditions[conditionIndex].params = settings.workflow_conditions[
      conditionIndex
    ].params.filter((_, i) => i !== paramIndex);
    settings.workflow_conditions = [...settings.workflow_conditions];
  }

  // ========== Phenomenon Attributes Management ==========

  function togglePhenomenonAttribute(key: string) {
    if (settings.phenomenon_attributes.includes(key)) {
      settings.phenomenon_attributes = settings.phenomenon_attributes.filter(k => k !== key);
    } else {
      settings.phenomenon_attributes = [...settings.phenomenon_attributes, key];
    }
  }
</script>

<div class="h-screen flex flex-col bg-gray-100">
  <div
    class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-sm"
  >
    <div>
      <h1 class="text-2xl font-bold text-gray-800">설정</h1>
      <a href="/" class="text-sm text-blue-600 hover:underline"
        >← 대시보드로 돌아가기</a
      >
    </div>
    <button
      class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm font-medium disabled:opacity-50"
      on:click={handleSave}
      disabled={saving}
    >
      {saving ? "저장 중..." : "저장"}
    </button>
  </div>

  <div class="flex-1 overflow-y-auto p-8">
    {#if loading}
      <div class="text-center text-gray-500">로딩 중...</div>
    {:else}
      <div class="max-w-4xl mx-auto space-y-8">
        <!-- LLM 설정 (요약) -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-bold text-gray-800 mb-4">
            요약 생성 LLM 설정
          </h2>
          <p class="text-sm text-gray-500 mb-4">
            자동 요약 생성에 사용할 LLM API를 설정합니다. API Key는 백엔드의
            .env 파일에서 LLM_API_KEY로 설정해주세요.
          </p>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API 연결 형식
              </label>
              <select
                bind:value={settings.llm.api_type}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="openai">OpenAI API</option>
                <option value="gemini">Google Gemini API</option>
                <option value="openai_compatible"
                  >OpenAI Compatible (직접 호출)</option
                >
              </select>
              <p class="text-xs text-gray-400 mt-1">
                {#if settings.llm.api_type === "openai"}
                  OpenAI 공식 SDK를 사용합니다.
                {:else if settings.llm.api_type === "gemini"}
                  Google Generative AI SDK를 사용합니다.
                {:else}
                  Bearer 토큰 인증으로 직접 API를 호출합니다.
                {/if}
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API Endpoint
              </label>
              <input
                type="text"
                bind:value={settings.llm.api_endpoint}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={settings.llm.api_type === "gemini"
                  ? "https://generativelanguage.googleapis.com/v1beta"
                  : "https://api.openai.com/v1"}
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Model Name
              </label>
              <input
                type="text"
                bind:value={settings.llm.model_name}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={settings.llm.api_type === "gemini"
                  ? "gemini-1.5-flash"
                  : "gpt-4o"}
              />
            </div>
          </div>
        </div>

        <!-- LLM 설정 (워크플로우) -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-bold text-gray-800 mb-4">
            워크플로우 생성 LLM 설정
          </h2>
          <p class="text-sm text-gray-500 mb-4">
            워크플로우 자동 생성 및 수정에 사용할 LLM API를 설정합니다.
            기본적으로 요약 생성 LLM과 동일하게 설정할 수 있습니다.
          </p>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API 연결 형식
              </label>
              <select
                bind:value={settings.workflow_llm.api_type}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="openai">OpenAI API</option>
                <option value="gemini">Google Gemini API</option>
                <option value="openai_compatible"
                  >OpenAI Compatible (직접 호출)</option
                >
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API Endpoint
              </label>
              <input
                type="text"
                bind:value={settings.workflow_llm.api_endpoint}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://api.openai.com/v1"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Model Name
              </label>
              <input
                type="text"
                bind:value={settings.workflow_llm.model_name}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="gpt-4o"
              />
            </div>

            <div class="border-t border-gray-100 pt-4 mt-4">
              <h3 class="text-md font-semibold text-gray-700 mb-3">
                프롬프트 설정
              </h3>
              <div class="space-y-3">
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1"
                    >System Prompt</label
                  >
                  <textarea
                    bind:value={settings.workflow_prompts.system_prompt}
                    class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none h-24"
                  ></textarea>
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1"
                    >User Query Prompt Template</label
                  >
                  <p class="text-[10px] text-gray-400 mb-1">
                    사용 가능한 변수: {"{workflow_json}"}, {"{query}"}
                  </p>
                  <textarea
                    bind:value={settings.workflow_prompts.user_prompt}
                    class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none h-24"
                  ></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- PPT 요약 필드 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h2 class="text-xl font-bold text-gray-800">PPT 요약 필드</h2>
              <p class="text-sm text-gray-500 mt-1">
                각 필드별로 LLM에 전달할 프롬프트를 설정합니다.
              </p>
            </div>
            <button
              class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
              on:click={addField}
            >
              + 필드 추가
            </button>
          </div>

          <div class="space-y-3">
            {#if settings.summary_fields.length === 0}
              <div class="text-center text-gray-400 py-8">
                필드가 없습니다. 필드를 추가해주세요.
              </div>
            {:else}
              {#each settings.summary_fields as field, index (field.id)}
                <div
                  class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden"
                >
                  <!-- Field Header -->
                  <div class="flex items-center gap-3 p-4">
                    <div class="flex flex-col gap-1">
                      <button
                        class="text-gray-500 hover:text-gray-700 disabled:opacity-30"
                        on:click={() => moveFieldUp(index)}
                        disabled={index === 0}
                        title="위로 이동"
                      >
                        ▲
                      </button>
                      <button
                        class="text-gray-500 hover:text-gray-700 disabled:opacity-30"
                        on:click={() => moveFieldDown(index)}
                        disabled={index === settings.summary_fields.length - 1}
                        title="아래로 이동"
                      >
                        ▼
                      </button>
                    </div>

                    <div class="flex-1 flex items-center gap-3">
                      <div class="flex-1">
                        <label class="block text-xs text-gray-500 mb-1"
                          >필드명</label
                        >
                        <input
                          type="text"
                          bind:value={field.name}
                          class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="필드 이름"
                        />
                      </div>
                      <div class="w-48">
                        <label class="block text-xs text-gray-500 mb-1"
                          >ID (읽기전용)</label
                        >
                        <input
                          type="text"
                          value={field.id}
                          readonly
                          class="w-full border border-gray-200 rounded px-3 py-2 bg-gray-100 text-gray-500 text-sm"
                        />
                      </div>
                    </div>

                    <button
                      class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                      on:click={() => toggleExpand(field.id)}
                      title="프롬프트 설정"
                    >
                      {expandedFieldId === field.id ? "▼ 접기" : "▶ 프롬프트"}
                    </button>

                    <button
                      class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                      on:click={() => removeField(index)}
                    >
                      삭제
                    </button>
                  </div>

                  <!-- Expanded Prompt Section -->
                  {#if expandedFieldId === field.id}
                    <div
                      class="border-t border-gray-200 p-4 bg-white space-y-4"
                    >
                      <div>
                        <label
                          class="block text-sm font-medium text-gray-700 mb-2"
                        >
                          System Prompt
                        </label>
                        <textarea
                          bind:value={field.system_prompt}
                          class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                          rows="3"
                          placeholder="LLM의 역할과 행동 지침을 정의합니다. 예: 당신은 PPT 문서를 분석하는 전문가입니다."
                        ></textarea>
                      </div>

                      <div>
                        <label
                          class="block text-sm font-medium text-gray-700 mb-2"
                        >
                          User Query Prompt
                        </label>
                        <textarea
                          bind:value={field.user_prompt}
                          class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                          rows="3"
                          placeholder="실제 요청 내용입니다. 예: 이 슬라이드들의 핵심 내용을 3줄로 요약해주세요."
                        ></textarea>
                      </div>
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <!-- 발생현상 속성 설정 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="mb-4">
            <h2 class="text-xl font-bold text-gray-800">발생현상 속성</h2>
            <p class="text-sm text-gray-500 mt-1">
              발생현상 수집 시 자동으로 포함될 PPT 속성을 선택합니다.
            </p>
          </div>

          <div class="space-y-2">
            {#if availableAttributes.length === 0}
              <div class="text-center text-gray-400 py-8">
                정의된 속성이 없습니다.
              </div>
            {:else}
              {#each availableAttributes as attr (attr.key)}
                <label
                  class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors {settings.phenomenon_attributes.includes(attr.key)
                    ? 'bg-blue-50 border-blue-300'
                    : 'bg-gray-50 border-gray-200 hover:bg-gray-100'}"
                >
                  <input
                    type="checkbox"
                    checked={settings.phenomenon_attributes.includes(attr.key)}
                    on:change={() => togglePhenomenonAttribute(attr.key)}
                    class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <div class="flex-1">
                    <div class="font-medium text-gray-800">{attr.display_name}</div>
                    <div class="text-xs text-gray-500">{attr.key}</div>
                  </div>
                  <span class="text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded">
                    {attr.attr_type.variant}
                  </span>
                </label>
              {/each}
            {/if}
          </div>
        </div>

        <!-- Workflow Actions 설정 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h2 class="text-xl font-bold text-gray-800">워크플로우 액션</h2>
              <p class="text-sm text-gray-500 mt-1">
                워크플로우에서 사용할 수 있는 액션들을 정의합니다. 각 액션에
                필요한 파라미터도 설정할 수 있습니다.
              </p>
            </div>
            <button
              class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
              on:click={addWorkflowAction}
            >
              + 액션 추가
            </button>
          </div>

          <div class="space-y-3">
            {#if settings.workflow_actions.length === 0}
              <div class="text-center text-gray-400 py-8">
                정의된 액션이 없습니다. 액션을 추가해주세요.
              </div>
            {:else}
              {#each settings.workflow_actions as action, index (action.id)}
                <div
                  class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden"
                >
                  <!-- Action Header -->
                  <div class="flex items-center gap-3 p-4">
                    <div class="flex-1 flex items-center gap-3">
                      <div class="flex-1">
                        <label class="block text-xs text-gray-500 mb-1"
                          >액션명</label
                        >
                        <input
                          type="text"
                          bind:value={action.name}
                          class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="액션 이름"
                        />
                      </div>
                      <div class="w-48">
                        <label class="block text-xs text-gray-500 mb-1"
                          >ID (읽기전용)</label
                        >
                        <input
                          type="text"
                          value={action.id}
                          readonly
                          class="w-full border border-gray-200 rounded px-3 py-2 bg-gray-100 text-gray-500 text-sm"
                        />
                      </div>
                    </div>

                    <button
                      class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                      on:click={() => toggleActionExpand(action.id)}
                      title="파라미터 설정"
                    >
                      {expandedActionId === action.id
                        ? "▼ 접기"
                        : "▶ 파라미터"} ({action.params.length})
                    </button>

                    <button
                      class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                      on:click={() => removeWorkflowAction(index)}
                    >
                      삭제
                    </button>
                  </div>

                  <!-- Expanded Params Section -->
                  {#if expandedActionId === action.id}
                    <div
                      class="border-t border-gray-200 p-4 bg-white space-y-4"
                    >
                      <div class="flex justify-between items-center">
                        <label class="text-sm font-medium text-gray-700"
                          >파라미터 목록</label
                        >
                        <button
                          class="text-blue-600 hover:text-blue-700 text-sm font-medium"
                          on:click={() => addActionParam(index)}
                        >
                          + 파라미터 추가
                        </button>
                      </div>

                      {#if action.params.length === 0}
                        <div class="text-center text-gray-400 py-4 text-sm">
                          파라미터가 없습니다.
                        </div>
                      {:else}
                        <div class="space-y-2">
                          {#each action.params as param, paramIndex (param.id)}
                            <div
                              class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
                            >
                              <div class="flex-1">
                                <input
                                  type="text"
                                  bind:value={param.name}
                                  class="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  placeholder="파라미터 이름"
                                />
                              </div>
                              <label
                                class="flex items-center gap-2 text-sm text-gray-600 cursor-pointer"
                              >
                                <input
                                  type="checkbox"
                                  bind:checked={param.required}
                                  class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                                />
                                필수
                              </label>
                              <button
                                class="text-red-500 hover:text-red-600 p-1"
                                on:click={() =>
                                  removeActionParam(index, paramIndex)}
                                title="파라미터 삭제"
                              >
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
                                    d="M6 18L18 6M6 6l12 12"
                                  />
                                </svg>
                              </button>
                            </div>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <!-- Workflow Conditions 설정 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h2 class="text-xl font-bold text-gray-800">워크플로우 조건</h2>
              <p class="text-sm text-gray-500 mt-1">
                워크플로우에서 사용할 수 있는 조건들을 정의합니다. 각 조건에
                필요한 파라미터도 설정할 수 있습니다.
              </p>
            </div>
            <button
              class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
              on:click={addWorkflowCondition}
            >
              + 조건 추가
            </button>
          </div>

          <div class="space-y-3">
            {#if settings.workflow_conditions.length === 0}
              <div class="text-center text-gray-400 py-8">
                정의된 조건이 없습니다. 조건을 추가해주세요.
              </div>
            {:else}
              {#each settings.workflow_conditions as condition, index (condition.id)}
                <div
                  class="border border-orange-200 rounded-lg bg-orange-50/30 overflow-hidden"
                >
                  <!-- Condition Header -->
                  <div class="flex items-center gap-3 p-4">
                    <div class="flex-1 flex items-center gap-3">
                      <div class="flex-1">
                        <label class="block text-xs text-gray-500 mb-1"
                          >조건명</label
                        >
                        <input
                          type="text"
                          bind:value={condition.name}
                          class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500"
                          placeholder="조건 이름"
                        />
                      </div>
                      <div class="w-48">
                        <label class="block text-xs text-gray-500 mb-1"
                          >ID (읽기전용)</label
                        >
                        <input
                          type="text"
                          value={condition.id}
                          readonly
                          class="w-full border border-gray-200 rounded px-3 py-2 bg-gray-100 text-gray-500 text-sm"
                        />
                      </div>
                    </div>

                    <button
                      class="text-gray-500 hover:text-orange-600 px-3 py-2 rounded transition text-sm"
                      on:click={() => toggleConditionExpand(condition.id)}
                      title="파라미터 설정"
                    >
                      {expandedConditionId === condition.id
                        ? "▼ 접기"
                        : "▶ 파라미터"} ({condition.params.length})
                    </button>

                    <button
                      class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                      on:click={() => removeWorkflowCondition(index)}
                    >
                      삭제
                    </button>
                  </div>

                  <!-- Expanded Params Section -->
                  {#if expandedConditionId === condition.id}
                    <div
                      class="border-t border-orange-200 p-4 bg-white space-y-4"
                    >
                      <div class="flex justify-between items-center">
                        <label class="text-sm font-medium text-gray-700"
                          >파라미터 목록</label
                        >
                        <button
                          class="text-orange-600 hover:text-orange-700 text-sm font-medium"
                          on:click={() => addConditionParam(index)}
                        >
                          + 파라미터 추가
                        </button>
                      </div>

                      {#if condition.params.length === 0}
                        <div class="text-center text-gray-400 py-4 text-sm">
                          파라미터가 없습니다.
                        </div>
                      {:else}
                        <div class="space-y-2">
                          {#each condition.params as param, paramIndex (param.id)}
                            <div
                              class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
                            >
                              <div class="flex-1">
                                <input
                                  type="text"
                                  bind:value={param.name}
                                  class="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                                  placeholder="파라미터 이름"
                                />
                              </div>
                              <label
                                class="flex items-center gap-2 text-sm text-gray-600 cursor-pointer"
                              >
                                <input
                                  type="checkbox"
                                  bind:checked={param.required}
                                  class="w-4 h-4 text-orange-600 rounded focus:ring-orange-500"
                                />
                                필수
                              </label>
                              <button
                                class="text-red-500 hover:text-red-600 p-1"
                                on:click={() =>
                                  removeConditionParam(index, paramIndex)}
                                title="파라미터 삭제"
                              >
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
                                    d="M6 18L18 6M6 6l12 12"
                                  />
                                </svg>
                              </button>
                            </div>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
