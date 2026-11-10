# JavaScript Variables and Data Types

## Explanation

A variable is a name that refers to a value. Modern JavaScript declares variables with `let` and `const`; older code uses `var`.

- `const` creates a binding that cannot be reassigned. The value itself can still change if it is an object or array.
- `let` creates a binding that can be reassigned.
- `var` is function-scoped and hoisted with the value `undefined`. Prefer `let` and `const`.

JavaScript has seven **primitive** types and one non-primitive type:

| Type | Example |
|---|---|
| `string` | `'hello'` |
| `number` | `42`, `3.14`, `NaN`, `Infinity` |
| `bigint` | `10n` |
| `boolean` | `true`, `false` |
| `undefined` | a declared variable with no value |
| `null` | an intentional "no value" |
| `symbol` | `Symbol('id')` |
| `object` | `{}`, `[]`, functions, dates |

Primitives are immutable and compared by value. Objects are compared by reference.

## Examples

```javascript
const name = 'Ada';
let score = 10;
score += 5; // 15

const list = [1, 2];
list.push(3); // allowed: the array changes, the binding does not
// list = [];  // TypeError: Assignment to constant variable.

console.log(typeof 'hi');       // 'string'
console.log(typeof 42);         // 'number'
console.log(typeof undefined);  // 'undefined'
console.log(typeof null);       // 'object' (a historical quirk)
console.log(typeof []);         // 'object'
console.log(Array.isArray([])); // true
```

## Equality and Type Coercion

`===` (strict equality) compares without converting types. `==` (loose equality) converts types first, which leads to surprises.

```javascript
console.log(1 === '1');          // false
console.log(1 == '1');           // true  ('1' is converted to 1)
console.log(0 == false);         // true
console.log(null == undefined);  // true
console.log(null === undefined); // false
console.log(NaN === NaN);        // false; use Number.isNaN(value)
console.log([1] === [1]);        // false: two different objects
console.log('5' + 1);            // '51' (+ with a string concatenates)
console.log('5' - 1);            // 4    (- converts to numbers)
```

Falsy values: `false`, `0`, `-0`, `0n`, `''`, `null`, `undefined`, `NaN`. Everything else is truthy, including `'0'`, `[]`, and `{}`.

## Common Mistakes

- Using `==` and getting unexpected coercion. Prefer `===`.
- Assuming `const` makes objects immutable. Use `Object.freeze` for a shallow freeze.
- Checking for arrays with `typeof`. Use `Array.isArray`.
- Floating-point surprises: `0.1 + 0.2 === 0.3` is `false`.

## Edge Cases

- `typeof null` is `'object'`.
- `typeof function () {}` is `'function'`, even though functions are objects.
- Very large integers lose precision beyond `Number.MAX_SAFE_INTEGER`; use `bigint` when needed.
