# JavaScript Arrays and Array Methods

## Explanation

An array is an ordered list of values, indexed from `0`. Arrays are objects, so they are passed and compared by reference. `array.length` is one more than the highest index.

Array methods fall into two groups:

- **Non-mutating** (return something new): `map`, `filter`, `reduce`, `slice`, `concat`, `find`, `findIndex`, `some`, `every`, `includes`, `indexOf`, `join`, `flat`, `toSorted`, `toReversed`
- **Mutating** (change the original array): `push`, `pop`, `shift`, `unshift`, `splice`, `sort`, `reverse`, `fill`

## Examples

```javascript
const nums = [3, 1, 4, 1, 5];

const doubled = nums.map((n) => n * 2);         // [6, 2, 8, 2, 10]
const big = nums.filter((n) => n > 2);          // [3, 4, 5]
const total = nums.reduce((sum, n) => sum + n, 0); // 14
const firstEven = nums.find((n) => n % 2 === 0);   // 4
const hasOne = nums.includes(1);                // true
const position = nums.indexOf(1);               // 1 (first match)

const copy = nums.slice(1, 3); // [1, 4]  (end index not included)
nums.splice(1, 2);             // removes 2 items at index 1; nums is now [3, 1, 5]
```

Looping:

```javascript
for (const value of ['a', 'b']) {
  console.log(value);
}

['a', 'b'].forEach((value, index) => console.log(index, value));
```

## Sorting

`sort` converts elements to strings by default, which surprises people with numbers.

```javascript
console.log([10, 9, 1].sort());                // [1, 10, 9]
console.log([10, 9, 1].sort((a, b) => a - b)); // [1, 9, 10]
```

`sort` mutates the array. Use `toSorted` (or sort a copy: `[...arr].sort(...)`) to keep the original.

## Common Mistakes

- Off-by-one errors: the last index is `length - 1`, so `i <= arr.length` goes one step too far.
- Forgetting to `return` inside a `map` or `filter` callback that uses curly braces.
- Calling `reduce` on an empty array with no initial value, which throws a `TypeError`.
- Using `forEach` and expecting a return value (it always returns `undefined`).
- Comparing arrays with `===`, which compares references, not contents.

## Edge Cases

- Empty arrays: `[].every(fn)` is `true`, `[].some(fn)` is `false`, `[].find(fn)` is `undefined`.
- `indexOf` cannot find `NaN`; `includes` can.
- Sparse arrays (`[1, , 3]`) have holes that some methods skip.
