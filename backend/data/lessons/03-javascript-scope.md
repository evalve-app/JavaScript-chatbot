# JavaScript Scope

## Explanation

Scope decides where a variable can be accessed. JavaScript uses **lexical scope**: what a piece of code can see is decided by where it is written, not where it is called.

Kinds of scope:

- **Global scope**: variables declared outside any function or block.
- **Function scope**: variables declared inside a function are visible only inside it. `var` is function-scoped.
- **Block scope**: `let` and `const` are visible only inside the nearest `{ ... }` block, such as an `if` body or a loop.
- **Module scope**: top-level variables in an ES module are local to that module.

When code reads a variable, JavaScript looks in the current scope, then the enclosing scope, and so on up to the global scope. This chain is the **scope chain**. If the name is never found, a `ReferenceError` is thrown.

## Examples

```javascript
const site = 'StudyBot'; // global

function outer() {
  const level = 'outer';

  function inner() {
    const level = 'inner'; // shadows outer's level
    console.log(site, level); // StudyBot inner
  }

  inner();
  console.log(level); // outer
}

outer();
```

Block scope with `let` versus function scope with `var`:

```javascript
if (true) {
  var a = 1;
  let b = 2;
}
console.log(a); // 1
console.log(b); // ReferenceError: b is not defined
```

## Common Mistakes

- Assigning to an undeclared variable. In sloppy mode it silently creates a global; in strict mode (and in modules) it throws a `ReferenceError`.
- Expecting a variable declared inside a block to be available after it.
- Accidentally shadowing a variable and changing the inner copy instead of the outer one.
- Using `var` in loops and being surprised that callbacks all see the final value (see the closures lesson).

## Edge Cases

- `let` and `const` are in a "temporal dead zone" from the start of their block until their declaration line; reading them earlier throws a `ReferenceError`.
- Function parameters are scoped to the function body.
- A `try...catch` `catch (error)` binding is scoped to the `catch` block.
