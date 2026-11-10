# JavaScript Recursion

## Explanation

A **recursive** function solves a problem by calling itself on a smaller version of the same problem. Every recursive function needs:

1. **A base case**: a condition where the function returns without calling itself.
2. **A recursive case**: a call on a smaller input that moves toward the base case.

Each call gets its own set of local variables on the call stack. When the base case returns, the pending calls finish one by one in reverse order.

Recursion fits naturally with nested structures: trees, nested arrays, the DOM, and file systems.

## Examples

Factorial:

```javascript
function factorial(n) {
  if (n <= 1) return 1;        // base case
  return n * factorial(n - 1); // recursive case
}

console.log(factorial(5)); // 120
```

Flatten a nested array:

```javascript
function flatten(array) {
  const result = [];

  for (const item of array) {
    if (Array.isArray(item)) {
      result.push(...flatten(item));
    } else {
      result.push(item);
    }
  }

  return result;
}

console.log(flatten([1, [2, [3, [4]]], 5])); // [1, 2, 3, 4, 5]
console.log(flatten([]));                    // []
```

Walking a tree:

```javascript
const tree = {
  value: 1,
  children: [
    { value: 2, children: [] },
    { value: 3, children: [{ value: 4, children: [] }] },
  ],
};

function sumTree(node) {
  return node.value + node.children.reduce((total, child) => total + sumTree(child), 0);
}

console.log(sumTree(tree)); // 10
```

## Recursion vs. Iteration

Anything recursive can be written with a loop (sometimes with an explicit stack). Loops are often faster and avoid stack limits; recursion is often clearer for nested data. JavaScript engines generally do not optimize tail calls, so deep recursion can still overflow.

## Common Mistakes

- **Missing or unreachable base case**, causing `RangeError: Maximum call stack size exceeded`.
- Not moving toward the base case (for example, calling `factorial(n)` instead of `factorial(n - 1)`).
- Forgetting to `return` the recursive call's result.
- Mutating a shared array across calls by accident.

## Edge Cases

- Inputs like `0`, negative numbers, and empty arrays often need explicit handling.
- Naive recursive Fibonacci repeats work exponentially; memoization fixes this.
- Very deep inputs (tens of thousands of levels) can exceed the call stack.
