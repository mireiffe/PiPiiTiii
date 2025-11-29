<script>
    export let shape;
    export let scale = 1;
    export let projectId = "";

    // Helper to convert PPT color to CSS
    function getCssColor(rgb) {
        if (!rgb) return "transparent";
        return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    }

    // Helper to get font style
    function getTextStyle(style) {
        if (!style) return "";
        const color = getCssColor(style.color_rgb || [0, 0, 0]);
        const size = (style.font_size || 18) * scale;
        const bold = style.bold ? "bold" : "normal";
        const italic = style.italic ? "italic" : "normal";
        const underline = style.underline ? "underline" : "none";

        return `
      color: ${color};
      font-size: ${size}px;
      font-weight: ${bold};
      font-style: ${italic};
      text-decoration: ${underline};
      font-family: ${style.font_name || "sans-serif"};
    `;
    }

    // Helper for fill
    function getFillStyle(fill) {
        if (!fill || fill.visible === false) return "";
        const color = fill.fore_color_rgb || fill.back_color_rgb;
        if (!color) return "";
        return `background-color: ${getCssColor(color)};`;
    }

    // Helper for border
    function getBorderStyle(line) {
        if (!line || line.visible === false) return "";
        const width = (line.weight || 1) * scale;
        const color = getCssColor(line.color_rgb || [0, 0, 0]);
        // Dash style mapping could be added here
        return `border: ${width}px solid ${color};`;
    }

    $: style = `
    position: absolute;
    left: ${shape.left * scale}px;
    top: ${shape.top * scale}px;
    width: ${shape.width * scale}px;
    height: ${shape.height * scale}px;
    ${getFillStyle(shape.fill)}
    ${getBorderStyle(shape.line)}
    z-index: ${shape.z_order_position || 1};
    overflow: hidden;
  `;

    const IMAGE_BASE = "http://localhost:8000";
</script>

<div
    {style}
    class="absolute select-none group"
    data-shape-id={shape.shape_index}
>
    <!-- Image -->
    {#if shape.image_file}
        <img
            src={`${IMAGE_BASE}/results/${projectId}/${shape.image_file}`}
            alt={shape.name}
            class="w-full h-full object-contain pointer-events-none"
        />
    {/if}

    <!-- Text -->
    {#if shape.text && !shape.table}
        <div
            class="w-full h-full p-1 whitespace-pre-wrap break-words pointer-events-none"
            style={getTextStyle(shape.text_style)}
        >
            {shape.text}
        </div>
    {/if}

    <!-- Table -->
    {#if shape.table}
        <div
            class="w-full h-full grid pointer-events-none"
            style={`
      grid-template-columns: repeat(${shape.table.cols}, 1fr);
      grid-template-rows: repeat(${shape.table.rows}, 1fr);
    `}
        >
            {#each shape.table.cells as cell}
                <div
                    class="border border-gray-400 p-1 overflow-hidden"
                    style={`
          ${getFillStyle(cell.fill)}
          ${getTextStyle(cell.text_style)}
        `}
                >
                    {cell.text}
                </div>
            {/each}
        </div>
    {/if}

    <!-- Selection Overlay (visible on hover/drag) -->
    <div
        class="absolute inset-0 border-2 border-blue-500 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
    ></div>
</div>
