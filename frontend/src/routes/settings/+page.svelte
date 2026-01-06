<script>
  import { onMount } from "svelte";
  import { fetchSettings, updateSettings } from "$lib/api/project";

  let loading = true;
  let saving = false;
  let settings = {
    llm: {
      api_endpoint: "",
      model_name: ""
    },
    summary_fields: []
  };

  onMount(async () => {
    try {
      const res = await fetchSettings();
      if (res.ok) {
        settings = await res.json();
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
    settings.summary_fields = [...settings.summary_fields, {
      id: newId,
      name: "새 필드",
      order: newOrder
    }];
  }

  function removeField(index) {
    if (confirm("이 필드를 삭제하시겠습니까?")) {
      settings.summary_fields = settings.summary_fields.filter((_, i) => i !== index);
      // Reorder
      settings.summary_fields = settings.summary_fields.map((field, i) => ({
        ...field,
        order: i
      }));
    }
  }

  function moveFieldUp(index) {
    if (index === 0) return;
    const temp = settings.summary_fields[index - 1];
    settings.summary_fields[index - 1] = settings.summary_fields[index];
    settings.summary_fields[index] = temp;
    settings.summary_fields = settings.summary_fields.map((field, i) => ({
      ...field,
      order: i
    }));
  }

  function moveFieldDown(index) {
    if (index === settings.summary_fields.length - 1) return;
    const temp = settings.summary_fields[index + 1];
    settings.summary_fields[index + 1] = settings.summary_fields[index];
    settings.summary_fields[index] = temp;
    settings.summary_fields = settings.summary_fields.map((field, i) => ({
      ...field,
      order: i
    }));
  }
</script>

<div class="h-screen flex flex-col bg-gray-100">
  <div class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-sm">
    <div>
      <h1 class="text-2xl font-bold text-gray-800">설정</h1>
      <a href="/" class="text-sm text-blue-600 hover:underline">← 대시보드로 돌아가기</a>
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
        <!-- LLM 설정 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-bold text-gray-800 mb-4">LLM 설정</h2>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API Endpoint
              </label>
              <input
                type="text"
                bind:value={settings.llm.api_endpoint}
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
                bind:value={settings.llm.model_name}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="gpt-4"
              />
            </div>
          </div>
        </div>

        <!-- PPT 요약 필드 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold text-gray-800">PPT 요약 필드</h2>
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
                <div class="flex items-center gap-3 p-4 border border-gray-200 rounded-lg bg-gray-50">
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

                  <div class="flex-1">
                    <input
                      type="text"
                      bind:value={field.name}
                      class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="필드 이름"
                    />
                  </div>

                  <button
                    class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                    on:click={() => removeField(index)}
                  >
                    삭제
                  </button>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
