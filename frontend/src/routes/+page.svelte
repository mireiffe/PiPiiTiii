<script>
  import { onMount } from "svelte";

  let projects = [];
  let loading = true;
  let searchTerm = "";
  let sortBy = "date";

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
</script>

<div class="min-h-screen bg-gray-100 p-8">
  <div class="max-w-6xl mx-auto">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold text-gray-800">PiPiiTiii</h1>
      <a
        href="/upload"
        class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition shadow-md"
      >
        Upload New PPT
      </a>
    </div>

    <!-- Search and Sort Controls -->
    <div
      class="bg-white p-4 rounded-xl shadow-sm mb-6 flex flex-col md:flex-row gap-4"
    >
      <div class="flex-1">
        <input
          type="text"
          placeholder="Search by name, author, title..."
          bind:value={searchTerm}
          class="w-full border border-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div class="w-full md:w-48">
        <select
          bind:value={sortBy}
          class="w-full border border-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="date">Date (Newest)</option>
          <option value="name">Name (A-Z)</option>
          <option value="author">Author (A-Z)</option>
          <option value="title">Title (A-Z)</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="text-center py-20">
        <p class="text-gray-500 text-lg">Loading projects...</p>
      </div>
    {:else if filteredProjects.length === 0}
      <div class="bg-white rounded-xl shadow-sm p-12 text-center">
        <p class="text-gray-500 text-lg mb-4">
          No projects found matching your criteria.
        </p>
        {#if projects.length === 0}
          <a href="/upload" class="text-blue-600 hover:underline font-medium">
            Upload your first PPT file
          </a>
        {/if}
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#each filteredProjects as project}
          <a
            href={`/viewer/${project.id}`}
            class="block bg-white rounded-xl shadow-sm hover:shadow-md transition p-6 border border-gray-100"
          >
            <div class="flex justify-between items-start mb-4">
              <div
                class="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded"
              >
                PPTX
              </div>
              <span class="text-gray-400 text-sm">
                {new Date(project.created_at).toLocaleDateString()}
              </span>
            </div>
            <h2
              class="text-xl font-bold text-gray-800 mb-2 truncate"
              title={project.name}
            >
              {project.name}
            </h2>
            {#if project.title}
              <p
                class="text-gray-600 text-sm mb-2 truncate"
                title={project.title}
              >
                {project.title}
              </p>
            {/if}
            <div
              class="text-gray-500 text-sm mt-4 pt-4 border-t border-gray-100"
            >
              <div class="flex justify-between">
                <span>Slides: {project.slide_count}</span>
                <span class="truncate max-w-[150px]" title={project.author}>
                  {project.author || "Unknown"}
                </span>
              </div>
            </div>
          </a>
        {/each}
      </div>
    {/if}
  </div>
</div>
