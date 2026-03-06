import { getUtilBucket, colorForUtil } from './colorScale';
import { describe, test, expect } from 'vitest'

describe('colorScale utilization buckets', () => {
    test('bucket boundaries', () => {
        expect(getUtilBucket(0)).toBe(0);
        expect(getUtilBucket(10)).toBe(0);  // <=50
        expect(getUtilBucket(50)).toBe(0);
        expect(getUtilBucket(51)).toBe(1);  // 51..70
        expect(getUtilBucket(70)).toBe(1);
        expect(getUtilBucket(71)).toBe(2);  // 71..90
        expect(getUtilBucket(90)).toBe(2);
        expect(getUtilBucket(91)).toBe(3);  // 91..100
        expect(getUtilBucket(100)).toBe(3);
        expect(getUtilBucket(101)).toBe(4); // overload >100
    });

    test('color mapping stable', () => {
        const c = colorForUtil(80);
        expect(typeof c).toBe('string');
    });
});
