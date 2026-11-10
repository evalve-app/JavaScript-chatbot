# JavaScript Callbacks

## Explanation

A **callback** is a function passed to another function so it can be called later. The receiving function decides when, and with what arguments, to call it.

Callbacks can be:

- **Synchronous**: called right away, before the outer function returns. Array methods like `map` and `forEach` use synchronous callbacks.
- **Asynchronous**: called later, after some event or delay. `setTimeout`, event listeners, and Node.js file APIs use asynchronous callbacks.

## Examples

Synchronous callback:

```javascript
function repeat(times, callback) {
  for (let i = 0; i < times; i++) {
    callback(i);
  }
}

repeat(3, (i) => console.log(`Run ${i}`));
```

Asynchronous callback:

```javascript
console.log('start');
setTimeout(() => console.log('timer done'), 1000);
console.log('end');
// start, end, timer done
```

Node.js "error-first" callback style:

```javascript
const fs = require('fs');

fs.readFile('notes.txt', 'utf8', (error, contents) => {
  if (error) {
    console.error('Could not read file:', error.message);
    return;
  }
  console.log(contents);
});
```

## Callback Hell

Nesting many asynchronous callbacks makes code hard to read and handle errors in:

```javascript
getUser(id, (user) => {
  getOrders(user, (orders) => {
    getInvoice(orders[0], (invoice) => {
      console.log(invoice);
    });
  });
});
```

Promises and `async`/`await` solve this by flattening the structure.

## Common Mistakes

- Calling the function instead of passing it: `setTimeout(sayHi(), 1000)` runs `sayHi` now and passes its return value.
- Trying to `return` a value from an asynchronous callback to the outer function. The outer function has already returned.
- Forgetting to handle the `error` argument in error-first callbacks.
- Losing `this` when passing a method as a callback (`setTimeout(obj.method, 0)`); use an arrow function or `bind`.

## Edge Cases

- `setTimeout(fn, 0)` does not run immediately; it runs after the current code and queued microtasks finish.
- A callback can be called more than once, or never, depending on the function that receives it.
