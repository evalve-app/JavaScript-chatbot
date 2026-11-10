# JavaScript Functions and Parameters

## Explanation

A function is a reusable block of code. JavaScript has several ways to create one:

- **Function declarations**: `function add(a, b) { ... }`. Hoisted, so they can be called before they appear.
- **Function expressions**: `const add = function (a, b) { ... };`
- **Arrow functions**: `const add = (a, b) => a + b;`. Shorter, and they do not have their own `this` or `arguments`.

**Parameters** are the names in the definition. **Arguments** are the values passed when calling. JavaScript does not check argument counts: missing arguments are `undefined`, and extra arguments are ignored (unless collected).

A function returns `undefined` unless it uses `return` with a value.

## Examples

```javascript
function greet(name = 'friend') { // default parameter
  return `Hello, ${name}!`;
}

console.log(greet('Lin')); // Hello, Lin!
console.log(greet());      // Hello, friend!

const sum = (...numbers) => numbers.reduce((total, n) => total + n, 0); // rest parameter
console.log(sum(1, 2, 3)); // 6

function describe({ name, age }) { // destructured parameter
  return `${name} is ${age}`;
}
console.log(describe({ name: 'Kai', age: 30 }));

console.log(greet.length); // 0 (parameters with defaults are not counted)
```

Arrow functions can return an object literal by wrapping it in parentheses:

```javascript
const makePoint = (x, y) => ({ x, y });
```

## Functions Are Values

Functions can be stored in variables, passed as arguments, and returned from other functions. Functions that take or return other functions are called **higher-order functions**.

```javascript
const twice = (fn) => (value) => fn(fn(value));
const addThree = (n) => n + 3;
console.log(twice(addThree)(1)); // 7
```

## Common Mistakes

- Forgetting `return`, so the function returns `undefined`.
- Using curly braces in an arrow function and expecting an implicit return: `(n) => { n * 2 }` returns `undefined`.
- Putting `return` on its own line before the value. Automatic semicolon insertion makes it `return;`.
- Calling a function instead of passing it: `button.addEventListener('click', handle())` runs `handle` immediately.
- Passing arguments in the wrong order.

## Edge Cases

- Default parameters apply only when the argument is `undefined`, not `null`.
- Arrow functions cannot be used as constructors with `new`.
