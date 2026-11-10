# JavaScript Hoisting

## Explanation

Before running code in a scope, JavaScript registers the declarations in that scope. This is called **hoisting**. It behaves as if declarations were moved to the top of their scope, but different declarations are hoisted differently:

| Declaration | Hoisted? | Value before the declaration line |
|---|---|---|
| `function` declaration | Yes, with its body | The full function (callable) |
| `var` | Yes | `undefined` |
| `let` / `const` | Yes, but uninitialized | Throws `ReferenceError` (temporal dead zone) |
| `class` | Yes, but uninitialized | Throws `ReferenceError` |
| Function expression / arrow function | Follows the rules of its `var`/`let`/`const` | Depends on the variable keyword |

## Examples

```javascript
console.log(sayHi()); // 'hi': function declarations are fully hoisted

function sayHi() {
  return 'hi';
}

console.log(count); // undefined: var is hoisted and set to undefined
var count = 5;

console.log(total); // ReferenceError: Cannot access 'total' before initialization
let total = 10;
```

Function expressions are not callable early:

```javascript
console.log(typeof add); // 'undefined'
add(1, 2);               // TypeError: add is not a function

var add = function (a, b) {
  return a + b;
};
```

With `const add = ...` instead, the call would throw a `ReferenceError`.

## Temporal Dead Zone

The temporal dead zone (TDZ) is the region from the start of a block until the `let`/`const` declaration runs. Accessing the variable in the TDZ throws an error. This helps catch bugs where a variable is used before it has a value.

```javascript
let value = 'outer';
{
  console.log(value); // ReferenceError, not 'outer'
  let value = 'inner';
}
```

The inner `value` is hoisted to the top of the block, so it shadows the outer one even before its declaration line.

## Common Mistakes

- Calling a function expression or arrow function before it is defined.
- Relying on `var` hoisting, which makes code hard to read.
- Expecting the outer variable to be used inside a block that later declares the same name with `let`.

## Edge Cases

- Function declarations inside blocks behave differently in strict and sloppy mode. Avoid relying on them before the block runs.
- `import` declarations are hoisted to the top of the module.
