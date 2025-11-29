<script>
  import { onMount } from "svelte";
  import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";

  let projects = [];
  let loading = true;
  let searchTerm = "";
  let sortBy = "date";

  // Selection state
  let selectedProjectId = null;
  let selectedProjectDetails = null;
  let loadingDetails = false;

  $: filteredProjects = projects
    .filter((p) => {
      const term = searchTerm.toLowerCase();
      return (
        p.name.toLowerCase().includes(term) ||
        (p.author && p.author.toLowerCase().includes(term)) ||
        (p.title && p.title.toLowerCase().includes(term)) ||
        (p.subject && p.subject.toLowerCase().includes(term))
      );
    })
    .sort((a, b) => {
      if (sortBy === "date")
        return new Date(b.created_at) - new Date(a.created_at);
      if (sortBy === "name") return a.name.localeCompare(b.name);
      if (sortBy === "author")
        return (a.author || "").localeCompare(b.author || "");
      if (sortBy === "title")
        return (a.title || "").localeCompare(b.title || "");
      return 0;
    });

  onMount(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/projects");
      if (res.ok) {
        projects = await res.json();
      }
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

  async function selectProject(project) {
    selectedProjectId = project.id;
    selectedProjectDetails = null; // Reset while loading
    loadingDetails = true;

    try {
      const res = await fetch(
        `http://localhost:8000/api/project/${project.id}`,
      );
      if (res.ok) {
        selectedProjectDetails = await res.json();
      }
    } catch (e) {
      console.error("Failed to load project details", e);
    } finally {
      loadingDetails = false;
    }
  }
</script>

<div class="h-screen flex flex-col bg-gray-100 overflow-hidden">
  <!-- Header -->
  <div
    class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shrink-0"
  >
    <h1 class="text-2xl font-bold text-gray-800">PiPiiTiii</h1>
    <a
      href="/upload"
      class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm text-sm font-medium"
    >
      Upload New PPT
    </a>
  </div>

  <div class="flex-1 flex overflow-hidden">
    <!-- Left Panel: Project List -->
    <div
      class="w-1/3 min-w-[350px] max-w-[500px] flex flex-col border-r border-gray-200 bg-white"
    >
      <!-- Search & Sort -->
      <div class="p-4 border-b border-gray-100 space-y-3">
        <input
          type="text"
          placeholder="Search projects..."
          bind:value={searchTerm}
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          bind:value={sortBy}
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="date">Date (Newest)</option>
          <option value="name">Name (A-Z)</option>
          <option value="author">Author (A-Z)</option>
        </select>
      </div>

      <!-- List -->
      <div class="flex-1 overflow-y-auto">
        {#if loading}
          <div class="p-8 text-center text-gray-500 text-sm">Loading...</div>
        {:else if filteredProjects.length === 0}
          <div class="p-8 text-center text-gray-500 text-sm">
            No projects found.
          </div>
        {:else}
          <div class="divide-y divide-gray-100">
            {#each filteredProjects as project}
              <button
                class="w-full text-left p-4 hover:bg-gray-50 transition flex flex-col gap-1 {selectedProjectId ===
                project.id
                  ? 'bg-blue-50 border-l-4 border-blue-500'
                  : 'border-l-4 border-transparent'}"
                on:click={() => selectProject(project)}
              >
                <div class="flex justify-between items-start w-full">
                  <h3 class="font-semibold text-gray-800 truncate pr-2">
                    {project.name}
                  </h3>
                  <span class="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                </div>
                {#if project.title}
                  <p class="text-sm text-gray-600 truncate">{project.title}</p>
                {/if}
                <div class="flex items-center gap-2 text-xs text-gray-400 mt-1">
                  <span class="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                    {project.slide_count} slides
                  </span>
                  {#if project.author}
                    <span>by {project.author}</span>
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Right Panel: Preview -->
    <div class="flex-1 bg-gray-50 flex flex-col overflow-hidden relative">
      {#if !selectedProjectId}
        <div
          class="flex-1 flex flex-col items-center justify-center text-gray-400"
        >
          <svg
            class="w-16 h-16 mb-4 opacity-20"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
              clip-rule="evenodd"
            />
          </svg>
          <p class="text-lg font-medium">Select a project to preview</p>
        </div>
      {:else if loadingDetails}
        <div class="flex-1 flex items-center justify-center text-gray-500">
          <div
            class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-2"
          ></div>
        </div>
      {:else if selectedProjectDetails}
        <!-- Preview Header -->
        <div
          class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shadow-sm z-10"
        >
          <div>
            <h2 class="text-xl font-bold text-gray-800">
              {selectedProjectDetails.name}
            </h2>
            <p class="text-sm text-gray-500">
              {selectedProjectDetails.slide_count} slides • Last modified {new Date(
                selectedProjectDetails.created_at,
              ).toLocaleDateString()}
            </p>
          </div>
          <a
            href={`/viewer/${selectedProjectId}`}
            class="bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 transition shadow-md font-medium flex items-center gap-2"
          >
            <span>Open Viewer</span>
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
                d="M14 5l7 7m0 0l-7 7m7-7H3"
              />
            </svg>
          </a>
        </div>

        <!-- Slides Grid -->
        <div class="flex-1 overflow-y-auto p-8">
          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {#each selectedProjectDetails.slides as slide}
              <div class="group">
                <div
                  class="aspect-video bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden relative group-hover:shadow-md transition"
                >
                  <!-- Thumbnail Renderer -->
                  <div
                    class="absolute top-0 left-0 origin-top-left pointer-events-none"
                    style="transform: scale({300 /
                      (selectedProjectDetails.slide_width ||
                        960)}); width: {selectedProjectDetails.slide_width}px; height: {selectedProjectDetails.slide_height}px;"
                  >
                    {#each slide.shapes.sort((a, b) => (a.z_order_position || 0) - (b.z_order_position || 0)) as shape}
                      <div class="absolute top-0 left-0">
                        <ShapeRenderer
                          {shape}
                          scale={1}
                          projectId={selectedProjectId}
                        />
                      </div>
                    {/each}
                  </div>

                  <!-- Overlay -->
                  <a
                    href={`/viewer/${selectedProjectId}?slide=${slide.slide_index}`}
                    class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-5 transition flex items-center justify-center"
                  >
                  </a>
                </div>
                <p class="text-center text-sm text-gray-500 mt-2 font-medium">
                  Slide {slide.slide_index}
                </p>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
