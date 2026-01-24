/**
 * Tests for frontend/src/lib/utils/listOperations.ts
 *
 * Tests immutable list operation utilities.
 */

import { describe, it, expect } from 'vitest';
import {
    moveUp,
    moveDown,
    removeAt,
    removeWhere,
    append,
    prepend,
    insertAt,
    updateAt,
    updateWhere,
    reorder,
    updateOrderField,
    createListManager,
    findById,
    findIndexById,
    removeById,
    updateById,
} from '$lib/utils/listOperations';

describe('moveUp', () => {
    it('should swap item with previous item', () => {
        const items = ['a', 'b', 'c'];
        const result = moveUp(items, 1);
        expect(result).toEqual(['b', 'a', 'c']);
    });

    it('should return same array for first item', () => {
        const items = ['a', 'b', 'c'];
        const result = moveUp(items, 0);
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should return same array for negative index', () => {
        const items = ['a', 'b', 'c'];
        const result = moveUp(items, -1);
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should return same array for out of bounds index', () => {
        const items = ['a', 'b', 'c'];
        const result = moveUp(items, 5);
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should return new array (immutable)', () => {
        const items = ['a', 'b', 'c'];
        const result = moveUp(items, 1);
        expect(result).not.toBe(items);
    });
});

describe('moveDown', () => {
    it('should swap item with next item', () => {
        const items = ['a', 'b', 'c'];
        const result = moveDown(items, 1);
        expect(result).toEqual(['a', 'c', 'b']);
    });

    it('should return same array for last item', () => {
        const items = ['a', 'b', 'c'];
        const result = moveDown(items, 2);
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should return same array for negative index', () => {
        const items = ['a', 'b', 'c'];
        const result = moveDown(items, -1);
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should return new array (immutable)', () => {
        const items = ['a', 'b', 'c'];
        const result = moveDown(items, 0);
        expect(result).not.toBe(items);
    });
});

describe('removeAt', () => {
    it('should remove item at index', () => {
        const items = ['a', 'b', 'c'];
        const result = removeAt(items, 1);
        expect(result).toEqual(['a', 'c']);
    });

    it('should remove first item', () => {
        const items = ['a', 'b', 'c'];
        const result = removeAt(items, 0);
        expect(result).toEqual(['b', 'c']);
    });

    it('should remove last item', () => {
        const items = ['a', 'b', 'c'];
        const result = removeAt(items, 2);
        expect(result).toEqual(['a', 'b']);
    });

    it('should return same array for invalid index', () => {
        const items = ['a', 'b', 'c'];
        expect(removeAt(items, -1)).toEqual(items);
        expect(removeAt(items, 5)).toEqual(items);
    });

    it('should return new array (immutable)', () => {
        const items = ['a', 'b', 'c'];
        const result = removeAt(items, 1);
        expect(result).not.toBe(items);
        expect(items).toHaveLength(3);
    });
});

describe('removeWhere', () => {
    it('should remove items matching predicate', () => {
        const items = [1, 2, 3, 4, 5];
        const result = removeWhere(items, (x) => x % 2 === 0);
        expect(result).toEqual([1, 3, 5]);
    });

    it('should return all items if none match', () => {
        const items = [1, 3, 5];
        const result = removeWhere(items, (x) => x % 2 === 0);
        expect(result).toEqual([1, 3, 5]);
    });

    it('should return empty array if all match', () => {
        const items = [2, 4, 6];
        const result = removeWhere(items, (x) => x % 2 === 0);
        expect(result).toEqual([]);
    });
});

describe('append', () => {
    it('should add item to end', () => {
        const items = ['a', 'b'];
        const result = append(items, 'c');
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should work with empty array', () => {
        const items: string[] = [];
        const result = append(items, 'a');
        expect(result).toEqual(['a']);
    });

    it('should return new array (immutable)', () => {
        const items = ['a', 'b'];
        const result = append(items, 'c');
        expect(result).not.toBe(items);
        expect(items).toHaveLength(2);
    });
});

describe('prepend', () => {
    it('should add item to beginning', () => {
        const items = ['b', 'c'];
        const result = prepend(items, 'a');
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should work with empty array', () => {
        const items: string[] = [];
        const result = prepend(items, 'a');
        expect(result).toEqual(['a']);
    });
});

describe('insertAt', () => {
    it('should insert at specified index', () => {
        const items = ['a', 'c'];
        const result = insertAt(items, 1, 'b');
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should insert at beginning for index 0', () => {
        const items = ['b', 'c'];
        const result = insertAt(items, 0, 'a');
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should insert at end for index equal to length', () => {
        const items = ['a', 'b'];
        const result = insertAt(items, 2, 'c');
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should clamp negative index to 0', () => {
        const items = ['b', 'c'];
        const result = insertAt(items, -5, 'a');
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should clamp index beyond length to length', () => {
        const items = ['a', 'b'];
        const result = insertAt(items, 10, 'c');
        expect(result).toEqual(['a', 'b', 'c']);
    });
});

describe('updateAt', () => {
    it('should update item at index', () => {
        const items = [{ v: 1 }, { v: 2 }, { v: 3 }];
        const result = updateAt(items, 1, (item) => ({ v: item.v * 10 }));
        expect(result[1].v).toBe(20);
    });

    it('should not modify other items', () => {
        const items = [{ v: 1 }, { v: 2 }, { v: 3 }];
        const result = updateAt(items, 1, (item) => ({ v: item.v * 10 }));
        expect(result[0].v).toBe(1);
        expect(result[2].v).toBe(3);
    });

    it('should return same array for invalid index', () => {
        const items = ['a', 'b', 'c'];
        const result = updateAt(items, 5, (x) => x.toUpperCase());
        expect(result).toEqual(items);
    });
});

describe('updateWhere', () => {
    it('should update items matching predicate', () => {
        const items = [{ id: 1, v: 'a' }, { id: 2, v: 'b' }];
        const result = updateWhere(
            items,
            (item) => item.id === 1,
            (item) => ({ ...item, v: 'updated' })
        );
        expect(result[0].v).toBe('updated');
        expect(result[1].v).toBe('b');
    });
});

describe('reorder', () => {
    it('should move item from one index to another', () => {
        const items = ['a', 'b', 'c', 'd'];
        const result = reorder(items, 0, 2);
        expect(result).toEqual(['b', 'c', 'a', 'd']);
    });

    it('should move item backward', () => {
        const items = ['a', 'b', 'c', 'd'];
        const result = reorder(items, 3, 1);
        expect(result).toEqual(['a', 'd', 'b', 'c']);
    });

    it('should return same array if from equals to', () => {
        const items = ['a', 'b', 'c'];
        const result = reorder(items, 1, 1);
        expect(result).toEqual(['a', 'b', 'c']);
    });

    it('should return same array for invalid indices', () => {
        const items = ['a', 'b', 'c'];
        expect(reorder(items, -1, 1)).toEqual(items);
        expect(reorder(items, 1, -1)).toEqual(items);
        expect(reorder(items, 5, 1)).toEqual(items);
        expect(reorder(items, 1, 5)).toEqual(items);
    });

    it('should return new array (immutable)', () => {
        const items = ['a', 'b', 'c'];
        const result = reorder(items, 0, 2);
        expect(result).not.toBe(items);
    });
});

describe('updateOrderField', () => {
    it('should update order property based on index', () => {
        const items = [
            { id: 'a', order: 5 },
            { id: 'b', order: 10 },
            { id: 'c', order: 2 },
        ];
        const result = updateOrderField(items);
        expect(result[0].order).toBe(0);
        expect(result[1].order).toBe(1);
        expect(result[2].order).toBe(2);
    });

    it('should preserve other properties', () => {
        const items = [{ id: 'a', name: 'test', order: 5 }];
        const result = updateOrderField(items);
        expect(result[0].id).toBe('a');
        expect(result[0].name).toBe('test');
    });
});

describe('createListManager', () => {
    it('should create manager with bound operations', () => {
        let items = ['a', 'b', 'c'];
        const manager = createListManager(
            () => items,
            (newItems) => { items = newItems; }
        );

        manager.moveDown(0);
        expect(items).toEqual(['b', 'a', 'c']);
    });

    it('should support add operation', () => {
        let items = ['a', 'b'];
        const manager = createListManager(
            () => items,
            (newItems) => { items = newItems; }
        );

        manager.add('c');
        expect(items).toEqual(['a', 'b', 'c']);
    });

    it('should support remove operation', () => {
        let items = ['a', 'b', 'c'];
        const manager = createListManager(
            () => items,
            (newItems) => { items = newItems; }
        );

        manager.remove(1);
        expect(items).toEqual(['a', 'c']);
    });
});

describe('findById', () => {
    it('should find item by id', () => {
        const items = [{ id: '1', name: 'a' }, { id: '2', name: 'b' }];
        const result = findById(items, '2');
        expect(result?.name).toBe('b');
    });

    it('should return undefined if not found', () => {
        const items = [{ id: '1', name: 'a' }];
        const result = findById(items, '99');
        expect(result).toBeUndefined();
    });
});

describe('findIndexById', () => {
    it('should find index by id', () => {
        const items = [{ id: '1' }, { id: '2' }, { id: '3' }];
        expect(findIndexById(items, '2')).toBe(1);
    });

    it('should return -1 if not found', () => {
        const items = [{ id: '1' }];
        expect(findIndexById(items, '99')).toBe(-1);
    });
});

describe('removeById', () => {
    it('should remove item by id', () => {
        const items = [{ id: '1' }, { id: '2' }, { id: '3' }];
        const result = removeById(items, '2');
        expect(result).toHaveLength(2);
        expect(findById(result, '2')).toBeUndefined();
    });

    it('should return all items if id not found', () => {
        const items = [{ id: '1' }, { id: '2' }];
        const result = removeById(items, '99');
        expect(result).toHaveLength(2);
    });
});

describe('updateById', () => {
    it('should update item by id', () => {
        const items = [{ id: '1', v: 1 }, { id: '2', v: 2 }];
        const result = updateById(items, '2', (item) => ({ ...item, v: 20 }));
        expect(result[1].v).toBe(20);
    });

    it('should not modify if id not found', () => {
        const items = [{ id: '1', v: 1 }];
        const result = updateById(items, '99', (item) => ({ ...item, v: 99 }));
        expect(result).toEqual(items);
    });
});
