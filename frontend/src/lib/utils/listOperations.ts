/**
 * Common list operations utility
 *
 * Abstracts common patterns used across settings components:
 * - moveUp/moveDown
 * - add/remove items
 * - reorder by drag-drop
 *
 * Reduces duplication in:
 * - WorkflowDefinitionsSection
 * - CoreStepsSection
 * - WorkflowStepsSection
 * - PhaseSettingsSection
 */

/**
 * Move an item up in the array (swap with previous item)
 * Returns new array (immutable)
 */
export function moveUp<T>(items: T[], index: number): T[] {
    if (index <= 0 || index >= items.length) return items;
    const newItems = [...items];
    [newItems[index - 1], newItems[index]] = [newItems[index], newItems[index - 1]];
    return newItems;
}

/**
 * Move an item down in the array (swap with next item)
 * Returns new array (immutable)
 */
export function moveDown<T>(items: T[], index: number): T[] {
    if (index < 0 || index >= items.length - 1) return items;
    const newItems = [...items];
    [newItems[index], newItems[index + 1]] = [newItems[index + 1], newItems[index]];
    return newItems;
}

/**
 * Remove an item at the specified index
 * Returns new array (immutable)
 */
export function removeAt<T>(items: T[], index: number): T[] {
    if (index < 0 || index >= items.length) return items;
    return [...items.slice(0, index), ...items.slice(index + 1)];
}

/**
 * Remove an item by predicate
 * Returns new array (immutable)
 */
export function removeWhere<T>(items: T[], predicate: (item: T) => boolean): T[] {
    return items.filter(item => !predicate(item));
}

/**
 * Add an item at the end of the array
 * Returns new array (immutable)
 */
export function append<T>(items: T[], item: T): T[] {
    return [...items, item];
}

/**
 * Add an item at the beginning of the array
 * Returns new array (immutable)
 */
export function prepend<T>(items: T[], item: T): T[] {
    return [item, ...items];
}

/**
 * Insert an item at a specific index
 * Returns new array (immutable)
 */
export function insertAt<T>(items: T[], index: number, item: T): T[] {
    if (index < 0) index = 0;
    if (index > items.length) index = items.length;
    return [...items.slice(0, index), item, ...items.slice(index)];
}

/**
 * Update an item at a specific index
 * Returns new array (immutable)
 */
export function updateAt<T>(items: T[], index: number, updater: (item: T) => T): T[] {
    if (index < 0 || index >= items.length) return items;
    return items.map((item, i) => i === index ? updater(item) : item);
}

/**
 * Update an item by predicate
 * Returns new array (immutable)
 */
export function updateWhere<T>(items: T[], predicate: (item: T) => boolean, updater: (item: T) => T): T[] {
    return items.map(item => predicate(item) ? updater(item) : item);
}

/**
 * Reorder items by moving from one index to another (drag-drop style)
 * Returns new array (immutable)
 */
export function reorder<T>(items: T[], fromIndex: number, toIndex: number): T[] {
    if (fromIndex === toIndex) return items;
    if (fromIndex < 0 || fromIndex >= items.length) return items;
    if (toIndex < 0 || toIndex >= items.length) return items;

    const newItems = [...items];
    const [removed] = newItems.splice(fromIndex, 1);
    newItems.splice(toIndex, 0, removed);
    return newItems;
}

/**
 * Update order property for items that have an 'order' field
 * Useful after reordering to maintain consistent order values
 */
export function updateOrderField<T extends { order: number }>(items: T[]): T[] {
    return items.map((item, index) => ({ ...item, order: index }));
}

/**
 * Create a list management helper with bound callbacks
 * Returns an object with all common operations that automatically dispatch updates
 */
export function createListManager<T>(
    getItems: () => T[],
    setItems: (items: T[]) => void,
) {
    return {
        moveUp(index: number) {
            setItems(moveUp(getItems(), index));
        },
        moveDown(index: number) {
            setItems(moveDown(getItems(), index));
        },
        remove(index: number) {
            setItems(removeAt(getItems(), index));
        },
        add(item: T) {
            setItems(append(getItems(), item));
        },
        insert(index: number, item: T) {
            setItems(insertAt(getItems(), index, item));
        },
        update(index: number, updater: (item: T) => T) {
            setItems(updateAt(getItems(), index, updater));
        },
        reorder(fromIndex: number, toIndex: number) {
            setItems(reorder(getItems(), fromIndex, toIndex));
        },
    };
}

/**
 * Type-safe find by ID helper
 */
export function findById<T extends { id: string }>(items: T[], id: string): T | undefined {
    return items.find(item => item.id === id);
}

/**
 * Type-safe find index by ID helper
 */
export function findIndexById<T extends { id: string }>(items: T[], id: string): number {
    return items.findIndex(item => item.id === id);
}

/**
 * Remove by ID helper
 */
export function removeById<T extends { id: string }>(items: T[], id: string): T[] {
    return items.filter(item => item.id !== id);
}

/**
 * Update by ID helper
 */
export function updateById<T extends { id: string }>(items: T[], id: string, updater: (item: T) => T): T[] {
    return items.map(item => item.id === id ? updater(item) : item);
}
