// Drag and drop utilities for cause derivation

export interface DragDropState<T extends string> {
    draggingId: T | null;
    dragOverId: T | null;
}

export function createDragDropHandlers<T extends string>(
    getState: () => DragDropState<T>,
    setState: (state: Partial<DragDropState<T>>) => void,
    onDrop: (draggedId: T, targetId: T) => void
) {
    function handleDragStart(e: DragEvent, id: T) {
        setState({ draggingId: id });
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", id);
        }
    }

    function handleDragOver(e: DragEvent, id: T) {
        e.preventDefault();
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = "move";
        }
        setState({ dragOverId: id });
    }

    function handleDragLeave() {
        setState({ dragOverId: null });
    }

    function handleDrop(e: DragEvent, targetId: T) {
        e.preventDefault();
        const { draggingId } = getState();
        setState({ dragOverId: null });

        if (!draggingId || draggingId === targetId) return;
        onDrop(draggingId, targetId);
        setState({ draggingId: null });
    }

    function handleDragEnd() {
        setState({ draggingId: null, dragOverId: null });
    }

    return {
        handleDragStart,
        handleDragOver,
        handleDragLeave,
        handleDrop,
        handleDragEnd,
    };
}
