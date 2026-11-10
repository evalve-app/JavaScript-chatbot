# JavaScript Objects

## Explanation

An object is a collection of **properties**: key/value pairs. Keys are strings (or symbols); values can be anything, including functions (called **methods**).

Objects are reference values. Assigning an object to another variable copies the reference, so both variables point to the same object.

## Examples

```javascript
const user = {
  name: 'Mira',
  age: 28,
  'favorite color': 'green',
  greet() {
    return `Hi, I'm ${this.name}`;
  },
};

console.log(user.name);              // dot notation
console.log(user['favorite color']); // bracket notation (needed for spaces or dynamic keys)

const key = 'age';
console.log(user[key]); // 28

user.email = 'mira@example.com'; // add a property
delete user.age;                 // remove a property

console.log('name' in user);         // true
console.log(Object.hasOwn(user, 'email')); // true
```

Iterating:

```javascript
const scores = { ana: 9, ben: 7 };

for (const [name, score] of Object.entries(scores)) {
  console.log(name, score);
}

console.log(Object.keys(scores));   // ['ana', 'ben']
console.log(Object.values(scores)); // [9, 7]
```

Destructuring and spreading:

```javascript
const { name, age = 0 } = { name: 'Leo' }; // age defaults to 0
const merged = { ...{ a: 1 }, ...{ b: 2 } }; // { a: 1, b: 2 }
```

## References and Copies

```javascript
const a = { count: 1 };
const b = a;
b.count = 2;
console.log(a.count); // 2: same object

const shallow = { ...a };       // copies top-level properties only
const deep = structuredClone(a); // copies nested objects too
```

## Common Mistakes

- Using dot notation with a variable: `obj.key` reads the property named `"key"`, not the value of `key`.
- Expecting `{ ...obj }` to copy nested objects.
- Comparing objects with `===` to check if their contents match.
- Losing `this` by extracting a method: `const fn = user.greet; fn()`.

## Edge Cases

- Accessing a missing property returns `undefined`; accessing a property of `undefined` throws. Optional chaining (`user.address?.city`) avoids the error.
- Number keys are converted to strings: `obj[1]` and `obj['1']` are the same property.
