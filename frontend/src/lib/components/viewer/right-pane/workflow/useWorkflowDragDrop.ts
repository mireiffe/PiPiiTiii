// Drag & Drop hook for workflow steps

export interface DragDropState {
    draggedIndex: number | null;
    dropTargetIndex: number | null;
}

export interface DragDropHandlers {
    handleDragStart: (event: DragEvent, index: number) => void;
    handleDragOver: (event: DragEvent, index: number) => void;
    handleDragEnd: () => void;
    handleDrop: (event: DragEvent) => void;
    handleContainerDragOver: (event: DragEvent, totalSteps: number) => void;
    handleContainerDrop: (event: DragEvent, totalSteps: number) => void;
}

export function createDragDropHandlers(
    getState: () => DragDropState,
    setState: (state: Partial<DragDropState>) => void,
    onReorder: (fromIndex: number, toIndex: number) => void,
    onDragStart?: () => void
): DragDropHandlers {
    function handleDragStart(event: DragEvent, index: number) {
        onDragStart?.();
        setState({ draggedIndex: index });
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", index.toString());
        }
    }

    function handleDragOver(event: DragEvent, index: number) {
        event.preventDefault();
        event.stopPropagation();
        const { draggedIndex } = getState();
        if (draggedIndex === null) return;

        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }

        const target = event.currentTarget as HTMLElement;
        const rect = target.getBoundingClientRect();
        const offsetY = event.clientY - rect.top;
        const isTopHalf = offsetY < rect.height / 2;

        setState({ dropTargetIndex: isTopHalf ? index : index + 1 });
    }

    function handleDragEnd() {
        setState({ draggedIndex: null, dropTargetIndex: null });
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();

        const { draggedIndex, dropTargetIndex } = getState();

        if (draggedIndex !== null && dropTargetIndex !== null) {
            let target = dropTargetIndex;

            if (draggedIndex < target) {
                target -= 1;
            }

            if (target !== draggedIndex) {
                onReorder(draggedIndex, target);
            }
        }

        setState({ draggedIndex: null, dropTargetIndex: null });
    }

    function handleContainerDragOver(event: DragEvent, totalSteps: number) {
        event.preventDefault();
        const { draggedIndex } = getState();
        if (draggedIndex === null) return;
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }
        setState({ dropTargetIndex: totalSteps });
    }

    function handleContainerDrop(event: DragEvent, totalSteps: number) {
        event.preventDefault();
        const { draggedIndex } = getState();
        if (draggedIndex === null) return;
        setState({ dropTargetIndex: totalSteps });
        handleDrop(event);
    }

    return {
        handleDragStart,
        handleDragOver,
        handleDragEnd,
        handleDrop,
        handleContainerDragOver,
        handleContainerDrop,
    };
}
