# JavaScript Closures

## Explanation

A **closure** is a function together with the variables from the scope where it was created. Because JavaScript uses lexical scope, an inner function can keep using variables from its outer function even after the outer function has returned.

A closure keeps a reference to the variable itself, not a snapshot of its value. If the variable changes, the closure sees the new value.

Closures are used for:

- Private state (data that can only be changed through specific functions)
- Function factories (functions that build customized functions)
- Callbacks and event handlers that remember context
- Techniques like memoization, debouncing, and partial application

## Examples

Private state:

```javascript
function createBankAccount(initial) {
  let balance = initial;

  return {
    deposit(amount) {
      balance += amount;
      return balance;
    },
    getBalance() {
      return balance;
    },
  };
}

const account = createBankAccount(100);
account.deposit(50);
console.log(account.getBalance()); // 150
console.log(account.balance);      // undefined: balance is private
```

Function factory:

```javascript
function multiplier(factor) {
  return (n) => n * factor;
}

const double = multiplier(2);
const triple = multiplier(3);
console.log(double(5), triple(5)); // 10 15
```

## The Classic Loop Problem

```javascript
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0);
}
// Logs: 3 3 3

for (let j = 0; j < 3; j++) {
  setTimeout(() => console.log(j), 0);
}
// Logs: 0 1 2
```

`var` creates one `i` shared by every callback. `let` creates a new `j` for each loop iteration, so each callback closes over its own value.

## Common Mistakes

- Thinking a closure copies the value at creation time. It references the live variable.
- Using `var` in loops with asynchronous callbacks.
- Creating closures that hold large objects for a long time, which keeps that memory from being freed.

## Edge Cases

- Every function in JavaScript forms a closure, but the term is usually used when the function outlives its outer scope.
- Two closures created by the same outer call share the same variables.
