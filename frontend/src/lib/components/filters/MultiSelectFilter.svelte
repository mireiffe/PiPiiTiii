<script>
  /** @type {string} */
  export let title;
  /** @type {any[]} */
  export let options = [];
  /** @type {any[]} */
  export let selected = [];
  /** @type {(selected: any[]) => void} */
  export let onChange;

  let searchTerm = "";
  let expanded = false;
  let inputElement;

  // 검색어에 따라 옵션 필터링
  $: filteredOptions = options.filter((opt) =>
    String(opt).toLowerCase().includes(searchTerm.toLowerCase())
  );

  $: allSelected = options.length > 0 && selected.length === options.length;

  function toggleOption(option) {
    let newSelected;
    if (selected.includes(option)) {
      newSelected = selected.filter((s) => s !== option);
    } else {
      newSelected = [...selected, option];
    }
    onChange(newSelected);
  }

  function toggleAll() {
    if (allSelected) {
      onChange([]);
    } else {
      onChange([...options]);
    }
  }

  // 외부 클릭 시 닫기 처리를 위한 액션 (간단한 구현)
  function clickOutside(node) {
    const handleClick = (event) => {
      if (node && !node.contains(event.target) && !event.defaultPrevented) {
        expanded = false;
      }
    };
    document.addEventListener("click", handleClick, true);
    return {
      destroy() {
        document.removeEventListener("click", handleClick, true);
      },
    };
  }

  function handleInputFocus() {
    expanded = true;
  }
</script>

<div class="flex flex-col relative" use:clickOutside>
  <div
    class="flex items-center w-full bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors overflow-hidden focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-400 {expanded
      ? 'rounded-b-none border-b-0 bg-gray-50'
      : ''}"
  >
    <div class="flex-1 relative flex items-center h-9">
      <input
        bind:this={inputElement}
        type="text"
        bind:value={searchTerm}
        on:focus={handleInputFocus}
        placeholder={title}
        class="w-full h-full px-3 text-sm text-gray-700 bg-transparent border-none focus:outline-none placeholder-gray-500"
      />
      {#if !searchTerm && selected.length > 0 && selected.length < options.length}
        <div class="absolute right-2 pointer-events-none">
          <span
            class="text-[10px] font-medium text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded-full border border-blue-100"
          >
            {selected.length}
          </span>
        </div>
      {/if}
    </div>

    <button
      class="h-9 px-2 text-gray-400 hover:text-gray-600 border-l border-gray-100 hover:bg-gray-50 transition-colors flex items-center justify-center"
      on:click={() => {
        expanded = !expanded;
        if (expanded) inputElement?.focus();
      }}
      tabindex="-1"
    >
      <svg
        class="w-3.5 h-3.5 transition-transform duration-200 {expanded
          ? 'rotate-180'
          : ''}"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M19 9l-7 7-7-7"
        />
      </svg>
    </button>
  </div>

  {#if expanded}
    <div
      class="absolute top-full left-0 right-0 bg-white border border-gray-200 border-t-0 rounded-b-lg p-2 shadow-lg z-20 max-h-60 flex flex-col"
    >
      <div class="flex justify-between items-center mb-2 px-1">
        <span class="text-xs text-gray-400">
          {filteredOptions.length} items
        </span>
        <button
          class="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors hover:bg-blue-50 px-2 py-0.5 rounded"
          on:click={toggleAll}
        >
          {allSelected ? "Clear All" : "Select All"}
        </button>
      </div>

      <div class="overflow-y-auto space-y-0.5 custom-scrollbar pr-1 flex-1">
        {#if filteredOptions.length === 0}
          <div class="py-4 text-center text-xs text-gray-400 italic">
            No matches found
          </div>
        {/if}
        {#each filteredOptions as option}
          <label
            class="flex items-center gap-2.5 cursor-pointer group select-none hover:bg-blue-50 p-1.5 rounded-md transition-colors"
          >
            <div class="relative flex items-center justify-center w-4 h-4">
              <input
                type="checkbox"
                class="peer appearance-none w-4 h-4 border border-gray-300 rounded bg-white checked:bg-blue-500 checked:border-blue-500 transition-all cursor-pointer"
                checked={selected.includes(option)}
                on:change={() => toggleOption(option)}
              />
              <svg
                class="absolute w-2.5 h-2.5 text-white pointer-events-none opacity-0 peer-checked:opacity-100 transition-opacity"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            <span
              class="text-sm text-gray-700 group-hover:text-gray-900 transition-colors truncate"
            >
              {option}
            </span>
          </label>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #9ca3af;
  }
</style>
