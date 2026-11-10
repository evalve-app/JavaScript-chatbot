# JavaScript Error Handling

## Explanation

When something goes wrong, JavaScript **throws** an error. If nothing catches it, the current operation stops and the error is reported.

Common built-in error types:

| Error | Typical cause |
|---|---|
| `SyntaxError` | Code that cannot be parsed, such as a missing parenthesis or quote |
| `ReferenceError` | Using a variable that does not exist (or is in the temporal dead zone) |
| `TypeError` | Using a value the wrong way, such as calling `undefined` or reading a property of `null` |
| `RangeError` | A value out of range, such as an invalid array length or too much recursion |

Use `try...catch` to handle errors and `throw` to raise your own. `finally` runs whether or not an error occurred.

## Examples

```javascript
function parseAge(input) {
  const age = Number(input);
  if (Number.isNaN(age) || age < 0) {
    throw new RangeError(`Invalid age: ${input}`);
  }
  return age;
}

try {
  parseAge('abc');
} catch (error) {
  console.log(error.name);    // RangeError
  console.log(error.message); // Invalid age: abc
} finally {
  console.log('Validation finished');
}
```

Custom error classes:

```javascript
class ValidationError extends Error {
  constructor(field, message) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
  }
}

try {
  throw new ValidationError('email', 'Email is required');
} catch (error) {
  if (error instanceof ValidationError) {
    console.log(`${error.field}: ${error.message}`);
  } else {
    throw error; // rethrow errors you don't know how to handle
  }
}
```

Asynchronous errors:

```javascript
async function load() {
  try {
    const response = await fetch('/api/data');
    return await response.json();
  } catch (error) {
    console.error('Load failed:', error.message);
    return null;
  }
}
```

## Reading Error Messages

- `TypeError: Cannot read properties of undefined (reading 'name')` means you accessed `.name` on something that is `undefined`. Check the value before the dot.
- `ReferenceError: total is not defined` usually means a typo or a variable used outside its scope.
- `SyntaxError: Unexpected end of input` often means a missing `}` or `)`.

## Common Mistakes

- Throwing strings instead of `Error` objects (you lose the stack trace).
- Catching errors and silently ignoring them.
- Expecting `try...catch` to catch errors in a callback that runs later (for example, inside `setTimeout`).
- Forgetting that `fetch` does not reject on HTTP errors like 404; check `response.ok`.

## Edge Cases

- `SyntaxError`s in a file stop the whole script before it runs, so `try...catch` in that file cannot catch them.
- A `return` inside `finally` overrides any earlier `return` or thrown error.
